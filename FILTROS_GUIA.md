# 📋 GUÍA DE FILTROS - WONDERTECH PRICE LIST

## 📍 Ubicación de los Filtros

Los filtros se configuran en el archivo `wondertech_pricelist_env.py`, dentro del diccionario `CONFIG` (línea ~36).

---

## 🔧 Filtros Disponibles

### 1. 📅 **FILTRO POR FECHA** (Recomendado)

Filtra productos según su vigencia en Odoo.

#### Opciones:
- `fecha_inicio_max`: Solo productos que **inician antes** de esta fecha
- `fecha_fin_min`: Solo productos que **terminan después** de esta fecha

#### Ejemplos:

```python
# Solo productos vigentes hasta el 18/04/2026
"fecha_inicio_max": "2026-04-18",

# Solo productos que terminan después del 10/04/2026
"fecha_fin_min": "2026-04-10",

# Combinar ambos (productos en rango de fechas)
"fecha_inicio_max": "2026-04-18",
"fecha_fin_min": "2026-04-01",

# Sin filtro de fecha
"fecha_inicio_max": None,
"fecha_fin_min": None,
```

---

### 2. 📂 **FILTRO POR CATEGORÍAS**

Solo incluye productos de ciertas categorías (Tipo de Producto).

#### Ejemplos:

```python
# Solo estas categorías
"categorias_incluidas": ["ACCESORIOS", "AUDIO", "CABLES"],

# Solo una categoría
"categorias_incluidas": ["CELULARES"],

# Todas las categorías (sin filtro)
"categorias_incluidas": None,
```

#### Categorías Disponibles (ejemplo):
- ACCESORIOS
- AUDIO
- CABLES
- CÁMARAS
- CELULARES
- COMPUTADORES
- CONECTIVIDAD
- DISCOS
- IMPRESORAS
- MONITORES
- etc.

---

### 3. 🏷️ **FILTRO POR MARCAS**

Solo incluye productos de ciertas marcas.

#### Ejemplos:

```python
# Solo estas marcas
"marcas_incluidas": ["HP", "LENOVO", "DELL"],

# Solo Apple
"marcas_incluidas": ["APPLE"],

# Todas las marcas (sin filtro)
"marcas_incluidas": None,
```

---

### 4. 💰 **FILTRO POR RANGO DE PRECIOS**

Solo incluye productos dentro de un rango de precios.

#### Ejemplos:

```python
# Productos entre $10,000 y $500,000
"precio_min": 10000,
"precio_max": 500000,

# Solo productos mayores a $100,000
"precio_min": 100000,
"precio_max": None,

# Solo productos menores a $200,000
"precio_min": None,
"precio_max": 200000,

# Sin filtro de precio
"precio_min": None,
"precio_max": None,
```

---

### 5. 🔢 **LÍMITE MÁXIMO DE PRODUCTOS**

Limita la cantidad de productos por lista de precios.

#### Ejemplos:

```python
# Máximo 50 productos por lista
"max_productos": 50,

# Máximo 20 productos
"max_productos": 20,

# Sin límite
"max_productos": None,
```

---

## 🎯 EJEMPLOS DE USO COMBINADO

### Ejemplo 1: Lista Business - Solo productos vigentes y de ciertas categorías

```python
CONFIG = {
    "listas": ["Lista Business"],
    
    # Filtros
    "fecha_inicio_max": "2026-04-18",
    "categorias_incluidas": ["ACCESORIOS", "AUDIO", "CABLES"],
    
    # Resto de configuración...
}
```

### Ejemplo 2: Lista Reseller - Solo HP y LENOVO, precio $50k-$300k

```python
CONFIG = {
    "listas": ["Lista Reseller"],
    
    # Filtros
    "marcas_incluidas": ["HP", "LENOVO"],
    "precio_min": 50000,
    "precio_max": 300000,
    "max_productos": 30,
    
    # Resto de configuración...
}
```

### Ejemplo 3: Lista completa con fecha y límite

```python
CONFIG = {
    "listas": ["Lista Business", "Lista Reseller"],
    
    # Filtros
    "fecha_inicio_max": "2026-04-18",
    "max_productos": 100,
    
    # Resto de configuración...
}
```

---

## 📊 MENSAJES DE CONSOLA

Cuando ejecutás el script, vas a ver algo así:

```
🔧  Filtros configurados:
   ✓ Fecha inicio máx: 2026-04-18
   ✓ Categorías: ACCESORIOS, AUDIO, CABLES
   ✓ Precio mín: $50,000
   ✓ Máx productos: 50
```

O si no hay filtros:

```
🔧  Filtros configurados:
   ⚠️  Sin filtros (todos los productos)
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Fechas**: Usar formato `YYYY-MM-DD` (ej: `"2026-04-18"`)
2. **Categorías**: Los nombres deben ser exactos (mayúsculas recomendado)
3. **Marcas**: Deben coincidir exactamente con las de Odoo
4. **Precios**: En pesos colombianos (COP), sin puntos ni comas
5. **Combinación**: Podés combinar todos los filtros al mismo tiempo
6. **Orden de filtrado**: Fecha → Categoría → Marca → Precio → Límite

---

## 🚀 RECOMENDACIÓN

Para empezar, te recomiendo usar solo el **filtro por fecha**:

```python
"fecha_inicio_max": "2026-04-18",
```

Esto te va a dar solo los productos que están vigentes hasta esa fecha. Después podés agregar más filtros si necesitas.
