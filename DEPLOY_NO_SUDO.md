# Deploy sin SUDO - Wondertech PriceList Webhook

## 🎯 Escenario
- ✅ No tienes permisos `sudo` en el servidor
- ✅ Nginx ya está configurado y es compartido con otros desarrollos
- ✅ Tu app será un webhook dentro de un nginx existente
- ✅ Solo necesitas configurar tu aplicación y que el admin agregue una ruta

---

## 📋 Lo que necesitas del admin del servidor

Pídele al administrador del servidor que agregue esto al `nginx.conf` existente:

### Opción A: Subruta dentro del dominio existente
```nginx
# Agregar al server block existente en nginx.conf
location /pricelist/ {
    proxy_pass http://127.0.0.1:5008/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Esto hará que tu webhook sea accesible en:
- `https://dominio-existente.com/pricelist/`
- `https://dominio-existente.com/pricelist/webhook/generate-all`

### Opción B: Subdominio dedicado (si el admin prefiere)
```nginx
server {
    listen 80;
    server_name pricelist.dominio-existente.com;

    location / {
        proxy_pass http://127.0.0.1:5008;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🚀 Tu Deploy (sin sudo)

### Paso 1: Preparar tu directorio home
```bash
# Crear directorio en tu home (no necesitas sudo)
mkdir -p ~/apps/pricelist
cd ~/apps/pricelist
```

### Paso 2: Subir tu código

**Opción A: Usando Git**
```bash
cd ~/apps/pricelist
git clone <URL_DE_TU_REPO> .
```

**Opción B: Usando SCP desde tu Windows**
```powershell
# Desde PowerShell en tu máquina
scp -r "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios\*" usuario@servidor:~/apps/pricelist/
```

**Opción C: Usando rsync**
```bash
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.env' --exclude 'venv' \
  "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios/" \
  usuario@servidor:~/apps/pricelist/
```

### Paso 3: Configurar Python (sin sudo)

```bash
cd ~/apps/pricelist

# Verificar que Python está disponible
python3 --version
python3 -m venv --help

# Si python3 no está, probar alternativas
python --version
which python

# Crear entorno virtual
python3 -m venv venv

# Activar
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

**⚠️ Si no puedes crear el venv, pídele al admin que instale:**
```bash
# (El admin necesita sudo para esto)
sudo apt install -y python3 python3-pip python3-venv
```

### Paso 4: Configurar .env

```bash
cd ~/apps/pricelist

# Crear .env
nano .env
# o usa tu editor preferido: vim, code, etc.
```

Contenido del `.env` para producción:
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
PROD_ODOO_PASSWORD=TU_API_KEY_PRODUCCION

# ========================================
# TOKEN WEBHOOK
# ========================================
WEBHOOK_TOKEN=TU_TOKEN_SECRETO

# ========================================
# CONFIGURACIÓN SERVIDOR
# ========================================
PORT=5008
FLASK_DEBUG=false
```

### Paso 5: Crear directorios necesarios

```bash
cd ~/apps/pricelist

mkdir -p PDFs/output PDFs/img logs

# Ajustar permisos (solo tus archivos)
chmod 600 .env
chmod -R 755 PDFs
```

### Paso 6: Probar la aplicación manualmente

```bash
cd ~/apps/pricelist
source venv/bin/activate

# Ejecutar en foreground
python api_wondertech.py

# Deberías ver:
# WONDERTECH - Webhook Price List Generator
# Servidor corriendo en: http://0.0.0.0:5008

# Probar en otra terminal
curl http://localhost:5008/

# Detener con Ctrl+C
```

### Paso 7: Configurar PM2 (sin sudo)

**Instalar PM2 localmente (sin sudo):**
```bash
# Si npm no está disponible, pídele al admin que instale Node.js
# O instala PM2 globalmente si tienes permisos:
npm install -g pm2

# Si no puedes instalar global, instala local:
mkdir -p ~/npm
npm config set prefix '~/npm'
npm install -g pm2

# Agregar a tu PATH
echo 'export PATH="$HOME/npm/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verificar
pm2 --version
```

**Iniciar tu app con PM2:**
```bash
cd ~/apps/pricelist

# Asegúrate de que ecosystem.config.js está presente
# Si no, créalo:
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'wondertech-pricelist',
    script: 'api_wondertech.py',
    interpreter: 'venv/bin/python',
    instances: 1,  // Sin sudo, mejor 1 instancia
    exec_mode: 'fork',  // fork en lugar de cluster (no necesitas root)
    env: {
      NODE_ENV: 'production',
      PORT: 5008
    },
    max_memory_restart: '500M',
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_file: './logs/pm2-combined.log',
    time: true,
    merge_logs: true,
    autorestart: true,
    watch: false,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 3000,
    kill_timeout: 5008
  }]
};
EOF

# Iniciar aplicación
pm2 start ecosystem.config.js

# Ver status
pm2 status

# Ver logs
pm2 logs wondertech-pricelist

# Guardar para auto-restart
pm2 save

# Configurar auto-start (sin sudo)
pm2 startup
# Copia y ejecuta el comando que te muestra
```

### Paso 8: Solicitar configuración de Nginx al admin

Envía este mensaje al administrador del servidor:

---

**Mensaje para el Admin:**

```
Hola! Necesito que agregues una ruta a nginx para mi webhook de generación 
de listas de precios.

Opción A (Recomendada - Subruta):

En el server block existente de nginx.conf, agregar:

location /pricelist/ {
    proxy_pass http://127.0.0.1:5008/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

Mi aplicación ya está corriendo en el puerto 5008 con PM2 en:
/home/TU_USUARIO/apps/pricelist

Los endpoints que necesito accesibles son:
- /pricelist/ (health check)
- /pricelist/webhook/odoo
- /pricelist/webhook/generate-all
- /pricelist/webhook/generate/<lista_nombre>

Gracias!
```

---

## ✅ Verificar Deploy

### Desde el servidor:
```bash
# Verificar que PM2 está corriendo
pm2 status

# Probar directamente
curl http://localhost:5008/

# Ver logs
pm2 logs wondertech-pricelist
```

### Desde tu navegador:
```
https://dominio-existente.com/pricelist/
https://dominio-existente.com/pricelist/webhook/generate-all
```

### Probar webhook:
```bash
# Desde tu máquina o con curl
curl -X POST https://dominio-existente.com/pricelist/webhook/generate-all \
  -H "Content-Type: application/json" \
  -d '{"format": "json"}'
```

---

## 🔧 Comandos Útiles (sin sudo)

### PM2
```bash
pm2 status                    # Ver estado de apps
pm2 logs wondertech-pricelist # Ver logs en tiempo real
pm2 restart wondertech-pricelist # Reiniciar app
pm2 stop wondertech-pricelist    # Detener app
pm2 monit                     # Monitoreo
pm2 info wondertech-pricelist # Información detallada
```

### Logs manuales
```bash
# Ver logs de PM2
tail -f ~/apps/pricelist/logs/pm2-out.log
tail -f ~/apps/pricelist/logs/pm2-error.log

# Buscar errores
grep -i error ~/apps/pricelist/logs/pm2-error.log
```

---

## 📁 Estructura sin sudo

```
/home/TU_USUARIO/
└── apps/
    └── pricelist/
        ├── api_wondertech.py
        ├── wondertech_pricelist_env.py
        ├── ecosystem.config.js
        ├── requirements.txt
        ├── .env                      # (chmod 600)
        ├── venv/                     # Entorno virtual
        ├── PDFs/
        │   ├── output/               # PDFs generados
        │   └── img/                  # Imágenes
        └── logs/                     # Logs de PM2
```

---

## 🐛 Troubleshooting (sin sudo)

### ❌ Python no está disponible
```bash
# Buscar python en el sistema
which python3
which python
find /usr -name "python*" 2>/dev/null

# Si no está, solicitar al admin:
# sudo apt install -y python3 python3-pip python3-venv
```

### ❌ PM2 no está disponible
```bash
# Instalar localmente (sin sudo)
mkdir -p ~/npm
npm config set prefix '~/npm'
npm install -g pm2
echo 'export PATH="$HOME/npm/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### ❌ Puerto 5008 ya en uso
```bash
# Ver qué está usando el puerto
lsof -i :5008
netstat -tulpn 2>/dev/null | grep 5008

# Cambiar el puerto en .env y ecosystem.config.js
# PORT=5001
```

### ❌ Permisos denegados para crear directorios
```bash
# Solo puedes escribir en tu home
mkdir -p ~/apps/pricelist
cd ~/apps/pricelist

# NO intentar crear en /var/www o /opt sin sudo
```

### ❌ Aplicación no inicia con PM2
```bash
# Ver logs de error
pm2 logs wondertech-pricelist --err

# Probar manualmente
cd ~/apps/pricelist
source venv/bin/activate
python api_wondertech.py

# Si funciona manualmente pero no con PM2, verificar:
pm2 info wondertech-pricelist
# Revisar que el interpreter path sea correcto
```

---

## 🔐 Seguridad (sin sudo)

```bash
# Proteger tu .env (solo lectura para ti)
chmod 600 ~/apps/pricelist/.env

# Verificar permisos
ls -la ~/apps/pricelist/.env

# No exponer logs públicamente
chmod 700 ~/apps/pricelist/logs
```

---

## 📊 Monitoreo sin sudo

### Script de verificación
Crea `~/apps/pricelist/check.sh`:
```bash
#!/bin/bash
echo "=== Wondertech PriceList Status ==="
echo ""

# PM2 status
echo "📊 PM2 Status:"
pm2 status wondertech-pricelist
echo ""

# Puerto
echo "🔌 Puerto 5008:"
if lsof -i :5008 > /dev/null 2>&1; then
    echo "✅ Puerto 5008 está en uso"
else
    echo "❌ Puerto 5008 NO está en uso"
fi
echo ""

# Disco
echo "💾 Uso de disco:"
du -sh ~/apps/pricelist/PDFs/output/ 2>/dev/null || echo "Sin PDFs"
echo ""

# Logs recientes
echo "📝 Últimos errores:"
tail -5 ~/apps/pricelist/logs/pm2-error.log 2>/dev/null || echo "Sin errores"
```

```bash
chmod +x ~/apps/pricelist/check.sh
./check.sh
```

---

## 📝 Resumen para el Admin

Cuando contactes al admin, necesitarás:

1. ✅ Tu aplicación ya corriendo en `localhost:5008` (verificar con `pm2 status`)
2. ✅ El mensaje con la configuración de nginx que necesitas
3. ✅ Confirmar que la ruta será `/pricelist/` o un subdominio

---

**¡Listo! Con esto puedes hacer deploy sin permisos sudo 🎉**
