from dotenv import load_dotenv
import os
import json
import requests
import sys

load_dotenv()

print("=" * 60)
print("1. VALIDACIÓN DE VARIABLES DE ENTORNO")
print("=" * 60)

odoo_api_key = os.getenv("ODOO_API_KEY")
prod_odoo_password = os.getenv("PROD_ODOO_PASSWORD")
url = os.getenv("PROD_ODOO_JSONRPC")
db = os.getenv("PROD_ODOO_DB")
uid = os.getenv("PROD_ODOO_UID")

print("ODOO_API_KEY existe?:", bool(odoo_api_key))
print("PROD_ODOO_PASSWORD existe?:", bool(prod_odoo_password))
print("PROD_ODOO_JSONRPC existe?:", bool(url))
print("PROD_ODOO_DB existe?:", bool(db))
print("PROD_ODOO_UID existe?:", bool(uid))
print("PROD_ODOO_PASSWORD es literal ${ODOO_API_KEY}?:", prod_odoo_password == "${ODOO_API_KEY}")

if odoo_api_key:
    print("Primeros 6 caracteres de ODOO_API_KEY:", odoo_api_key[:6])

if prod_odoo_password:
    print("Primeros 6 caracteres de PROD_ODOO_PASSWORD:", prod_odoo_password[:6])

password = odoo_api_key or prod_odoo_password

print("\nVariable final usada para autenticar:", "ODOO_API_KEY" if odoo_api_key else "PROD_ODOO_PASSWORD")

if not url or not db or not uid or not password:
    print("\nERROR: faltan variables obligatorias para probar Odoo.")
    print("Revisa tu .env o variables del servidor.")
    sys.exit(1)

if prod_odoo_password == "${ODOO_API_KEY}":
    print("\nADVERTENCIA: PROD_ODOO_PASSWORD está tomando el texto literal '${ODOO_API_KEY}'.")
    print("Eso significa que tu cargador .env no expandió la variable.")
    print("Igualmente se intentará la conexión usando ODOO_API_KEY si existe.")
    if not odoo_api_key:
        sys.exit(1)

print("\n" + "=" * 60)
print("2. PRUEBA REAL CONTRA ODOO")
print("=" * 60)

try:
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                db,
                int(uid),
                password,
                "res.partner",
                "search_read",
                [[]],
                {"fields": ["name"], "limit": 1}
            ],
        },
        "id": 1,
    }

    response = requests.post(url, json=payload, timeout=60)
    print("HTTP Status:", response.status_code)

    try:
        result = response.json()
    except Exception:
        print("ERROR: la respuesta no es JSON válido")
        print(response.text)
        sys.exit(1)

    print("\nRespuesta completa:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if "error" in result:
        print("\nRESULTADO: LA CONEXIÓN FALLÓ")
        print("Posibles causas:")
        print("- API key incorrecta")
        print("- UID incorrecto")
        print("- La API key pertenece a otro usuario")
        print("- Variables mal cargadas")
        sys.exit(1)

    print("\nRESULTADO: CONEXIÓN EXITOSA CON ODOO")
    print("La API key está funcionando correctamente.")

except requests.exceptions.RequestException as e:
    print("\nERROR DE RED O REQUEST:")
    print(str(e))
    sys.exit(1)

except Exception as e:
    print("\nERROR GENERAL:")
    print(str(e))
    sys.exit(1)