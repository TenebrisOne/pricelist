# Deploy de Lista de Precios Wondertech en Ubuntu Server

## 📋 Tabla de Contenidos
- [Prerrequisitos](#prerrequisitos)
- [Paso 1: Preparar el Servidor](#paso-1-preparar-el-servidor)
- [Paso 2: Configurar la Aplicación](#paso-2-configurar-la-aplicación)
- [Paso 3: Configurar PM2](#paso-3-configurar-pm2)
- [Paso 4: Configurar Nginx](#paso-4-configurar-nginx)
- [Paso 5: Configurar SSL (Opcional)](#paso-5-configurar-ssl-opcional)
- [Paso 6: Verificar el Deploy](#paso-6-verificar-el-deploy)
- [Comandos Útiles](#comandos-útiles)
- [Troubleshooting](#troubleshooting)

---

## Prerrequisitos

- ✅ Servidor Ubuntu con acceso SSH
- ✅ Usuario con privilegios sudo
- ✅ Dominio o IP pública configurada
- ✅ Puerto 80 (y 443 si usas SSL) abierto

---

## Paso 1: Preparar el Servidor

### 1.1 Conectar al servidor via SSH
```bash
ssh usuario@tu-servidor.com
```

### 1.2 Actualizar el sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.3 Instalar dependencias necesarias
```bash
# Instalar Python 3 y pip
sudo apt install -y python3 python3-pip python3-venv

# Instalar Node.js y npm (necesario para PM2)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Instalar PM2 globalmente
sudo npm install -g pm2

# Instalar Nginx
sudo apt install -y nginx

# Instalar Git (si no está instalado)
sudo apt install -y git
```

### 1.4 Verificar instalaciones
```bash
python3 --version
node --version
npm --version
pm2 --version
nginx -v
```

---

## Paso 2: Configurar la Aplicación

### 2.1 Crear directorio de la aplicación
```bash
# Crear directorio para la aplicación
sudo mkdir -p /var/www/pricelist
sudo chown $USER:$USER /var/www/pricelist
cd /var/www/pricelist
```

### 2.2 Subir el código al servidor

**Opción A: Usando Git (recomendado)**
```bash
# Clonar el repositorio (ajusta la URL)
git clone <URL_DE_TU_REPOSITORIO> /var/www/pricelist
cd /var/www/pricelist
```

**Opción B: Usando SCP (desde tu máquina local)**
```bash
# Desde tu máquina Windows (PowerShell o CMD):
scp -r "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios\*" usuario@tu-servidor.com:/var/www/pricelist/
```

**Opción C: Usando rsync**
```bash
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude '.env' \
  "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios/" \
  usuario@tu-servidor.com:/var/www/pricelist/
```

### 2.3 Crear entorno virtual de Python
```bash
cd /var/www/pricelist

# Crear virtual environment
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Configurar variables de entorno
```bash
# Crear archivo .env
nano .env
```

Copiar y pegar la configuración del `.env` local, **ajustando para producción**:

```env
# ========================================
# SELECTOR DE AMBIENTE
# ========================================
# true para PRODUCCIÓN, false para PRUEBAS
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
# CREDENCIALES PRUEBAS (opcional)
# ========================================
TEST_ODOO_JSONRPC=https://pruebasabril-1.odoo.com/jsonrpc
TEST_ODOO_DB=pruebasabril-1
TEST_ODOO_UID=41
TEST_ODOO_PASSWORD=d0651720e8b8c2a68168534eb3de32229242393b
TEST_CALLBACK_URL=https://pruebasabril-1.odoo.com/web/hook/a4719c9d-f200-418e-b5a1-941dddf61101

# ========================================
# TOKEN DE SEGURIDAD WEBHOOK
# ========================================
WEBHOOK_TOKEN=TU_TOKEN_SECRETO_AQUI

# ========================================
# CONFIGURACIÓN DEL SERVIDOR
# ========================================
PORT=5008
FLASK_DEBUG=false
```

**⚠️ IMPORTANTE:**
- Cambia `PROD_ODOO_PASSWORD` por tu API key real de producción
- Genera un `WEBHOOK_TOKEN` seguro (puedes usar: `openssl rand -hex 32`)
- Guarda el archivo con `Ctrl+O`, `Enter`, `Ctrl+X`

### 2.5 Configurar permisos
```bash
# Crear directorios necesarios
mkdir -p PDFs/output PDFs/img

# Ajustar permisos
chmod -R 755 /var/www/pricelist
chmod 600 .env  # Proteger el archivo .env

# Copiar las imágenes de header/footer si existen
# (desde tu máquina local o donde las tengas)
```

### 2.6 Probar que la aplicación funciona
```bash
# Activar el entorno virtual
source venv/bin/activate

# Ejecutar la aplicación manualmente
python api_wondertech.py

# Deberías ver:
# WONDERTECH - Webhook Price List Generator
# Servidor corriendo en: http://0.0.0.0:5008

# Probar en otro terminal o navegador:
curl http://localhost:5008/

# Detener con Ctrl+C
```

---

## Paso 3: Configurar PM2

### 3.1 Crear archivo de configuración de PM2
```bash
cd /var/www/pricelist
nano ecosystem.config.js
```

El archivo `ecosystem.config.js` ya está creado en este repositorio. Súbelo o créalo con:

```javascript
module.exports = {
  apps: [{
    name: 'wondertech-pricelist',
    script: 'api_wondertech.py',
    interpreter: 'venv/bin/python',
    instances: 2,  // Número de instancias (ajusta según CPU)
    exec_mode: 'cluster',
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
```

### 3.2 Crear directorio de logs
```bash
mkdir -p logs
```

### 3.3 Iniciar la aplicación con PM2
```bash
cd /var/www/pricelist

# Iniciar aplicación
pm2 start ecosystem.config.js

# Ver status
pm2 status

# Ver logs en tiempo real
pm2 logs wondertech-pricelist

# Ver detalles de la app
pm2 show wondertech-pricelist
```

### 3.4 Configurar PM2 para inicio automático
```bash
# Generar script de startup
pm2 startup

# Copiar y ejecutar el comando que te muestra PM2
# (algo como: sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u tu-usuario --hp /home/tu-usuario)

# Guardar la configuración actual
pm2 save

# Verificar que el servicio está habilitado
sudo systemctl enable pm2-$(whoami)
```

### 3.5 Comandos útiles de PM2
```bash
# Ver status
pm2 status

# Ver logs
pm2 logs wondertech-pricelist

# Reiniciar aplicación
pm2 restart wondertech-pricelist

# Detener aplicación
pm2 stop wondertech-pricelist

# Ver monitoreo
pm2 monit

# Ver información detallada
pm2 info wondertech-pricelist
```

---

## Paso 4: Configurar Nginx

### 4.1 Crear configuración de Nginx
```bash
sudo nano /etc/nginx/sites-available/wondertech-pricelist
```

Copiar y pegar la siguiente configuración (**ajusta el dominio**):

```nginx
server {
    listen 80;
    server_name pricelist.wondertech.com.co;  # CAMBIA ESTO por tu dominio o IP

    # Logs
    access_log /var/log/nginx/pricelist-access.log;
    error_log /var/log/nginx/pricelist-error.log;

    # Límite de tamaño para subida de archivos (si aplica)
    client_max_body_size 10M;

    # Timeouts
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;

    # Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Ubicación principal
    location / {
        proxy_pass http://127.0.0.1:5008;
        proxy_http_version 1.1;
        
        # Headers importantes
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Archivos estáticos (si los hay)
    location /static {
        alias /var/www/pricelist/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # PDFs generados (opcional - acceso directo)
    location /pdfs/ {
        alias /var/www/pricelist/PDFs/output/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
        
        # Proteger con autenticación si es necesario
        # auth_basic "Restricted Access";
        # auth_basic_user_file /etc/nginx/.htpasswd;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5008/;
        access_log off;
    }
}
```

### 4.2 Habilitar el sitio
```bash
# Crear enlace simbólico
sudo ln -s /etc/nginx/sites-available/wondertech-pricelist /etc/nginx/sites-enabled/

# Eliminar el sitio por defecto (opcional pero recomendado)
sudo rm /etc/nginx/sites-enabled/default

# Probar configuración de Nginx
sudo nginx -t

# Si todo está bien, reiniciar Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 4.3 Verificar que Nginx está corriendo
```bash
sudo systemctl status nginx
```

---

## Paso 5: Configurar SSL (Opcional pero Recomendado)

### 5.1 Instalar Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 5.2 Obtener certificado SSL
```bash
# Para un solo dominio
sudo certbot --nginx -d pricelist.wondertech.com.co

# Certbot te preguntará:
# - Tu email para renovaciones
# - Si deseas redirigir HTTP a HTTPS (recomendado: Sí)
```

### 5.3 Verificar renovación automática
```bash
# Probar renovación (dry run)
sudo certbot renew --dry-run

# Verificar el timer de systemd
sudo systemctl status certbot.timer
```

**Nota:** Si usas un firewall, asegúrate de abrir los puertos:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

---

## Paso 6: Verificar el Deploy

### 6.1 Verificar que todo está corriendo
```bash
# Verificar PM2
pm2 status

# Verificar Nginx
sudo systemctl status nginx

# Verificar puertos
sudo netstat -tulpn | grep -E ':(80|443|5008)'
```

### 6.2 Probar endpoints

**Desde el servidor:**
```bash
curl http://localhost:5008/
curl http://localhost:5008/webhook/odoo
```

**Desde tu navegador o máquina local:**
```
http://tu-dominio.com/
http://tu-dominio.com/webhook/odoo
http://tu-dominio.com/webhook/generate-all
http://tu-dominio.com/webhook/generate/Lista_Business
```

**Ejemplo de solicitud JSON:**
```bash
curl -X POST http://tu-dominio.com/webhook/generate/Lista_Business \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: TU_TOKEN_SECRETO" \
  -d '{"format": "json"}'
```

**Ejemplo para descargar PDF:**
```bash
curl -X POST http://tu-dominio.com/webhook/generate/Lista_Business \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: TU_TOKEN_SECRETO" \
  -d '{"format": "pdf"}' \
  --output lista_business.pdf
```

### 6.3 Verificar logs
```bash
# Logs de PM2
pm2 logs wondertech-pricelist --lines 100

# Logs de Nginx
sudo tail -f /var/log/nginx/pricelist-access.log
sudo tail -f /var/log/nginx/pricelist-error.log

# Logs de la aplicación (en el directorio del proyecto)
tail -f logs/pm2-out.log
tail -f logs/pm2-error.log
```

---

## Comandos Útiles

### Gestión de PM2
```bash
# Iniciar aplicación
pm2 start wondertech-pricelist

# Reiniciar aplicación
pm2 restart wondertech-pricelist

# Detener aplicación
pm2 stop wondertech-pricelist

# Recargar sin downtime
pm2 reload wondertech-pricelist

# Ver logs en tiempo real
pm2 logs wondertech-pricelist

# Ver monitoreo
pm2 monit

# Guardar estado actual
pm2 save

# Limpiar logs
pm2 flush
```

### Gestión de Nginx
```bash
# Ver status
sudo systemctl status nginx

# Reiniciar
sudo systemctl restart nginx

# Recargar configuración (sin downtime)
sudo systemctl reload nginx

# Probar configuración
sudo nginx -t

# Ver logs de acceso
sudo tail -f /var/log/nginx/pricelist-access.log

# Ver logs de error
sudo tail -f /var/log/nginx/pricelist-error.log
```

### Actualización de la aplicación
```bash
cd /var/www/pricelist

# 1. Actualizar código (si usas Git)
git pull origin main

# 2. Instalar nuevas dependencias
source venv/bin/activate
pip install -r requirements.txt

# 3. Reiniciar aplicación
pm2 restart wondertech-pricelist

# 4. Verificar
pm2 logs wondertech-pricelist
```

### Backup
```bash
# Crear backup del directorio
tar -czf /backup/pricelist-backup-$(date +%Y%m%d).tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='logs/*' \
  --exclude='PDFs/output/*' \
  /var/www/pricelist/

# Backup solo del .env (¡IMPORTANTE!)
cp /var/www/pricelist/.env /backup/pricelist-env-backup-$(date +%Y%m%d)
```

---

## Troubleshooting

### La aplicación no inicia con PM2
```bash
# Ver logs de error
pm2 logs wondertech-pricelist --err

# Verificar que el virtual environment existe
ls -la /var/www/pricelist/venv/bin/python

# Verificar que las dependencias están instaladas
source /var/www/pricelist/venv/bin/activate
pip list

# Intentar ejecutar manualmente
cd /var/www/pricelist
source venv/bin/activate
python api_wondertech.py
```

### Error 502 Bad Gateway
```bash
# Verificar que PM2 está corriendo
pm2 status

# Verificar que el puerto 5008 está escuchando
sudo netstat -tulpn | grep 5008

# Verificar configuración de Nginx
sudo nginx -t

# Verificar logs de Nginx
sudo tail -f /var/log/nginx/pricelist-error.log

# Reiniciar servicios
pm2 restart wondertech-pricelist
sudo systemctl restart nginx
```

### Error de conexión a Odoo
```bash
# Verificar conectividad
curl -I https://wondertechsas.odoo.com/jsonrpc

# Verificar variables de entorno
cat /var/www/pricelist/.env

# Probar conexión manualmente
source /var/www/pricelist/venv/bin/activate
python -c "from wondertech_pricelist_env import cargar_credenciales_desde_env, conectar_odoo; print('OK')"
```

### Permisos de archivos
```bash
# Ajustar permisos del directorio
sudo chown -R $USER:$USER /var/www/pricelist
chmod -R 755 /var/www/pricelist
chmod 600 /var/www/pricelist/.env

# Verificar que Nginx puede acceder a los PDFs
sudo chmod -R 755 /var/www/pricelist/PDFs
```

### Renovación de SSL falla
```bash
# Verificar que el puerto 80 está accesible desde internet
sudo ufw status

# Forzar renovación
sudo certbot renew --force-renewal

# Ver logs de Certbot
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Puerto ya en uso
```bash
# Ver qué proceso está usando el puerto
sudo lsof -i :5008
sudo fuser 5008/tcp

# Matar el proceso si es necesario
sudo kill -9 <PID>
```

---

## 📝 Notas Importantes

1. **Seguridad:**
   - Mantén el archivo `.env` seguro y con permisos restrictivos (600)
   - Usa tokens de webhook fuertes y únicos
   - Considera agregar autenticación a los endpoints
   - Mantén el sistema actualizado

2. **Performance:**
   - Ajusta `instances` en PM2 según los CPUs disponibles (`nproc` para ver cuántos tienes)
   - Considera usar Redis para caché si el tráfico aumenta
   - Monitorea el uso de memoria

3. **Monitoreo:**
   - Considera integrar con PM2 Plus: `pm2 plus`
   - Configura alertas para caídas del servicio
   - Revisa logs regularmente

4. **Mantenimiento:**
   - Realiza backups regularmente
   - Limpia logs antiguos
   - Actualiza dependencias periódicamente
   - Renueva certificados SSL antes de que expiren

---

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs de PM2 y Nginx
2. Verifica que todos los servicios estén corriendo
3. Comprueba la conectividad a Odoo
4. Revisa que las variables de entorno estén correctas

---

**Última actualización:** Abril 2026  
**Versión:** 1.0
