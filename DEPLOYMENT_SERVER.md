# Deploy a /var/www/webhooks - Wondertech PriceList

## 📍 Tu Configuración

- **Local:** `c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios`
- **Remoto:** `cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST`
- **Usuario:** `cristianwonder`
- **Servidor:** `ubuntu-s-1vcpu-1gb-sfo3-01`
- **Path remoto:** `/var/www/webhooks/WEBHOOK_PRICELIST`

> ⚠️ **Nota:** `/var/www/webhooks` es compartido con otros webhooks de la empresa.
> Tu proyecto vive en `/var/www/webhooks/WEBHOOK_PRICELIST`.

---

## 🚀 Deploy Completo (Desde PowerShell/Windows)

### Paso 1: Abrir PowerShell en tu carpeta

```powershell
cd "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios"
```

### Paso 2: Subir archivos al servidor

**Opción A: Usando rsync (recomendado - más rápido y eficiente)**

Si tienes Git Bash o WSL instalado:
```bash
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude 'venv' --exclude '.env' --exclude 'PDFs/output/*' --exclude 'logs/*' \
  "./" \
  cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/
```

**Opción B: Usando scp**

Desde PowerShell:
```powershell
# Subir todo el directorio (primera vez)
scp -r "./" cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/
```

**Opción C: Usando scp con exclude manual (si rsync no está disponible)**

Sube solo lo necesario:
```powershell
# Archivos principales
scp api_wondertech.py wondertech_pricelist_env.py requirements.txt ecosystem.config.js cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/

# Crear directorios en el servidor primero
ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01 "mkdir -p /var/www/webhooks/WEBHOOK_PRICELIST/{PDFs/output,PDFs/img,logs}"

# Si tienes imágenes en PDFs/img, súbelas también
scp ./PDFs/img/* cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/PDFs/img/
```

### Paso 3: Conectar al servidor y configurar

```bash
# SSH al servidor
ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01

# Ir al directorio
cd /var/www/webhooks/WEBHOOK_PRICELIST
```

### Paso 4: Configurar el archivo .env

```bash
# Crear el archivo .env en el servidor
nano .env
```

Pega este contenido (ajusta la API key):

```env
# ========================================
# SELECTOR DE AMBIENTE
# ========================================
USE_PRODUCTION=true

# ========================================
# CREDENCIALES PRODUCCIÓN
# ========================================
PROD_ODOO_JSONRPC=https://wondertechsas.odoo.com/jsonrpc
PROD_CALLBACK_URL=https://wondertechsas.odoo.com/web/hook/815464c9-033c-4e8b-9deb-15589f457b94
PROD_ODOO_DB=wondertechsas
PROD_ODOO_UID=5
PROD_ODOO_PASSWORD=TU_API_KEY_DE_PRODUCCION_AQUI

# ========================================
# TOKEN WEBHOOK
# ========================================
WEBHOOK_TOKEN=TU_TOKEN_SECRETO_GENERADO

# ========================================
# CONFIGURACIÓN SERVIDOR
# ========================================
PORT=5000
FLASK_DEBUG=false
```

**Para generar un token seguro:**
```bash
openssl rand -hex 32
```

Guarda con: `Ctrl+O`, `Enter`, `Ctrl+X`

### Paso 5: Configurar Python

```bash
cd /var/www/webhooks/WEBHOOK_PRICELIST

# Verificar Python
python3 --version
# o
python --version

# Crear entorno virtual
python3 -m venv venv

# Activar
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 6: Crear directorios necesarios

```bash
cd /var/www/webhooks/WEBHOOK_PRICELIST

mkdir -p PDFs/output PDFs/img logs

# Ajustar permisos
chmod 600 .env
chmod -R 755 PDFs
```

### Paso 7: Probar la aplicación

```bash
cd /var/www/webhooks/WEBHOOK_PRICELIST
source venv/bin/activate

# Ejecutar en foreground para probar
python api_wondertech.py
```

**Deberías ver:**
```
=======================================================
  WONDERTECH - Webhook Price List Generator
=======================================================
  Servidor corriendo en: http://0.0.0.0:5000
  Endpoints disponibles:
    - /webhook/odoo
    - /webhook/generate
    - /webhook/generate/<lista_nombre>
    - /webhook/generate-all
=======================================================
```

**Probar en otra terminal:**
```bash
# Desde otra terminal SSH
curl http://localhost:5000/
```

**Deberías ver:**
```json
{
  "status": "ok",
  "service": "WONDERTECH Price List Webhook",
  "version": "2.0",
  "endpoints": [
    "/webhook/odoo",
    "/webhook/generate",
    "/webhook/generate/<lista_nombre>",
    "/webhook/generate-all"
  ]
}
```

Detener con `Ctrl+C` en la terminal donde ejecutaste la app.

### Paso 8: Configurar PM2

```bash
cd /var/www/webhooks/WEBHOOK_PRICELIST

# Verificar PM2
pm2 --version

# Si no está instalado, instálalo localmente:
npm install -g pm2
# Agregar al PATH
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Iniciar la aplicación
pm2 start ecosystem.config.js

# Ver status
pm2 status

# Ver logs
pm2 logs wondertech-pricelist

# Guardar para auto-restart
pm2 save

# Configurar auto-start
pm2 startup
# Copia y ejecuta el comando que te muestra
```

### Paso 9: Verificar que todo funciona

```bash
# PM2 status
pm2 status wondertech-pricelist

# Debería mostrar:
# ┌────┬──────────────────────┬──────────┬──────┬───────────┬──────────┬──────────┐
# │ id │ name                 │ mode     │ ↺    │ status    │ cpu      │ memory   │
# ├────┼──────────────────────┼──────────┼──────┼───────────┼──────────┼──────────┤
# │ 0  │ wondertech-pricelist │ fork     │ 0    │ online    │ 0%       │ 45.2mb   │
# └────┴──────────────────────┴──────────┴──────┴───────────┴──────────┴──────────┘
```

### Paso 10: Solicitar configuración de Nginx al admin

Envía el template que está en `ADMIN_REQUEST_TEMPLATE.md` al administrador del servidor.

---

## ✅ Verificación Final

### Desde el servidor (después de que el admin configure nginx):
```bash
# Probar directamente
curl http://localhost:5000/

# Probar a través de nginx (después de configurado)
curl https://TU_DOMINIO/pricelist/
```

### Desde tu navegador:
```
https://TU_DOMINIO/pricelist/
https://TU_DOMINIO/pricelist/webhook/generate-all
```

### Probar endpoints del webhook:

**Generar todas las listas (JSON):**
```bash
curl -X POST https://TU_DOMINIO/pricelist/webhook/generate-all \
  -H "Content-Type: application/json" \
  -d '{"format": "json"}'
```

**Generar lista específica (PDF):**
```bash
curl -X POST https://TU_DOMINIO/pricelist/webhook/generate/Lista_Business \
  -H "Content-Type: application/json" \
  --output lista_business.pdf
```

---

## 🔧 Comandos Esenciales

### En el servidor (SSH):
```bash
# Ir al directorio
cd /var/www/webhooks/WEBHOOK_PRICELIST

# Activar entorno virtual
source venv/bin/activate

# Ver status de PM2
pm2 status

# Ver logs en tiempo real
pm2 logs wondertech-pricelist

# Reiniciar aplicación
pm2 restart wondertech-pricelist

# Detener aplicación
pm2 stop wondertech-pricelist

# Ver información detallada
pm2 info wondertech-pricelist
```

### Desde tu Windows (PowerShell):
```powershell
# SSH al servidor
ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01

# Subir cambios después de modificar algo local
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude 'venv' --exclude '.env' --exclude 'PDFs/output/*' --exclude 'logs/*' \
  "./" \
  cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/

# O con scp (sube todo)
scp -r "./" cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/
```

---

## 🔄 Actualizar la Aplicación (Deploy de cambios)

Cuando hagas cambios locales y quieras subirlos:

### Opción A: Rsync (solo archivos modificados)
```powershell
cd "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios"

rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' --exclude 'venv' --exclude '.env' --exclude 'PDFs/output/*' --exclude 'logs/*' \
  "./" \
  cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/
```

### Opción B: SCP (todo de nuevo)
```powershell
scp -r "./" cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/var/www/webhooks/WEBHOOK_PRICELIST/
```

### Luego, en el servidor (SSH):
```bash
ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01

cd /var/www/webhooks/WEBHOOK_PRICELIST
source venv/bin/activate

# Si hay nuevas dependencias en requirements.txt
pip install -r requirements.txt

# Reiniciar aplicación
pm2 restart wondertech-pricelist

# Ver logs para verificar que inició bien
pm2 logs wondertech-pricelist
```

---

## 📁 Estructura Final en el Servidor

```
/var/www/webhooks/WEBHOOK_PRICELIST/
├── api_wondertech.py              # App principal
├── wondertech_pricelist_env.py    # Lógica de generación
├── ecosystem.config.js            # Config PM2
├── requirements.txt               # Dependencias
├── .env                           # Credenciales (chmod 600)
├── DEPLOYMENT_SERVER.md           # Esta guía
├── ADMIN_REQUEST_TEMPLATE.md      # Template para admin
├── venv/                          # Entorno virtual Python
├── PDFs/
│   ├── output/                    # PDFs generados
│   └── img/                       # Imágenes header/footer
└── logs/
    ├── pm2-out.log
    ├── pm2-error.log
    └── pm2-combined.log
```

---

## 🐛 Troubleshooting

### ❌ Error: "Permission denied" al subir archivos
```bash
# Verificar permisos del directorio remoto
ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01
ls -la /var/www/
ls -la /var/www/webhooks/WEBHOOK_PRICELIST/

# Si no tienes permisos de escritura:
sudo chown -R cristianwonder:cristianwonder /var/www/webhooks/WEBHOOK_PRICELIST
# (Si no tienes sudo, pide al admin que lo haga)
```

### ❌ Python3 no encontrado
```bash
# Buscar python disponible
which python3
which python
python3 --version
python --version

# Si no está, pide al admin:
# sudo apt install -y python3 python3-pip python3-venv
```

### ❌ PM2 no está instalado
```bash
# Instalar localmente
mkdir -p ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
npm install -g pm2
```

### ❌ Puerto 5000 ya en uso
```bash
# Ver qué está usando el puerto
lsof -i :5000
# o
netstat -tulpn 2>/dev/null | grep 5000

# Cambiar el puerto en .env y ecosystem.config.js a 5001, 5002, etc.
```

### ❌ La app no inicia con PM2
```bash
# Ver logs de error
pm2 logs wondertech-pricelist --err

# Probar manualmente
cd /var/www/webhooks/WEBHOOK_PRICELIST
source venv/bin/activate
python api_wondertech.py

# Si funciona manual pero no con PM2:
pm2 delete wondertech-pricelist
pm2 start ecosystem.config.js
```

### ❌ Error de conexión a Odoo
```bash
# Verificar .env
cat /var/www/webhooks/WEBHOOK_PRICELIST/.env

# Probar conexión
curl -I https://wondertechsas.odoo.com/jsonrpc

# Ver logs completos
pm2 logs wondertech-pricelist --lines 100
```

---

## 📊 Monitoreo

### Script rápido de verificación
Crea `/var/www/webhooks/WEBHOOK_PRICELIST/check.sh`:
```bash
#!/bin/bash
echo "=== Wondertech PriceList Status ==="
echo ""
echo "📊 PM2 Status:"
pm2 status wondertech-pricelist
echo ""
echo "🔌 Puerto 5000:"
if lsof -i :5000 > /dev/null 2>&1; then
    echo "✅ Puerto 5000 está en uso"
else
    echo "❌ Puerto 5000 NO está en uso"
fi
echo ""
echo "💾 Espacio usado:"
du -sh /var/www/webhooks/WEBHOOK_PRICELIST/PDFs/output/ 2>/dev/null || echo "Sin PDFs"
echo ""
echo "📝 Últimos errores:"
tail -5 /var/www/webhooks/WEBHOOK_PRICELIST/logs/pm2-error.log 2>/dev/null || echo "Sin errores"
```

```bash
chmod +x /var/www/webhooks/WEBHOOK_PRICELIST/check.sh
./check.sh
```

---

## 📝 Checklist de Deploy

- [ ] Archivos subidos al servidor (`scp` o `rsync`)
- [ ] SSH al servidor: `ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01`
- [ ] Archivo `.env` creado con credenciales correctas
- [ ] Entorno virtual creado: `python3 -m venv venv`
- [ ] Dependencias instaladas: `pip install -r requirements.txt`
- [ ] Directorios creados: `PDFs/output`, `PDFs/img`, `logs`
- [ ] Aplicación probada manualmente: `python api_wondertech.py`
- [ ] PM2 configurado e iniciado: `pm2 start ecosystem.config.js`
- [ ] PM2 guardado para auto-start: `pm2 save`
- [ ] Enviado template al admin para configuración de nginx
- [ ] Verificado que los endpoints responden: `curl http://localhost:5000/`
- [ ] Probado webhook desde navegador o Postman

---

**¡Listo! Tu webhook de listas de precios está deployado 🎉**
