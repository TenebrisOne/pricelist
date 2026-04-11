"""
WONDERTECH webhook HTTP.

This file does not reimplement the generator. It only exposes the
existing logic in wondertech_pricelist_env.py through Flask so Odoo can
trigger it from a server.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file

from wondertech_pricelist_env import (
    CONFIG,
    buscar_lista,
    cargar_credenciales_desde_env,
    conectar_odoo,
    generar_pdf,
)

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "PDFs" / "output"

app = Flask(__name__)


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "si", "on"}


def _maybe_parse_json(value):
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text or text[0] not in "[{":
        return value

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _merge_multidict(payload, source):
    for key in source.keys():
        values = source.getlist(key)
        payload[key] = values if len(values) > 1 else values[0]


def _request_payload():
    payload = {}

    if request.is_json:
        payload.update(request.get_json(silent=True) or {})

    _merge_multidict(payload, request.args)
    _merge_multidict(payload, request.form)

    nested_payload = _maybe_parse_json(payload.get("payload"))
    if isinstance(nested_payload, dict):
        payload = {**nested_payload, **payload}

    return payload


def _as_list(value):
    value = _maybe_parse_json(value)

    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        normalized = value.replace("\n", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]

    return [str(value).strip()]


def _dedupe_preserving_order(values):
    seen = set()
    ordered = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)

    return ordered


def _resolve_requested_lists(payload, route_list=None, default_to_all=False):
    if route_list:
        return [route_list]

    list_keys = [
        "lista",
        "lista_nombre",
        "nombre_lista",
        "pricelist",
        "pricelist_name",
        "list_name",
        "name",
    ]
    for key in list_keys:
        if payload.get(key):
            return _dedupe_preserving_order(_as_list(payload[key]))

    list_collection_keys = ["listas", "pricelists", "listas_precio"]
    for key in list_collection_keys:
        if payload.get(key):
            return _dedupe_preserving_order(_as_list(payload[key]))

    if any(
        _to_bool(payload.get(flag))
        for flag in ("all", "todas", "todos", "generate_all")
    ):
        return list(CONFIG["listas"])

    if default_to_all:
        return list(CONFIG["listas"])

    return []


def _should_return_pdf(payload, default=False):
    response_format = str(payload.get("format", "")).strip().lower()
    if response_format == "pdf":
        return True
    if response_format == "json":
        return False

    for key in ("download", "return_pdf", "pdf"):
        if key in payload:
            return _to_bool(payload.get(key))

    return default


def _validate_webhook_token(payload):
    expected = (
        os.getenv("WEBHOOK_TOKEN", "").strip()
        or os.getenv("ODOO_WEBHOOK_TOKEN", "").strip()
    )
    if not expected:
        return None

    auth_header = request.headers.get("Authorization", "").strip()
    bearer_token = ""
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()

    candidates = [
        request.headers.get("X-Webhook-Token", "").strip(),
        bearer_token,
        str(payload.get("token", "")).strip(),
    ]

    if expected in candidates:
        return None

    return jsonify({"error": "Token de webhook invalido"}), 401


def _build_runtime_config():
    cred = cargar_credenciales_desde_env()
    return {**CONFIG, **cred}


def _generate_requested_lists(requested_lists):
    cfg = _build_runtime_config()
    models, uid = conectar_odoo(cfg["url"], cfg["db"], cfg["uid"], cfg["password"])

    generated = []
    skipped = []

    for nombre_lista in requested_lists:
        lista_info, productos, moneda_info = buscar_lista(models, uid, cfg, nombre_lista)

        if not lista_info:
            skipped.append(
                {
                    "lista": nombre_lista,
                    "motivo": "Lista no encontrada en Odoo",
                }
            )
            continue

        if not productos:
            skipped.append(
                {
                    "lista": nombre_lista,
                    "motivo": "La lista no tiene productos para generar PDF",
                }
            )
            continue

        moneda_cfg = {}
        if moneda_info:
            moneda_cfg = {
                "moneda": moneda_info.get("name", cfg.get("moneda", "COP")),
                "simbolo_moneda": moneda_info.get(
                    "symbol", cfg.get("simbolo_moneda", "$")
                ),
            }

        nombre_archivo = generar_pdf(nombre_lista, productos, {**cfg, **moneda_cfg})
        ruta_archivo = OUTPUT_DIR / nombre_archivo
        if not ruta_archivo.exists():
            raise FileNotFoundError(
                f"No se encontro el PDF generado para la lista '{nombre_lista}'"
            )

        generated.append(
            {
                "lista": nombre_lista,
                "archivo": nombre_archivo,
                "ruta_archivo": str(ruta_archivo),
                "productos": len(productos),
                "moneda": moneda_cfg.get("moneda", cfg.get("moneda", "COP")),
            }
        )

    return cfg, generated, skipped


def _json_result(cfg, requested_lists, generated, skipped):
    if generated and skipped:
        status = "partial"
        http_code = 200
    elif generated:
        status = "success"
        http_code = 200
    else:
        status = "error"
        http_code = 404

    return (
        jsonify(
            {
                "status": status,
                "ambiente": cfg["ambiente"],
                "listas_solicitadas": requested_lists,
                "cantidad_solicitada": len(requested_lists),
                "cantidad_generada": len(generated),
                "generadas": generated,
                "omitidas": skipped,
            }
        ),
        http_code,
    )


def _handle_generation(route_list=None, default_to_all=False, default_pdf=False):
    payload = _request_payload()

    token_error = _validate_webhook_token(payload)
    if token_error:
        return token_error

    requested_lists = _resolve_requested_lists(
        payload,
        route_list=route_list,
        default_to_all=default_to_all,
    )
    if not requested_lists:
        return (
            jsonify(
                {
                    "error": "No se recibio ninguna lista. Envia 'lista', 'listas' o usa el endpoint /webhook/generate-all.",
                }
            ),
            400,
        )

    try:
        cfg, generated, skipped = _generate_requested_lists(requested_lists)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    wants_pdf = _should_return_pdf(payload, default=default_pdf)
    if wants_pdf:
        if not generated:
            return _json_result(cfg, requested_lists, generated, skipped)

        if len(generated) != 1:
            return (
                jsonify(
                    {
                        "error": "La respuesta PDF solo esta disponible cuando se genera una sola lista.",
                        "listas_solicitadas": requested_lists,
                        "cantidad_generada": len(generated),
                    }
                ),
                400,
            )

        pdf_info = generated[0]
        return send_file(
            pdf_info["ruta_archivo"],
            mimetype="application/pdf",
            as_attachment=True,
            download_name=pdf_info["archivo"],
        )

    return _json_result(cfg, requested_lists, generated, skipped)


@app.route("/", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "WONDERTECH Price List Webhook",
            "version": "2.0",
            "endpoints": [
                "/webhook/odoo",
                "/webhook/generate",
                "/webhook/generate/<lista_nombre>",
                "/webhook/generate-all",
            ],
        }
    )


@app.route("/webhook/odoo", methods=["GET", "POST"])
def webhook_odoo():
    return _handle_generation(default_to_all=True, default_pdf=False)


@app.route("/webhook/generate", methods=["GET", "POST"])
def webhook_generate():
    return _handle_generation(default_to_all=True, default_pdf=False)


@app.route("/webhook/generate/<path:lista_nombre>", methods=["GET", "POST"])
def webhook_generate_single(lista_nombre):
    return _handle_generation(route_list=lista_nombre, default_pdf=True)


@app.route("/webhook/generate-all", methods=["GET", "POST"])
def webhook_generate_all():
    return _handle_generation(default_to_all=True, default_pdf=False)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = _to_bool(os.getenv("FLASK_DEBUG"), default=False)

    print("\n" + "=" * 55)
    print("  WONDERTECH - Webhook Price List Generator")
    print("=" * 55)
    print(f"  Servidor corriendo en: http://0.0.0.0:{port}")
    print("  Endpoints disponibles:")
    print("    - /webhook/odoo")
    print("    - /webhook/generate")
    print("    - /webhook/generate/<lista_nombre>")
    print("    - /webhook/generate-all")
    print("=" * 55 + "\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
