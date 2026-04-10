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
from collections import defaultdict
import xmlrpc.client
from datetime import datetime

from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Cargar variables del archivo .env
load_dotenv()

# ─────────────────────────────────────────────────────────────
#  ⚙️  CONFIGURACIÓN GENERAL (sin credenciales)
# ─────────────────────────────────────────────────────────────
CONFIG = {
    # Nombres exactos de las listas de precios en Odoo
    "listas": ["Lista Business", "Lista Reseller"],
    # Ciudad por defecto (se obtiene de Odoo, esto es fallback)
    # "ciudad": "BOGOTA",
    # Vigencia (texto que aparece en el banner del PDF)
    # ⚠️  ESTO ES DIFERENTE al filtro de fecha:
    #   - vigencia: Texto informativo que se muestra en el PDF
    #   - fecha_inicio_max/fecha_fin_min: Filtros para incluir/excluir productos
    "vigencia": "VIGENCIA: 01/04/2026 — 18/04/2026 | IVA INCLUIDO | SUJETO A DISPONIBILIDAD",
    # Footer
    "empresa": "WONDERTECH",
    "telefono": "304 6285091",
    "web": "reseller.wondertech.com.co",
    "direccion": "Cl. 99 #11B 66 OF 402 Chico norte - Bogotá",
    # ═══════════════════════════════════════════════════════════
    # 🔧  FILTROS DE PRODUCTOS
    # ═══════════════════════════════════════════════════════════
    # ⭐  FILTRO PRINCIPAL: Favoritos (POR DEFECTO: True = excluir favoritos)
    # Si es True, solo se incluyen productos donde is_favorite = False
    # Los productos marcados como favoritos (estrella) NO aparecen en el PDF
    "excluir_favoritos": True,  # ⭐ Por defecto: NO incluir productos favoritos
    # 📅  Filtro por fecha (None = sin filtro, o formato "YYYY-MM-DD")
    # Solo incluye productos con fecha_inicio <= fecha_actual <= fecha_fin
    # Ej: "fecha_inicio_max": "2026-04-18" (productos que inician antes de esta fecha)
    "fecha_inicio_max": None,  # Productos que inician antes de esta fecha
    "fecha_fin_min": None,  # Productos que terminan después de esta fecha
    # 📂  Filtro por categorías (None o lista vacía = todas las categorías)
    # Ej: ["ACCESORIOS", "AUDIO", "CABLES"]
    "categorias_incluidas": None,
    # 🏷️  Filtro por marcas (None o lista vacía = todas las marcas)
    # Ej: ["HP", "LENOVO", "DELL", "ASUS"]
    "marcas_incluidas": None,
    # 💰  Filtro por rango de precios (None = sin límite)
    "precio_min": None,  # Precio mínimo (None = sin mínimo)
    "precio_max": None,  # Precio máximo (None = sin máximo)
    # 🔢  Límite máximo de productos (None = todos)
    "max_productos": None,  # Número máximo de productos por lista
}

# ─────────────────────────────────────────────────────────────
#  🎨  COLORES CORPORATIVOS WONDERTECH
# ─────────────────────────────────────────────────────────────
ROJO_W = colors.HexColor("#DE1B60")  # Magenta moderno Wondertech
GRIS_OSC = colors.HexColor("#2C3E50")
GRIS_CLR = colors.HexColor("#ECF0F1")
BLANCO = colors.white


# ─────────────────────────────────────────────────────────────
#  🔐 CARGA DE CREDENCIALES DESDE .ENV
# ─────────────────────────────────────────────────────────────
def str_to_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def base_url_from_jsonrpc(jsonrpc_url):
    """Convierte https://empresa.odoo.com/jsonrpc -> https://empresa.odoo.com"""
    if not jsonrpc_url:
        return ""
    return jsonrpc_url.rstrip("/").removesuffix("/jsonrpc")


def cargar_credenciales_desde_env():
    """Lee el .env usando el selector USE_PRODUCTION."""
    use_production = str_to_bool(os.getenv("USE_PRODUCTION", "false"))
    prefijo = "PROD" if use_production else "TEST"

    jsonrpc_url = os.getenv(f"{prefijo}_ODOO_JSONRPC", "").strip()
    db = os.getenv(f"{prefijo}_ODOO_DB", "").strip()
    uid_raw = os.getenv(f"{prefijo}_ODOO_UID", "").strip()
    password = os.getenv(f"{prefijo}_ODOO_PASSWORD", "").strip()
    callback_url = os.getenv(f"{prefijo}_CALLBACK_URL", "").strip()

    faltantes = []
    if not jsonrpc_url:
        faltantes.append(f"{prefijo}_ODOO_JSONRPC")
    if not db:
        faltantes.append(f"{prefijo}_ODOO_DB")
    if not uid_raw:
        faltantes.append(f"{prefijo}_ODOO_UID")
    if not password:
        faltantes.append(f"{prefijo}_ODOO_PASSWORD")

    if faltantes:
        raise Exception("Faltan variables en el .env: " + ", ".join(faltantes))

    try:
        uid = int(uid_raw)
    except ValueError as exc:
        raise Exception(f"{prefijo}_ODOO_UID debe ser numérico.") from exc

    return {
        "ambiente": "PRODUCCIÓN" if use_production else "PRUEBAS",
        "jsonrpc_url": jsonrpc_url,
        "url": base_url_from_jsonrpc(jsonrpc_url),
        "db": db,
        "uid": uid,
        "password": password,
        "callback_url": callback_url,
    }


# ─────────────────────────────────────────────────────────────
#  🔌  CONEXIÓN A ODOO VÍA XML-RPC USANDO UID DESDE .ENV
# ─────────────────────────────────────────────────────────────
def conectar_odoo(url, db, uid, password):
    """Valida acceso y retorna el proxy de modelos de Odoo."""
    if not url:
        raise Exception(
            "❌ No se pudo derivar la URL base de Odoo desde *_ODOO_JSONRPC."
        )

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    common.version()  # valida conectividad básica

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)

    # Validación simple usando el UID del .env
    usuario = models.execute_kw(
        db, uid, password, "res.users", "read", [[uid]], {"fields": ["name", "login"]}
    )

    if not usuario:
        raise Exception(
            "❌ No fue posible validar el acceso con el UID y API Key del .env."
        )

    print(f"✅ Conectado a Odoo como UID={uid} ({usuario[0].get('login', '')})")
    return models, uid


def buscar_lista(models, uid, cfg, nombre_lista):
    """Busca una lista de precios por nombre y retorna sus ítems y la moneda."""
    db, pw = cfg["db"], cfg["password"]

    listas = models.execute_kw(
        db,
        uid,
        pw,
        "product.pricelist",
        "search_read",
        [[["name", "=", nombre_lista]]],
        {"fields": ["id", "name", "currency_id"], "limit": 1},
    )
    if not listas:
        print(f"⚠️  Lista '{nombre_lista}' no encontrada en Odoo.")
        return None, [], None

    lista = listas[0]
    lista_id = lista["id"]

    # Obtener información de la moneda desde currency_id
    moneda = cfg.get("moneda", "COP")  # valor por defecto
    simbolo_moneda = cfg.get("simbolo_moneda", "$")  # valor por defecto
    if lista.get("currency_id"):
        currency_id = lista["currency_id"][0]
        currency_name = lista["currency_id"][1] if len(lista["currency_id"]) > 1 else ""

        # Leer detalles de la moneda desde res.currency
        currency_info = models.execute_kw(
            db,
            uid,
            pw,
            "res.currency",
            "read",
            [[currency_id]],
            {"fields": ["name", "symbol"]},
        )
        if currency_info:
            moneda = currency_info[0].get("name", currency_name)
            simbolo_moneda = currency_info[0].get("symbol", currency_name)

    items_raw = models.execute_kw(
        db,
        uid,
        pw,
        "product.pricelist.item",
        "search_read",
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
        if item.get("product_id"):
            prod_id = item["product_id"][0]
            prod_info = models.execute_kw(
                db,
                uid,
                pw,
                "product.product",
                "read",
                [[prod_id]],
                {"fields": ["name", "default_code", "categ_id", "product_tmpl_id"]},
            )
            nombre_completo = prod_info[0]["name"] if prod_info else ""
            sku_interno = prod_info[0].get("default_code") or ""
            categ_id = prod_info[0].get("categ_id")
            tmpl_id = (
                prod_info[0].get("product_tmpl_id", [None])[0]
                if prod_info[0].get("product_tmpl_id")
                else None
            )
            es_favorito = False  # Se obtiene del template más abajo
            tipo_producto = ""  # Se obtiene más abajo del template
        elif item.get("product_tmpl_id"):
            tmpl_id = item["product_tmpl_id"][0]
            tmpl_info = models.execute_kw(
                db,
                uid,
                pw,
                "product.template",
                "read",
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
            nombre_completo = tmpl_info[0]["name"] if tmpl_info else ""
            sku_interno = tmpl_info[0].get("default_code") or ""
            categ_id = tmpl_info[0].get("categ_id")
            marca = tmpl_info[0].get("x_studio_marca") or ""
            tipo_producto = (
                tmpl_info[0].get("x_studio_selection_field_6ob_1j1gf5dtp") or ""
            )
            es_favorito = tmpl_info[0].get("is_favorite", False)
        else:
            continue

        # Obtener tipo de producto y favorito desde el template
        if not tipo_producto and tmpl_id:
            tmpl_info = models.execute_kw(
                db,
                uid,
                pw,
                "product.template",
                "read",
                [[tmpl_id]],
                {"fields": ["x_studio_selection_field_6ob_1j1gf5dtp", "is_favorite"]},
            )
            if tmpl_info:
                if not tipo_producto:
                    tipo_producto = (
                        tmpl_info[0].get("x_studio_selection_field_6ob_1j1gf5dtp") or ""
                    )
                if not es_favorito:
                    es_favorito = tmpl_info[0].get("is_favorite", False)

        marca, sku, descripcion = parsear_producto(nombre_completo, sku_interno, marca)
        categoria_final = tipo_producto if tipo_producto else "SIN CATEGORÍA"
        precio = item.get("fixed_price") or item.get("price") or 0
        fecha_inicio = item.get("date_start") or ""
        fecha_fin = item.get("date_end") or ""

        # ═══════════════════════════════════════════════════════
        # 🔧  APLICACIÓN DE FILTROS
        # ═══════════════════════════════════════════════════════

        # ⭐  FILTRO PRINCIPAL: Excluir favoritos (estrella marcada)
        if cfg.get("excluir_favoritos") and es_favorito:
            continue  # Producto es favorito, NO incluirlo en el PDF

        # 📅  Filtro por fecha
        if cfg.get("fecha_inicio_max") and fecha_inicio:
            if fecha_inicio > cfg["fecha_inicio_max"]:
                continue  # Producto inicia después de la fecha límite
        if cfg.get("fecha_fin_min") and fecha_fin:
            if fecha_fin < cfg["fecha_fin_min"]:
                continue  # Producto termina antes de la fecha mínima

        # 📂  Filtro por categorías
        if cfg.get("categorias_incluidas"):
            if categoria_final.upper() not in [
                c.upper() for c in cfg["categorias_incluidas"]
            ]:
                continue

        # 🏷️  Filtro por marcas
        if cfg.get("marcas_incluidas"):
            if marca.upper() not in [m.upper() for m in cfg["marcas_incluidas"]]:
                continue

        # 💰  Filtro por rango de precios
        if cfg.get("precio_min") is not None:
            if precio < cfg["precio_min"]:
                continue
        if cfg.get("precio_max") is not None:
            if precio > cfg["precio_max"]:
                continue

        # 📦  Agregar producto filtrado
        productos.append(
            {
                "marca": marca,
                "sku": sku,
                "descripcion": descripcion,
                "categoria": categoria_final,
                "precio": precio,
                "cantidad_min": item.get("min_quantity") or 0,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            }
        )

        # 🔢  Verificar límite máximo de productos
        if cfg.get("max_productos") and len(productos) >= cfg["max_productos"]:
            break

    print(
        f"✅ '{nombre_lista}': {len(productos)} productos cargados. Moneda: {moneda} ({simbolo_moneda})"
    )
    return lista, productos, {"name": moneda, "symbol": simbolo_moneda}


# ─────────────────────────────────────────────────────────────
#  🔍  PARSER DE NOMBRES DE PRODUCTO
# ─────────────────────────────────────────────────────────────
MARCAS_CONOCIDAS = [
    "HP/POLY",
    "HP",
    "LENOVO",
    "DELL",
    "ASUS",
    "APPLE",
    "SAMSUNG",
    "ADATA",
    "XUE",
    "GENERICO",
    "X-KIM",
    "KIOXIA",
    "SKHYNIX",
    "GENIUS",
    "TELTONIKA",
    "LENOVO-REFURBISHED",
]


def parsear_producto(nombre, sku_campo="", marca_odoo=""):
    nombre = (nombre or "").strip()
    sku = sku_campo.strip() if sku_campo else ""
    marca = marca_odoo.strip() if marca_odoo else ""
    descripcion = nombre

    match_sku = re.match(r"^\[([^\]]+)\]\s*", nombre)
    if match_sku:
        if not sku:
            sku = match_sku.group(1).strip()
        descripcion = nombre[match_sku.end() :]

    # Remover SKU del inicio de la descripción si está presente
    if sku and descripcion.upper().startswith(sku.upper()):
        descripcion = descripcion[len(sku) :].strip()
        if descripcion.startswith(("-", ",", ":")):
            descripcion = descripcion[1:].strip()

    # Si ya tenemos la marca desde Odoo, solo limpiar descripción
    if marca:
        descripcion = descripcion.strip()
        if descripcion.startswith(("-", ":")):
            descripcion = descripcion[1:].strip()
    else:
        # Fallback: intentar extraer marca del nombre
        desc_upper = descripcion.upper()
        for m in sorted(MARCAS_CONOCIDAS, key=len, reverse=True):
            if desc_upper.startswith(m.upper()):
                marca = m
                descripcion = descripcion[len(m) :].strip()
                if descripcion.startswith(("-", ":")):
                    descripcion = descripcion[1:].strip()
                break

        if not marca and descripcion:
            partes = descripcion.split()
            if len(partes) > 1:
                marca = partes[0]
                descripcion = " ".join(partes[1:])

    return marca.upper(), sku, descripcion.strip()


def formatear_precio(precio, simbolo="$"):
    if not precio:
        return f"{simbolo} 0"
    return f"{simbolo} {precio:,.0f}".replace(",", ".")


# ─────────────────────────────────────────────────────────────
#  📄  GENERACIÓN DEL PDF - DISEÑO PROFESIONAL
# ─────────────────────────────────────────────────────────────
def generar_pdf(nombre_lista, productos, cfg):
    # Crear directorio de salida si no existe
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "PDFs", "output"
    )
    os.makedirs(output_dir, exist_ok=True)

    nombre_archivo = f"Lista_{nombre_lista.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    ruta_completa = os.path.join(output_dir, nombre_archivo)

    # Rutas de las imágenes proveídas por el usuario
    img_header = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDFs", "img", "Captura de pantalla 2026-04-09 142117.png")
    img_footer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDFs", "img", "Captura de pantalla 2026-04-09 142259.png")

    doc = SimpleDocTemplate(
        ruta_completa,
        pagesize=landscape(A4),
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=7.2 * cm,    # Ajustado a proporción exacta de la imagen (6.93cm)
        bottomMargin=3.8 * cm, # Ajustado a proporción exacta del footer (3.6cm)
        title=f"Lista de Precios - {nombre_lista}",
        author=cfg["empresa"],
    )

    story = []

    # ── TABLA OPTIMIZADA DE ACUERDO A LA REFERENCIA VISUAL ──
    col_widths = [
        3.0 * cm,   # MARCA
        3.0 * cm,   # SKU
        14.2 * cm,  # DESCRIPCIÓN 
        2.2 * cm,   # CIUDAD
        1.8 * cm,   # TIPO MONEDA
        3.5 * cm,   # PRECIO
    ]

    header_style = ParagraphStyle(
        "hdr", fontSize=7.5, fontName="Helvetica-Bold",
        textColor=BLANCO, alignment=TA_CENTER, leading=9.5
    )
    
    vigencia_style = ParagraphStyle(
        "vigencia", fontSize=7.5, textColor=BLANCO,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )

    # Fila 0: Vigencia (abarcando todas las columnas, fondo rojo)
    fila_vigencia = [Paragraph(cfg["vigencia"], vigencia_style), "", "", "", "", ""]

    # Fila 1: Nombres de columnas
    encabezado = [
        Paragraph("MARCA", header_style),
        Paragraph("SKU", header_style),
        Paragraph("DESCRIPCIÓN", header_style),
        Paragraph("CIUDAD", header_style),
        Paragraph("TIPO\nMONEDA", header_style),
        Paragraph("PRECIO IVA\nINCLUIDO SI\nAPLICA", header_style),
    ]

    filas = [fila_vigencia, encabezado]
    
    # Estilos de celda
    cell_style = ParagraphStyle("cell", fontSize=7.5, fontName="Helvetica", leading=9.5)
    cell_center = ParagraphStyle("cell_c", fontSize=7.5, fontName="Helvetica", leading=9.5, alignment=TA_CENTER)
    price_style = ParagraphStyle("price", fontSize=8.5, fontName="Helvetica-Bold", leading=10, alignment=TA_RIGHT, textColor=GRIS_OSC)
    cat_style = ParagraphStyle("cat", fontSize=8, fontName="Helvetica-Bold", leading=10, textColor=BLANCO, alignment=TA_CENTER)

    # Agrupar productos por categoría
    productos_por_categoria = defaultdict(list)
    for p in productos:
        cat = p["categoria"] if p["categoria"] else "SIN CATEGORÍA"
        productos_por_categoria[cat].append(p)

    c_ciudad = cfg.get("ciudad", "BOGOTA")
    c_moneda = cfg.get("moneda", "COP")

    # Construir filas
    for categoria, productos_cat in sorted(productos_por_categoria.items()):
        # Fila separadora de categoría
        filas.append([Paragraph(categoria.upper(), cat_style), "", "", "", "", ""])

        # Filas de productos
        for p in productos_cat:
            fila = [
                Paragraph(p["marca"], cell_center),
                Paragraph(p["sku"], cell_center),
                Paragraph(p["descripcion"], cell_style),
                Paragraph(c_ciudad, cell_center),
                Paragraph(c_moneda, cell_center),
                Paragraph(formatear_precio(p["precio"], cfg.get("simbolo_moneda", "$")), price_style),
            ]
            filas.append(fila)

    # Crear tabla
    tabla = Table(filas, colWidths=col_widths, repeatRows=2)

    # ── ESTILOS DINÁMICOS DE TABLA ──
    style_rules = [
        # Grid general (Bordes negros como en la imagen)
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        
        # Vigencia Row (Row 0)
        ("BACKGROUND", (0, 0), (-1, 0), ROJO_W),
        ("SPAN", (0, 0), (-1, 0)),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        
        # Headers Row (Row 1)
        ("BACKGROUND", (0, 1), (-1, 1), ROJO_W),
        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
        ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),

        # Formato de variables
        ("FONTSIZE", (0, 2), (-1, -1), 7.5),
        ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 2), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 2), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]

    # Aplicar estilos por fila (Categorias y Productos)
    row_idx = 2
    for categoria, productos_cat in sorted(productos_por_categoria.items()):
        # Estilo para fila de categoría (Más delgada y fondo rojo)
        style_rules.append(("BACKGROUND", (0, row_idx), (-1, row_idx), ROJO_W))
        style_rules.append(("SPAN", (0, row_idx), (-1, row_idx)))
        style_rules.append(("TOPPADDING", (0, row_idx), (-1, row_idx), 0.5))  # Muy delgada
        style_rules.append(("BOTTOMPADDING", (0, row_idx), (-1, row_idx), 0.5)) # Muy delgada
        row_idx += 1

        for i in range(len(productos_cat)):
            bg_color = BLANCO
            style_rules.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg_color))
            style_rules.append(
                (
                    "LINEBELOW",
                    (0, row_idx),
                    (-1, row_idx),
                    0.5,
                    colors.HexColor("#E5E7E9"),
                )
            )
            row_idx += 1

    tabla.setStyle(TableStyle(style_rules))
    story.append(tabla)

    # ── HANDLERS PARA IMÁGENES DE HEADER Y FOOTER ──
    from reportlab.lib.utils import ImageReader

    def draw_backgrounds(canvas, doc):
        canvas.saveState()
        width = doc.pagesize[0]
        height = doc.pagesize[1]
        
        # Dibujar Imagen del Header (oficina + curva)
        if os.path.exists(img_header):
            try:
                img_reader = ImageReader(img_header)
                img_w, img_h = img_reader.getSize()
                draw_h = width * img_h / img_w
                canvas.drawImage(img_reader, 0, height - draw_h, width=width, height=draw_h, mask='auto')
            except Exception as e:
                print(f"Error dibujando header: {e}")

        # Dibujar Imagen del Footer (logos marcas)
        if os.path.exists(img_footer):
            try:
                img_reader = ImageReader(img_footer)
                img_w, img_h = img_reader.getSize()
                draw_h = width * img_h / img_w
                canvas.drawImage(img_reader, 0, 0, width=width, height=draw_h, mask='auto')
            except Exception as e:
                print(f"Error dibujando footer: {e}")

        canvas.restoreState()

    def on_page_cb(canvas, doc):
        draw_backgrounds(canvas, doc)

    doc.build(story, onFirstPage=on_page_cb, onLaterPages=on_page_cb)
    print(f"✅ PDF generado: PDFs/output/{nombre_archivo}")
    return nombre_archivo


# ─────────────────────────────────────────────────────────────
#  🚀  MAIN
# ─────────────────────────────────────────────────────────────
import sys

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    try:
        cred = cargar_credenciales_desde_env()
    except Exception as e:
        print(f"\n❌ Error cargando .env: {e}\n")
        return

    cfg = {**CONFIG, **cred}

    print("\n" + "=" * 55)
    print("  WONDERTECH — Generador de Listas de Precios")
    print("=" * 55)
    print(f"🌐 Ambiente seleccionado: {cfg['ambiente']}")
    print(f"🔗 JSON-RPC: {cfg['jsonrpc_url']}")
    print(f"🗄️  Base de datos: {cfg['db']}")

    # Mostrar filtros activos
    print("\n🔧  Filtros configurados:")
    filtros_activos = []

    # ⭐ Filtro principal: Favoritos
    if cfg.get("excluir_favoritos"):
        filtros_activos.append("⭐ Excluir favoritos (estrella)")
    else:
        filtros_activos.append("⭐ Incluir todos (favoritos + no favoritos)")

    if cfg.get("fecha_inicio_max"):
        filtros_activos.append(f"Fecha inicio máx: {cfg['fecha_inicio_max']}")
    if cfg.get("fecha_fin_min"):
        filtros_activos.append(f"Fecha fin mín: {cfg['fecha_fin_min']}")
    if cfg.get("categorias_incluidas"):
        filtros_activos.append(f"Categorías: {', '.join(cfg['categorias_incluidas'])}")
    if cfg.get("marcas_incluidas"):
        filtros_activos.append(f"Marcas: {', '.join(cfg['marcas_incluidas'])}")
    if cfg.get("precio_min") is not None:
        filtros_activos.append(f"Precio mín: ${cfg['precio_min']:,.0f}")
    if cfg.get("precio_max") is not None:
        filtros_activos.append(f"Precio máx: ${cfg['precio_max']:,.0f}")
    if cfg.get("max_productos"):
        filtros_activos.append(f"Máx productos: {cfg['max_productos']}")

    if filtros_activos:
        for f in filtros_activos:
            print(f"   ✓ {f}")
    else:
        print("   ⚠️  Sin filtros (todos los productos)")

    try:
        models, uid = conectar_odoo(cfg["url"], cfg["db"], cfg["uid"], cfg["password"])
    except Exception as e:
        print(f"\n{e}")
        print("\nVerifica:")
        print("  • USE_PRODUCTION en el .env")
        print("  • *_ODOO_JSONRPC")
        print("  • *_ODOO_DB")
        print("  • *_ODOO_UID")
        print("  • *_ODOO_PASSWORD (API Key)")
        return

    archivos = []
    for nombre_lista in cfg["listas"]:
        print(f"\n📋 Procesando: {nombre_lista}...")
        lista_info, productos, moneda_info = buscar_lista(
            models, uid, cfg, nombre_lista
        )

        if productos:
            # Usar la moneda de Odoo si está disponible
            moneda_cfg = {
                "moneda": moneda_info["name"],
                "simbolo_moneda": moneda_info["symbol"],
            }
            archivo = generar_pdf(nombre_lista, productos, {**cfg, **moneda_cfg})
            archivos.append(archivo)
        else:
            print("  ⚠️  Sin productos — se omite el PDF.")

    print("\n" + "=" * 55)
    print(f"✅ Proceso completado. PDFs generados: {len(archivos)}")
    for a in archivos:
        print(f"   📄 {a}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
