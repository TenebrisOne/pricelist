"""
=============================================================
WONDERTECH - Generador de Listas de Precios desde Odoo
=============================================================
Uso:
1. Crea un archivo .env con las credenciales del ambiente
2. Ejecuta: python wondertech_pricelist_env.py
3. Los PDFs se guardan en la carpeta donde ejecutas el script

Requisitos:
pip install reportlab python-dotenv
=============================================================
"""

import os
import re
import io
from collections import defaultdict
import xmlrpc.client
from datetime import datetime

from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

# Cargar variables del archivo .env
load_dotenv()

# -------------------------------------------------------------
#  CONFIGURACION GENERAL (sin credenciales)
# -------------------------------------------------------------
CONFIG = {
    "listas": ["Lista Business", "Lista Reseller"],
    "vigencia": "VIGENCIA: 01/04/2026 - 18/04/2026 | IVA INCLUIDO | SUJETO A DISPONIBILIDAD",
    "empresa": "WONDERTECH",
    "telefono": "304 6285091",
    "web": "reseller.wondertech.com.co",
    "direccion": "Cl. 99 #11B 66 OF 402 Chicó norte - Bogotá",
    "excluir_favoritos": True,
    "fecha_inicio_max": None,
    "fecha_fin_min": None,
    "categorias_incluidas": None,
    "marcas_incluidas": None,
    "precio_min": None,
    "precio_max": None,
    "max_productos": None,
}

# -------------------------------------------------------------
#  COLORES CORPORATIVOS WONDERTECH
# -------------------------------------------------------------
ROJO_W   = colors.HexColor("#DE1B60")
GRIS_OSC = colors.HexColor("#2C3E50")
GRIS_CLR = colors.HexColor("#ECF0F1")
BLANCO   = colors.white


# -------------------------------------------------------------
#  CARGA DE CREDENCIALES DESDE .ENV
# -------------------------------------------------------------
def str_to_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "si", "si", "on"}


def base_url_from_jsonrpc(jsonrpc_url):
    """Convierte https://empresa.odoo.com/jsonrpc -> https://empresa.odoo.com"""
    if not jsonrpc_url:
        return ""
    return jsonrpc_url.rstrip("/").removesuffix("/jsonrpc")


def cargar_credenciales_desde_env():
    """Lee el .env usando el selector USE_PRODUCTION."""
    use_production = str_to_bool(os.getenv("USE_PRODUCTION", "false"))
    prefijo = "PROD" if use_production else "TEST"

    jsonrpc_url  = os.getenv(f"{prefijo}_ODOO_JSONRPC", "").strip()
    db           = os.getenv(f"{prefijo}_ODOO_DB", "").strip()
    uid_raw      = os.getenv(f"{prefijo}_ODOO_UID", "").strip()
    password     = os.getenv(f"{prefijo}_ODOO_PASSWORD", "").strip()
    callback_url = os.getenv(f"{prefijo}_CALLBACK_URL", "").strip()

    faltantes = []
    if not jsonrpc_url: faltantes.append(f"{prefijo}_ODOO_JSONRPC")
    if not db:          faltantes.append(f"{prefijo}_ODOO_DB")
    if not uid_raw:     faltantes.append(f"{prefijo}_ODOO_UID")
    if not password:    faltantes.append(f"{prefijo}_ODOO_PASSWORD")

    if faltantes:
        raise Exception("Faltan variables en el .env: " + ", ".join(faltantes))

    try:
        uid = int(uid_raw)
    except ValueError as exc:
        raise Exception(f"{prefijo}_ODOO_UID debe ser numerico.") from exc

    return {
        "ambiente":     "PRODUCCION" if use_production else "PRUEBAS",
        "jsonrpc_url":  jsonrpc_url,
        "url":          base_url_from_jsonrpc(jsonrpc_url),
        "db":           db,
        "uid":          uid,
        "password":     password,
        "callback_url": callback_url,
    }


# -------------------------------------------------------------
#  CONEXION A ODOO VIA XML-RPC USANDO UID DESDE .ENV
# -------------------------------------------------------------
def conectar_odoo(url, db, uid, password):
    """Valida acceso y retorna el proxy de modelos de Odoo."""
    if not url:
        raise Exception("No se pudo derivar la URL base de Odoo desde *_ODOO_JSONRPC.")

    # Garantizar que uid sea entero
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        raise Exception(f"El UID debe ser un numero entero valido. Valor recibido: {uid!r}")

    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
        common.version()
    except Exception as exc:
        raise Exception(f"No se pudo conectar al servidor Odoo en {url}. Verifica la URL en el .env. Detalle: {exc}") from exc

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)

    try:
        usuario = models.execute_kw(
            db, uid, password, "res.users", "read", [[uid]], {"fields": ["name", "login"]}
        )
    except xmlrpc.client.Fault as fault:
        if fault.faultCode == 3:
            raise Exception(
                f"Acceso denegado en Odoo (Fault 3: Access Denied). "
                f"Verifica que las credenciales en el .env sean correctas:\n"
                f"  - UID usado: {uid}\n"
                f"  - Base de datos: {db}\n"
                f"  - URL: {url}\n"
                f"  - Asegurate de usar una API Key de Odoo (NO la contrasena web).\n"
                f"  Genera tu API Key en: Odoo > Configuracion > Usuarios > tu usuario > Claves API."
            ) from fault
        raise

    if not usuario:
        raise Exception("No fue posible validar el acceso con el UID y API Key del .env.")

    print(f"Conectado a Odoo como UID={uid} ({usuario[0].get('login', '')})")
    return models, uid


def buscar_lista(models, uid, cfg, nombre_lista=None, lista_id=None):
    """Busca una lista de precios por nombre o ID y retorna sus items y la moneda."""
    db, pw = cfg["db"], cfg["password"]

    domain = [["id", "=", int(lista_id)]] if lista_id is not None else [["name", "=", nombre_lista]]
    listas = models.execute_kw(
        db, uid, pw,
        "product.pricelist", "search_read",
        [domain],
        {"fields": ["id", "name", "currency_id"], "limit": 1},
    )
    if not listas:
        if lista_id is not None:
            print(f"Lista ID '{lista_id}' no encontrada en Odoo.")
        else:
            print(f"Lista '{nombre_lista}' no encontrada en Odoo.")
        return None, [], None

    lista    = listas[0]
    lista_id = lista["id"]
    nombre_lista = lista.get("name", nombre_lista)

    moneda         = cfg.get("moneda", "COP")
    simbolo_moneda = cfg.get("simbolo_moneda", "$")
    if lista.get("currency_id"):
        currency_id   = lista["currency_id"][0]
        currency_name = lista["currency_id"][1] if len(lista["currency_id"]) > 1 else ""

        currency_info = models.execute_kw(
            db, uid, pw,
            "res.currency", "read",
            [[currency_id]],
            {"fields": ["name", "symbol"]},
        )
        if currency_info:
            moneda         = currency_info[0].get("name", currency_name)
            simbolo_moneda = currency_info[0].get("symbol", currency_name)

    # ✅ CORREGIDO: "pricelist_id" sin espacio
    items_raw = models.execute_kw(
        db, uid, pw,
        "product.pricelist.item", "search_read",
        [[["pricelist_id", "=", lista_id]]],
        {
            "fields": [
                "product_tmpl_id",
                "product_id",
                "price",
                "fixed_price",
                "min_quantity",
                "date_start",
                "date_end",
                "applied_on",
            ],
            "limit": 2000,
        },
    )

    productos = []
    for item in items_raw:
        marca         = ""
        tipo_producto = ""
        es_favorito   = False
        tmpl_id       = None
        nombre_completo = ""
        sku_interno     = ""

        if item.get("product_id"):
            prod_id   = item["product_id"][0]
            prod_info = models.execute_kw(
                db, uid, pw,
                "product.product", "read",
                [[prod_id]],
                {"fields": ["name", "default_code", "categ_id", "product_tmpl_id"]},
            )
            if not prod_info:
                print(f"Producto ID {prod_id} no encontrado. Se omite.")
                continue

            prod_record     = prod_info[0]
            nombre_completo = prod_record.get("name") or ""
            sku_interno     = prod_record.get("default_code") or ""
            tmpl_id = (
                prod_record.get("product_tmpl_id", [None])[0]
                if prod_record.get("product_tmpl_id")
                else None
            )

        elif item.get("product_tmpl_id"):
            tmpl_id   = item["product_tmpl_id"][0]
            tmpl_info = models.execute_kw(
                db, uid, pw,
                "product.template", "read",
                [[tmpl_id]],
                {
                    "fields": [
                        "name",
                        "default_code",
                        "categ_id",
                        "x_studio_marca",
                        "x_studio_selection_field_6ob_1j1gf5dtp",
                        "is_favorite",
                    ]
                },
            )
            if not tmpl_info:
                print(f"Template ID {tmpl_id} no encontrado. Se omite.")
                continue

            tmpl_record     = tmpl_info[0]
            nombre_completo = tmpl_record.get("name") or ""
            sku_interno     = tmpl_record.get("default_code") or ""
            marca           = tmpl_record.get("x_studio_marca") or ""
            tipo_producto   = tmpl_record.get("x_studio_selection_field_6ob_1j1gf5dtp") or ""
            es_favorito     = tmpl_record.get("is_favorite", False)
        else:
            continue

        if tmpl_id and (not tipo_producto or not marca or not es_favorito):
            tmpl_info = models.execute_kw(
                db, uid, pw,
                "product.template", "read",
                [[tmpl_id]],
                {
                    "fields": [
                        "x_studio_marca",
                        "x_studio_selection_field_6ob_1j1gf5dtp",
                        "is_favorite",
                    ]
                },
            )
            if tmpl_info:
                tmpl_record = tmpl_info[0]
                if not marca:
                    marca = tmpl_record.get("x_studio_marca") or ""
                if not tipo_producto:
                    tipo_producto = tmpl_record.get("x_studio_selection_field_6ob_1j1gf5dtp") or ""
                if not es_favorito:
                    es_favorito = tmpl_record.get("is_favorite", False)

        marca, sku, descripcion = parsear_producto(nombre_completo, sku_interno, marca)
        categoria_final = tipo_producto if tipo_producto else "SIN CATEGORIA"
        precio          = item.get("fixed_price") or item.get("price") or 0
        fecha_inicio    = item.get("date_start") or ""
        fecha_fin       = item.get("date_end") or ""

        if cfg.get("excluir_favoritos") and es_favorito:
            continue
        if cfg.get("fecha_inicio_max") and fecha_inicio:
            if fecha_inicio > cfg["fecha_inicio_max"]:
                continue
        if cfg.get("fecha_fin_min") and fecha_fin:
            if fecha_fin < cfg["fecha_fin_min"]:
                continue
        if cfg.get("categorias_incluidas"):
            if categoria_final.upper() not in [c.upper() for c in cfg["categorias_incluidas"]]:
                continue
        if cfg.get("marcas_incluidas"):
            if marca.upper() not in [m.upper() for m in cfg["marcas_incluidas"]]:
                continue
        if cfg.get("precio_min") is not None:
            if precio < cfg["precio_min"]:
                continue
        if cfg.get("precio_max") is not None:
            if precio > cfg["precio_max"]:
                continue

        productos.append(
            {
                "marca":        marca,
                "sku":          sku,
                "descripcion":  descripcion,
                "categoria":    categoria_final,
                "precio":       precio,
                "cantidad_min": item.get("min_quantity") or 0,
                "fecha_inicio": fecha_inicio,
                "fecha_fin":    fecha_fin,
            }
        )

        if cfg.get("max_productos") and len(productos) >= cfg["max_productos"]:
            break

    print(f"'{nombre_lista}': {len(productos)} productos cargados. Moneda: {moneda} ({simbolo_moneda})")
    return lista, productos, {"name": moneda, "symbol": simbolo_moneda}


# -------------------------------------------------------------
#  PARSER DE NOMBRES DE PRODUCTO
# -------------------------------------------------------------
MARCAS_CONOCIDAS = [
    "HP/POLY", "HP", "LENOVO", "DELL", "ASUS", "APPLE", "SAMSUNG",
    "ADATA", "XUE", "GENERICO", "X-KIM", "KIOXIA", "SKHYNIX",
    "GENIUS", "TELTONIKA", "LENOVO-REFURBISHED",
]


def parsear_producto(nombre, sku_campo="", marca_odoo=""):
    nombre      = (nombre or "").strip()
    sku         = sku_campo.strip() if sku_campo else ""
    marca       = marca_odoo.strip() if marca_odoo else ""
    descripcion = nombre

    match_sku = re.match(r"^\[([^\]]+)\]\s*", nombre)
    if match_sku:
        if not sku:
            sku = match_sku.group(1).strip()
        descripcion = nombre[match_sku.end():]

    if sku and descripcion.upper().startswith(sku.upper()):
        descripcion = descripcion[len(sku):].strip()
        if descripcion.startswith(("-", ",", ":")):
            descripcion = descripcion[1:].strip()

    if marca:
        descripcion = descripcion.strip()
        if descripcion.startswith(("-", ":")):
            descripcion = descripcion[1:].strip()
    else:
        desc_upper = descripcion.upper()
        for m in sorted(MARCAS_CONOCIDAS, key=len, reverse=True):
            if desc_upper.startswith(m.upper()):
                marca       = m
                descripcion = descripcion[len(m):].strip()
                if descripcion.startswith(("-", ":")):
                    descripcion = descripcion[1:].strip()
                break

        if not marca and descripcion:
            partes = descripcion.split()
            if len(partes) > 1:
                marca       = partes[0]
                descripcion = " ".join(partes[1:])

    return marca.upper(), sku, descripcion.strip()


def formatear_precio(precio, simbolo="$"):
    if not precio:
        return f"{simbolo} 0"
    return f"{simbolo} {precio:,.0f}".replace(",", ".")


# -------------------------------------------------------------
#  GENERACION DEL PDF - DISENO PROFESIONAL
# -------------------------------------------------------------
def generar_pdf(nombre_lista, productos, cfg, save_to_disk=True):
    nombre_archivo = f"Lista_{nombre_lista.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "PDFs", "output"
    )
    ruta_completa = os.path.join(output_dir, nombre_archivo)
    output_target = ruta_completa
    buffer = None

    if save_to_disk:
        os.makedirs(output_dir, exist_ok=True)
    else:
        buffer = io.BytesIO()
        output_target = buffer

    img_header = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDFs", "img", "Captura de pantalla 2026-04-09 142117.png")
    img_footer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDFs", "img", "Captura de pantalla 2026-04-09 142259.png")

    doc = SimpleDocTemplate(
        output_target,
        pagesize=landscape(A4),
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=6.5 * cm,
        bottomMargin=3.7 * cm,
        title=f"Lista de Precios - {nombre_lista}",
        author=cfg["empresa"],
    )

    story = []

    col_widths = [
        3.0 * cm,
        3.0 * cm,
        16.4 * cm,
        1.8 * cm,
        3.5 * cm,
    ]

    header_style = ParagraphStyle(
        "hdr", fontSize=7.5, fontName="Helvetica-Bold",
        textColor=BLANCO, alignment=TA_CENTER, leading=9.5
    )
    vigencia_style = ParagraphStyle(
        "vigencia", fontSize=7.5, textColor=BLANCO,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )

    fila_vigencia = [Paragraph(cfg["vigencia"], vigencia_style), "", "", "", ""]

    encabezado = [
        Paragraph("MARCA",                           header_style),
        Paragraph("SKU",                              header_style),
        Paragraph("DESCRIPCION",                      header_style),
        Paragraph("TIPO\nMONEDA",                     header_style),
        Paragraph("PRECIO IVA\nINCLUIDO SI\nAPLICA",  header_style),
    ]

    filas = [fila_vigencia, encabezado]

    cell_style  = ParagraphStyle("cell",   fontSize=7.5, fontName="Helvetica",      leading=9.5)
    cell_center = ParagraphStyle("cell_c", fontSize=7.5, fontName="Helvetica",      leading=9.5, alignment=TA_CENTER)
    price_style = ParagraphStyle("price",  fontSize=8.5, fontName="Helvetica-Bold", leading=10,  alignment=TA_RIGHT, textColor=GRIS_OSC)
    cat_style   = ParagraphStyle("cat",    fontSize=8,   fontName="Helvetica-Bold", leading=10,  textColor=BLANCO,   alignment=TA_CENTER)

    productos_por_categoria = defaultdict(list)
    for p in productos:
        cat = p["categoria"] if p["categoria"] else "SIN CATEGORIA"
        productos_por_categoria[cat].append(p)

    c_moneda = cfg.get("moneda", "COP")

    for categoria, productos_cat in sorted(productos_por_categoria.items()):
        filas.append([Paragraph(categoria.upper(), cat_style), "", "", "", ""])
        for p in productos_cat:
            fila = [
                Paragraph(p["marca"],                                                      cell_center),
                Paragraph(p["sku"],                                                        cell_center),
                Paragraph(p["descripcion"],                                                cell_style),
                Paragraph(c_moneda,                                                        cell_center),
                Paragraph(formatear_precio(p["precio"], cfg.get("simbolo_moneda", "$")),   price_style),
            ]
            filas.append(fila)

    tabla = Table(filas, colWidths=col_widths, repeatRows=2)

    style_rules = [
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND",    (0, 0), (-1, 0),  ROJO_W),
        ("SPAN",          (0, 0), (-1, 0)),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0),  "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, 0),  3),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  3),
        ("BACKGROUND",    (0, 1), (-1, 1),  ROJO_W),
        ("ALIGN",         (0, 1), (-1, 1),  "CENTER"),
        ("VALIGN",        (0, 1), (-1, 1),  "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, 1),  6),
        ("BOTTOMPADDING", (0, 1), (-1, 1),  6),
        ("FONTSIZE",      (0, 2), (-1, -1), 7.5),
        ("VALIGN",        (0, 2), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 2), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 2), (-1, -1), 2.5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
    ]

    row_idx = 2
    for categoria, productos_cat in sorted(productos_por_categoria.items()):
        style_rules.append(("BACKGROUND",    (0, row_idx), (-1, row_idx), ROJO_W))
        style_rules.append(("SPAN",          (0, row_idx), (-1, row_idx)))
        style_rules.append(("TOPPADDING",    (0, row_idx), (-1, row_idx), 0.5))
        style_rules.append(("BOTTOMPADDING", (0, row_idx), (-1, row_idx), 0.5))
        row_idx += 1
        for i in range(len(productos_cat)):
            style_rules.append(("BACKGROUND", (0, row_idx), (-1, row_idx), BLANCO))
            style_rules.append(("LINEBELOW",  (0, row_idx), (-1, row_idx), 0.5, colors.HexColor("#E5E7E9")))
            row_idx += 1

    tabla.setStyle(TableStyle(style_rules))
    story.append(tabla)

    from reportlab.lib.utils import ImageReader

    def draw_backgrounds(canvas, doc):
        canvas.saveState()
        page_w = doc.pagesize[0]
        page_h = doc.pagesize[1]
        draw_w  = page_w - doc.leftMargin - doc.rightMargin
        start_x = doc.leftMargin

        if os.path.exists(img_header):
            try:
                img_reader = ImageReader(img_header)
                img_w, img_h = img_reader.getSize()
                draw_h  = draw_w * img_h / img_w * 0.90
                start_y = page_h - draw_h - 0.3 * cm
                canvas.drawImage(img_reader, start_x, start_y, width=draw_w, height=draw_h, mask="auto")
            except Exception:
                pass

        if os.path.exists(img_footer):
            try:
                img_reader = ImageReader(img_footer)
                img_w, img_h = img_reader.getSize()
                draw_h  = draw_w * img_h / img_w * 0.90
                canvas.drawImage(img_reader, start_x, 0.4 * cm, width=draw_w, height=draw_h, mask="auto")
            except Exception:
                pass

        canvas.restoreState()

    def on_page_cb(canvas, doc):
        draw_backgrounds(canvas, doc)

    doc.build(story, onFirstPage=on_page_cb, onLaterPages=on_page_cb)
    if save_to_disk:
        print(f"PDF generado: PDFs/output/{nombre_archivo}")
        with open(ruta_completa, "rb") as f:
            raw_bytes = f.read()
    else:
        raw_bytes = buffer.getvalue()
        print(f"PDF generado en memoria: {nombre_archivo}")

    return nombre_archivo, raw_bytes


# -------------------------------------------------------------
#  MAIN
# -------------------------------------------------------------
import sys


def main():
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    try:
        cred = cargar_credenciales_desde_env()
    except Exception as e:
        print(f"\nError cargando .env: {e}\n")
        return

    cfg = {**CONFIG, **cred}

    print("\n" + "=" * 55)
    print("  WONDERTECH - Generador de Listas de Precios")
    print("=" * 55)
    print(f"Ambiente seleccionado: {cfg['ambiente']}")
    print(f"JSON-RPC: {cfg['jsonrpc_url']}")
    print(f"Base de datos: {cfg['db']}")

    try:
        models, uid = conectar_odoo(cfg["url"], cfg["db"], cfg["uid"], cfg["password"])
    except Exception as e:
        print(f"\n{e}")
        return

    archivos = []
    for nombre_lista in cfg["listas"]:
        print(f"\nProcesando: {nombre_lista}...")
        lista_info, productos, moneda_info = buscar_lista(models, uid, cfg, nombre_lista)

        if productos:
            moneda_cfg = {
                "moneda":         moneda_info["name"],
                "simbolo_moneda": moneda_info["symbol"],
            }
            # ✅ generar_pdf retorna (nombre_archivo, raw_bytes)
            archivo, _ = generar_pdf(nombre_lista, productos, {**cfg, **moneda_cfg})
            archivos.append(archivo)
        else:
            print("  Sin productos - se omite el PDF.")

    print("\n" + "=" * 55)
    print(f"Proceso completado. PDFs generados: {len(archivos)}")
    for a in archivos:
        print(f"   {a}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
