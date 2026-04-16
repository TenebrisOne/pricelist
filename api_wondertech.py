"""
WONDERTECH webhook HTTP.

This file does not reimplement the generator. It only exposes the
existing logic in wondertech_pricelist_env.py through Flask so Odoo can
trigger it from a server.
"""

import base64
import contextlib
import io
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_file

from wondertech_pricelist_env import (
    CONFIG,
    buscar_lista,
    cargar_credenciales_desde_env,
    conectar_odoo,
    generar_pdf,
)

load_dotenv()

BASE_DIR   = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "PDFs" / "output"

app = Flask(__name__)

# ──── Logging con colores ────
class _ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG":    "\033[36m",
        "INFO":     "\033[32m",
        "WARNING":  "\033[33m",
        "ERROR":    "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        now   = datetime.now().strftime("%H:%M:%S")
        msg   = super().format(record)
        return f"[{now}] {color}{record.levelname:7s}{self.RESET} | {msg}"

_handler = logging.StreamHandler()
_handler.setFormatter(_ColoredFormatter())
_logger = logging.getLogger("wondertech")
_logger.setLevel(logging.INFO)
_logger.handlers = [_handler]
_logger.propagate = False
logging.getLogger("werkzeug").setLevel(logging.ERROR)


# ──── Logging de requests HTTP ────
@app.before_request
def _mark_request_start():
    g.request_started_at = time.perf_counter()
    g.request_id = str(uuid.uuid4())[:8]


@app.after_request
def _log_request(response):
    now    = datetime.now().strftime("%H:%M:%S")
    method = request.method
    path   = request.path
    status = response.status_code

    started_at = getattr(g, "request_started_at", None)
    duration = 0.0
    if started_at:
        duration = (time.perf_counter() - started_at) * 1000.0

    if status < 300:
        color = "\033[32m"
        icon  = "OK"
    elif status < 400:
        color = "\033[33m"
        icon  = "REDIR"
    else:
        color = "\033[31m"
        icon  = "ERR"

    reset = "\033[0m"
    dim   = "\033[2m"
    rid = getattr(g, "request_id", "-")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "-")

    _logger.info(
        f"{dim}{now}{reset} {color}{icon:<5s}{reset} {dim}rid={rid}{reset} "
        f"{method:<6s} {path:<42s} {color}{status}{reset} "
        f"{dim}{duration:7.1f}ms ip={ip}{reset}"
    )
    return response


def _capture_call_stdout(func, *args, **kwargs):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return result, buffer.getvalue()


def _log_captured_stdout(raw_text, request_id):
    for raw_line in (raw_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("Conectado a Odoo como UID="):
            _logger.info("[rid=%s] ODOO %s", request_id, line)
            continue
        if "productos cargados. Moneda:" in line:
            _logger.info("[rid=%s] DATA %s", request_id, line)
            continue
        if line.startswith("PDF generado:"):
            _logger.info("[rid=%s] FILE %s", request_id, line)
            continue
        if "no encontrado" in line.lower():
            _logger.warning("[rid=%s] WARN %s", request_id, line)
            continue

        _logger.info("[rid=%s] OUT  %s", request_id, line)


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
    seen    = set()
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

    auth_header  = request.headers.get("Authorization", "").strip()
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


def _get_record_name_by_id(models, cfg, res_model, res_id):
    db = cfg["db"]
    pw = cfg["password"]
    record = models.execute_kw(
        db, cfg["uid"], pw,
        res_model, "read",
        [[res_id]],
        {"fields": ["name"]},
    )
    if not record:
        return None
    return record[0].get("name")


def _create_odoo_attachment(models, cfg, res_model, res_id, name, raw_bytes):
    db = cfg["db"]
    pw = cfg["password"]

    attachment_id = models.execute_kw(
        db, cfg["uid"], pw,
        "ir.attachment", "create",
        [{
            "name":      name,
            "type":      "binary",
            "datas":     base64.b64encode(raw_bytes).decode("utf-8"),
            "res_model": res_model,
            "res_id":    res_id,
            "mimetype":  "application/pdf",
        }],
    )
    return attachment_id


def _post_chatter_message(models, cfg, res_model, res_id, body, subject, attachment_id=None):
    db = cfg["db"]
    pw = cfg["password"]

    message_vals = {
        "body":          body,
        "subject":       subject,
        "message_type":  "comment",
        "subtype_xmlid": "mail.mt_comment",
    }

    # ✅ Odoo 18: attachment_ids requiere lista de IDs, no tuplas ORM
    if attachment_id:
        message_vals["attachment_ids"] = [attachment_id]

    models.execute_kw(
        db, cfg["uid"], pw,
        res_model, "message_post",
        [[res_id]],
        message_vals,
    )


def _attach_pdf_to_record(models, cfg, res_model, res_id, filename, raw_bytes, message_body=None, message_subject=None):
    if not message_body:
        message_body = f"PDF generado automaticamente: {filename}"
    if not message_subject:
        message_subject = f"PDF generado: {filename}"

    attachment_id = _create_odoo_attachment(
        models, cfg, res_model, res_id, filename, raw_bytes
    )
    _post_chatter_message(
        models, cfg, res_model, res_id,
        body=message_body,
        subject=message_subject,
        attachment_id=attachment_id,
    )
    rid = getattr(g, "request_id", "-")
    _logger.info(
        "[rid=%s] CHATTER adjunto='%s' modelo=%s id=%d",
        rid, filename, res_model, res_id
    )
    return attachment_id


def _generate_requested_lists(requested_lists):
    rid = getattr(g, "request_id", "-")
    cfg = _build_runtime_config()
    _logger.info(
        "[rid=%s] START listas=%s ambiente=%s",
        rid, ", ".join(requested_lists), cfg.get("ambiente", "-")
    )
    (conn_result, conn_stdout) = _capture_call_stdout(
        conectar_odoo, cfg["url"], cfg["db"], cfg["uid"], cfg["password"]
    )
    _log_captured_stdout(conn_stdout, rid)
    models, uid = conn_result

    generated = []
    skipped   = []

    for nombre_lista in requested_lists:
        (fetch_result, fetch_stdout) = _capture_call_stdout(
            buscar_lista, models, uid, cfg, nombre_lista
        )
        _log_captured_stdout(fetch_stdout, rid)
        lista_info, productos, moneda_info = fetch_result

        if not lista_info:
            skipped.append({"lista": nombre_lista, "motivo": "Lista no encontrada en Odoo"})
            _logger.warning("[rid=%s] SKIP lista='%s' motivo='Lista no encontrada en Odoo'", rid, nombre_lista)
            continue

        if not productos:
            skipped.append({"lista": nombre_lista, "motivo": "La lista no tiene productos para generar PDF"})
            _logger.warning("[rid=%s] SKIP lista='%s' motivo='Sin productos para generar PDF'", rid, nombre_lista)
            continue

        moneda_cfg = {}
        if moneda_info:
            moneda_cfg = {
                "moneda":         moneda_info.get("name", cfg.get("moneda", "COP")),
                "simbolo_moneda": moneda_info.get("symbol", cfg.get("simbolo_moneda", "$")),
            }

        (pdf_result, pdf_stdout) = _capture_call_stdout(
            generar_pdf, nombre_lista, productos, {**cfg, **moneda_cfg}
        )
        _log_captured_stdout(pdf_stdout, rid)
        nombre_archivo, raw_bytes = pdf_result
        ruta_archivo = OUTPUT_DIR / nombre_archivo
        if not ruta_archivo.exists():
            raise FileNotFoundError(
                f"No se encontro el PDF generado para la lista '{nombre_lista}'"
            )

        generated.append({
            "lista":        nombre_lista,
            "archivo":      nombre_archivo,
            "ruta_archivo": str(ruta_archivo),
            "raw_bytes":    raw_bytes,
            "productos":    len(productos),
            "moneda":       moneda_cfg.get("moneda", cfg.get("moneda", "COP")),
        })
        _logger.info(
            "[rid=%s] DONE lista='%s' productos=%d archivo='%s'",
            rid, nombre_lista, len(productos), nombre_archivo
        )

    _logger.info(
        "[rid=%s] END generadas=%d omitidas=%d",
        rid, len(generated), len(skipped)
    )

    return cfg, generated, skipped


def _generate_requested_list_ids(requested_ids):
    rid = getattr(g, "request_id", "-")
    cfg = _build_runtime_config()
    _logger.info(
        "[rid=%s] START ids=%s ambiente=%s",
        rid, ", ".join(str(x) for x in requested_ids), cfg.get("ambiente", "-")
    )
    (conn_result, conn_stdout) = _capture_call_stdout(
        conectar_odoo, cfg["url"], cfg["db"], cfg["uid"], cfg["password"]
    )
    _log_captured_stdout(conn_stdout, rid)
    models, uid = conn_result

    generated = []
    skipped   = []

    for list_id in requested_ids:
        (fetch_result, fetch_stdout) = _capture_call_stdout(
            buscar_lista, models, uid, cfg, None, int(list_id)
        )
        _log_captured_stdout(fetch_stdout, rid)
        lista_info, productos, moneda_info = fetch_result

        if not lista_info:
            skipped.append({"lista_id": int(list_id), "motivo": "Lista no encontrada en Odoo"})
            _logger.warning("[rid=%s] SKIP lista_id=%d motivo='Lista no encontrada en Odoo'", rid, int(list_id))
            continue

        lista_nombre = lista_info.get("name") or f"ID {list_id}"

        if not productos:
            skipped.append({"lista": lista_nombre, "lista_id": int(list_id), "motivo": "La lista no tiene productos para generar PDF"})
            _logger.warning("[rid=%s] SKIP lista='%s' id=%d motivo='Sin productos para generar PDF'", rid, lista_nombre, int(list_id))
            continue

        moneda_cfg = {}
        if moneda_info:
            moneda_cfg = {
                "moneda":         moneda_info.get("name", cfg.get("moneda", "COP")),
                "simbolo_moneda": moneda_info.get("symbol", cfg.get("simbolo_moneda", "$")),
            }

        (pdf_result, pdf_stdout) = _capture_call_stdout(
            generar_pdf, lista_nombre, productos, {**cfg, **moneda_cfg}
        )
        _log_captured_stdout(pdf_stdout, rid)
        nombre_archivo, raw_bytes = pdf_result
        ruta_archivo = OUTPUT_DIR / nombre_archivo
        if not ruta_archivo.exists():
            raise FileNotFoundError(
                f"No se encontro el PDF generado para la lista ID '{list_id}'"
            )

        generated.append({
            "lista":        lista_nombre,
            "lista_id":     int(list_id),
            "archivo":      nombre_archivo,
            "ruta_archivo": str(ruta_archivo),
            "raw_bytes":    raw_bytes,
            "productos":    len(productos),
            "moneda":       moneda_cfg.get("moneda", cfg.get("moneda", "COP")),
        })
        _logger.info(
            "[rid=%s] DONE lista='%s' id=%d productos=%d archivo='%s'",
            rid, lista_nombre, int(list_id), len(productos), nombre_archivo
        )

    _logger.info(
        "[rid=%s] END generadas=%d omitidas=%d",
        rid, len(generated), len(skipped)
    )
    return cfg, generated, skipped


def _json_result(cfg, requested_lists, generated, skipped):
    if generated and skipped:
        status    = "partial"
        http_code = 200
    elif generated:
        status    = "success"
        http_code = 200
    else:
        status    = "error"
        http_code = 404

    generated_clean = [
        {k: v for k, v in g.items() if k != "raw_bytes"}
        for g in generated
    ]

    return (
        jsonify({
            "status":              status,
            "ambiente":            cfg["ambiente"],
            "listas_solicitadas":  requested_lists,
            "cantidad_solicitada": len(requested_lists),
            "cantidad_generada":   len(generated),
            "generadas":           generated_clean,
            "omitidas":            skipped,
        }),
        http_code,
    )


def _handle_generation(route_list=None, default_to_all=False, default_pdf=False):
    rid = getattr(g, "request_id", "-")
    payload = _request_payload()

    token_error = _validate_webhook_token(payload)
    if token_error:
        _logger.warning("[rid=%s] AUTH token de webhook invalido", rid)
        return token_error

    requested_lists = _resolve_requested_lists(
        payload,
        route_list=route_list,
        default_to_all=default_to_all,
    )
    if not requested_lists:
        _logger.warning("[rid=%s] INPUT sin listas en payload", rid)
        return (
            jsonify({"error": "No se recibio ninguna lista. Envia lista, listas o usa el endpoint /webhook/generate-all."}),
            400,
        )
    _logger.info(
        "[rid=%s] REQUEST listas=%s default_pdf=%s payload_keys=%s",
        rid, ", ".join(requested_lists), default_pdf, ",".join(sorted(payload.keys()))
    )

    try:
        cfg, generated, skipped = _generate_requested_lists(requested_lists)
    except Exception as exc:
        _logger.exception("[rid=%s] ERROR durante generacion: %s", rid, str(exc))
        return jsonify({"error": str(exc)}), 500

    wants_pdf = _should_return_pdf(payload, default=default_pdf)
    if wants_pdf:
        if not generated:
            _logger.warning("[rid=%s] PDF solicitado pero no se generaron archivos", rid)
            return _json_result(cfg, requested_lists, generated, skipped)

        if len(generated) != 1:
            _logger.warning("[rid=%s] PDF solicitado con %d listas generadas", rid, len(generated))
            return (
                jsonify({
                    "error":             "La respuesta PDF solo esta disponible cuando se genera una sola lista.",
                    "listas_solicitadas": requested_lists,
                    "cantidad_generada":  len(generated),
                }),
                400,
            )

        pdf_info = generated[0]
        _logger.info("[rid=%s] RESPONSE tipo=pdf archivo='%s'", rid, pdf_info["archivo"])
        return send_file(
            pdf_info["ruta_archivo"],
            mimetype="application/pdf",
            as_attachment=True,
            download_name=pdf_info["archivo"],
        )

    _logger.info("[rid=%s] RESPONSE tipo=json status=ok", rid)
    return _json_result(cfg, requested_lists, generated, skipped)


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status":  "ok",
        "service": "WONDERTECH Price List Webhook",
        "version": "2.0",
        "endpoints": [
            "/webhook/odoo",
            "/webhook/generate",
            "/webhook/generate/<lista_nombre>",
            "/webhook/generate-by-id",
            "/webhook/generate-attach/<lista_nombre>",
            "/webhook/generate-all",
        ],
    })


@app.route("/webhook", methods=["GET", "POST"])
def webhook_main():
    """Webhook principal para Odoo (curl -X POST http://localhost:5008/webhook)"""
    return _handle_generation(default_to_all=True, default_pdf=False)


@app.route("/webhook/odoo", methods=["GET", "POST"])
def webhook_odoo():
    return _handle_generation(default_to_all=True, default_pdf=False)


@app.route("/webhook/generate", methods=["GET", "POST"])
def webhook_generate():
    return _handle_generation(default_to_all=True, default_pdf=True)


@app.route("/webhook/generate/<path:lista_nombre>", methods=["GET", "POST"])
def webhook_generate_single(lista_nombre):
    """
    Generar y descargar PDF de una lista especifica.
    Soporta GET (para Odoo Studio) y POST (para webhooks).

    Ejemplos:
    - GET:  https://webhooks-odoo.wondertech.com.co/pricelist/webhook/generate/Lista%20Business
    - POST: curl -X POST https://webhooks-odoo.wondertech.com.co/pricelist/webhook/generate/Lista%20Business
    """
    return _handle_generation(route_list=lista_nombre, default_pdf=True)


@app.route("/webhook/generate-by-id", methods=["GET", "POST"])
def webhook_generate_by_id():
    rid = getattr(g, "request_id", "-")
    payload = _request_payload()

    token_error = _validate_webhook_token(payload)
    if token_error:
        return token_error

    res_model = (
        payload.get("res_model")
        or payload.get("_model")
        or "product.pricelist"
    )
    res_id = (
        payload.get("res_id")
        or payload.get("_id")
        or payload.get("id")
    )
    if res_id is None:
        return jsonify({"error": "Debe enviar res_id en el payload o query string (res_id, _id o id)."}), 400

    try:
        res_id = int(res_id)
    except (TypeError, ValueError):
        return jsonify({"error": "res_id debe ser un numero valido."}), 400

    _logger.info("[rid=%s] BY_ID modelo=%s id=%d", rid, res_model, res_id)

    # Si es una lista de precios, generar por ID exacto para evitar ambiguedad de nombres.
    if res_model == "product.pricelist":
        try:
            cfg, generated, skipped = _generate_requested_list_ids([res_id])
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

        if not generated:
            return _json_result(cfg, [f"id:{res_id}"], generated, skipped)

        if len(generated) != 1:
            return jsonify({"error": "Se esperaba exactamente una lista generada."}), 400

        pdf_info = generated[0]
        return send_file(
            pdf_info["ruta_archivo"],
            mimetype="application/pdf",
            as_attachment=True,
            download_name=pdf_info["archivo"],
        )

    cfg = _build_runtime_config()
    (conn_result, conn_stdout) = _capture_call_stdout(
        conectar_odoo, cfg["url"], cfg["db"], cfg["uid"], cfg["password"]
    )
    _log_captured_stdout(conn_stdout, rid)
    models, uid = conn_result
    nombre_lista = _get_record_name_by_id(models, cfg, res_model, res_id)
    if not nombre_lista:
        return (
            jsonify({
                "error":     "No se encontro el registro con res_model/res_id.",
                "res_model": res_model,
                "res_id":    res_id,
            }),
            404,
        )

    return _handle_generation(route_list=nombre_lista, default_pdf=True)


def _handle_generate_attach(lista_nombre_from_route=None):
    """
    Genera el PDF de la lista indicada, lo adjunta al Chatter del registro
    en Odoo y ademas lo devuelve como descarga al navegador.

    Payload esperado (JSON o form):
        res_model       - modelo Odoo (default: product.pricelist)
        res_id          - ID del registro donde se adjuntara el PDF
        message_body    - (opcional) cuerpo del mensaje en el Chatter
        message_subject - (opcional) asunto del mensaje en el Chatter
        token           - (opcional) token de seguridad del webhook
    """
    rid = getattr(g, "request_id", "-")
    payload = _request_payload()

    token_error = _validate_webhook_token(payload)
    if token_error:
        return token_error

    res_model = (
        payload.get("res_model")
        or payload.get("_model")
        or "product.pricelist"
    )
    res_id = (
        payload.get("res_id")
        or payload.get("_id")
        or payload.get("id")
    )
    if res_id is None:
        return jsonify({"error": "Debe enviar res_id en el payload (res_id, _id o id)."}), 400

    try:
        res_id = int(res_id)
    except (TypeError, ValueError):
        return jsonify({"error": "res_id debe ser un numero valido."}), 400

    message_body    = payload.get("message_body")
    message_subject = payload.get("message_subject")

    lista_nombre = (
        lista_nombre_from_route
        or payload.get("lista")
        or payload.get("lista_nombre")
        or payload.get("nombre_lista")
        or payload.get("pricelist")
        or payload.get("name")
        or payload.get("_name")
    )

    if not lista_nombre:
        try:
            cfg_lookup = _build_runtime_config()
            (conn_result, conn_stdout) = _capture_call_stdout(
                conectar_odoo,
                cfg_lookup["url"],
                cfg_lookup["db"],
                cfg_lookup["uid"],
                cfg_lookup["password"],
            )
            _log_captured_stdout(conn_stdout, rid)
            models_lookup, _ = conn_result
            lista_nombre = _get_record_name_by_id(models_lookup, cfg_lookup, res_model, res_id)
        except Exception as exc:
            return jsonify({"error": f"No se pudo resolver la lista por ID: {str(exc)}"}), 500

    if not lista_nombre:
        return jsonify({"error": "No se pudo determinar el nombre de la lista."}), 400

    lista_candidates = [lista_nombre]
    if " (" in lista_nombre and lista_nombre.endswith(")"):
        base_name = lista_nombre.rsplit(" (", 1)[0].strip()
        if base_name and base_name not in lista_candidates:
            lista_candidates.append(base_name)

    _logger.info(
        "[rid=%s] ATTACH lista='%s' modelo=%s id=%d",
        rid, lista_nombre, res_model, res_id
    )

    cfg = None
    generated = []
    skipped = []
    last_error = None
    lista_usada = None

    # Para pricelists: priorizar SIEMPRE el ID exacto, luego fallback por nombre.
    should_try_exact_id = (res_model == "product.pricelist")

    if should_try_exact_id:
        try:
            cfg, generated, skipped = _generate_requested_list_ids([res_id])
            if generated:
                lista_usada = generated[0].get("lista")
                _logger.info("[rid=%s] PRIORITY ID usada lista_id=%d", rid, res_id)
        except Exception as exc:
            last_error = str(exc)

    # Si por ID no genero nada, solo hacer fallback por nombre cuando
    # realmente no hubo coincidencia por ID.
    can_fallback_by_name = True
    if should_try_exact_id and skipped:
        id_not_found = any(
            str(item.get("motivo", "")).lower().startswith("lista no encontrada")
            for item in skipped
        )
        can_fallback_by_name = id_not_found

    if not generated and can_fallback_by_name:
        for candidate in lista_candidates:
            try:
                cfg, generated, skipped = _generate_requested_lists([candidate])
            except Exception as exc:
                last_error = str(exc)
                continue
            if generated:
                lista_usada = candidate
                _logger.info("[rid=%s] FALLBACK NAME usado='%s'", rid, candidate)
                break

    if not generated and last_error:
        return jsonify({"error": last_error}), 500

    if not generated:
        return _json_result(cfg, [lista_nombre], generated, skipped)

    if len(generated) != 1:
        return (
            jsonify({
                "error":             "Solo se puede adjuntar un PDF cuando se genera una sola lista.",
                "listas_solicitadas": [lista_nombre],
                "cantidad_generada":  len(generated),
            }),
            400,
        )

    pdf_info  = generated[0]
    raw_bytes = pdf_info["raw_bytes"]
    filename  = pdf_info["archivo"]

    (conn_result, conn_stdout) = _capture_call_stdout(
        conectar_odoo, cfg["url"], cfg["db"], cfg["uid"], cfg["password"]
    )
    _log_captured_stdout(conn_stdout, rid)
    models, uid = conn_result
    try:
        attachment_id = _attach_pdf_to_record(
            models, cfg,
            res_model, res_id,
            filename, raw_bytes,
            message_body=message_body,
            message_subject=message_subject,
        )
    except Exception as exc:
        return jsonify({"error": f"Error al adjuntar el PDF en Odoo: {str(exc)}"}), 500

    _logger.info("[rid=%s] ATTACH_OK lista_resuelta='%s' archivo='%s'", rid, lista_usada or lista_nombre, filename)
    return send_file(
        pdf_info["ruta_archivo"],
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/webhook/generate-attach", methods=["POST"])
def webhook_generate_attach_auto():
    """
    Variante sin lista en URL.
    Resuelve el nombre de la lista a partir de res_model/res_id o del payload.
    """
    return _handle_generate_attach()


@app.route("/webhook/generate-attach/<path:lista_nombre>", methods=["POST"])
def webhook_generate_attach(lista_nombre):
    return _handle_generate_attach(lista_nombre_from_route=lista_nombre)


@app.route("/webhook/generate-all", methods=["GET", "POST"])
def webhook_generate_all():
    return _handle_generation(default_to_all=True, default_pdf=True)


if __name__ == "__main__":
    # ── Leer configuracion desde .env ──
    port       = int(os.getenv("PORT", "5008"))
    debug      = _to_bool(os.getenv("FLASK_DEBUG"), default=False)
    use_prod   = _to_bool(os.getenv("USE_PRODUCTION", "false"))
    ambiente   = "PRODUCCION" if use_prod else "PRUEBAS"
    flask_modo = "DEBUG" if debug else "NORMAL"

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    print()
    print("\033[0;36m┌───────────────────────────────────────────────────────┐\033[0m")
    print("\033[0;36m│\033[0m  \033[1mWONDERTECH - Price List Webhook v2.0\033[0m                 \033[0;36m│\033[0m")
    print(f"\033[0;36m│\033[0m  \033[2m{now}\033[0m                                      \033[0;36m│\033[0m")
    print("\033[0;36m└───────────────────────────────────────────────────────┘\033[0m")
    print()
    print(f"\033[2m[{now}]\033[0m  \033[36mServidor\033[0m   : http://0.0.0.0:{port}")
    print(f"\033[2m[{now}]\033[0m  \033[36mPuerto\033[0m     : {port}")
    print(f"\033[2m[{now}]\033[0m  \033[36mAmbiente\033[0m   : {ambiente}")
    print(f"\033[2m[{now}]\033[0m  \033[36mFlask\033[0m      : {flask_modo}")
    print(f"\033[2m[{now}]\033[0m  \033[36mDirectorio\033[0m : {BASE_DIR}")
    print()
    print("\033[0;36m╭───────────────────────────────────────────────────────╮\033[0m")
    print("\033[0;36m│\033[0m  \033[1mEndpoints disponibles\033[0m                              \033[0;36m│\033[0m")
    print("\033[0;36m╰───────────────────────────────────────────────────────╯\033[0m")
    print()
    endpoints = [
        ("GET  /",                            "Health check"),
        ("POST /webhook/odoo",                "Webhook principal (Odoo)"),
        ("POST /webhook/generate-all",        "Generar todas las listas"),
        ("POST /webhook/generate/<lista>",    "Generar lista especifica"),
        ("POST /webhook/generate",            "Generar con filtros"),
        ("POST /webhook/generate-attach/<l>", "Generar + guardar en Chatter"),
        ("POST /webhook/generate-attach",      "Generar + guardar (Odoo webhook)"),
    ]
    for path, desc in endpoints:
        print(f"  \033[0;32m{path:<40s}\033[0m \033[2m|\033[0m {desc}")
    print()
    print("\033[2m─────────────────────────────────────────────────────────────\033[0m")
    print()
    _logger.info("Iniciando servidor Flask en puerto %d | Ambiente: %s | Flask: %s", port, ambiente, flask_modo)
    print()

    app.run(host="0.0.0.0", port=port, debug=debug)
