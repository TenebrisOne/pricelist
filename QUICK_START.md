# 🚀 Guía Rápida de Deploy - Wondertech PriceList

## ⚡ Deploy en 5 Pasos

### Paso 1: Conectar al servidor
```bash
ssh usuario@tu-servidor.com
```

### Paso 2: Instalar dependencias del servidor
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar todo lo necesario
sudo apt install -y python3 python3-pip python3-venv nginx git
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

### Paso 3: Subir y configurar la aplicación
```bash
# Crear directorio
sudo mkdir -p /var/www/pricelist
sudo chown $USER:$USER /var/www/pricelist
cd /var/www/pricelist

# Subir archivos (desde tu máquina Windows)
# Opción A: Usando Git
git clone <URL_REPOSITORIO> /var/www/pricelist

# Opción B: Usando SCP (desde Windows)
# scp -r "ruta\local\*" usuario@servidor:/var/www/pricelist/

# Configurar en el servidor
cd /var/www/pricelist
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Crear .env (usa nano o tu editor preferido)
nano .env
# Pega el contenido de tu .env local y ajusta para producción
```

### Paso 4: Iniciar con PM2
```bash
# Iniciar aplicación
pm2 start ecosystem.config.js

# Guardar configuración para auto-start
pm2 save
pm2 startup
# (copia y ejecuta el comando que te muestra)

# Verificar
pm2 status
pm2 logs wondertech-pricelist
```

### Paso 5: Configurar Nginx
```bash
# Copiar configuración
sudo cp nginx.conf /etc/nginx/sites-available/wondertech-pricelist

# Editar para poner tu dominio
sudo nano /etc/nginx/sites-available/wondertech-pricelist

# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/wondertech-pricelist /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# (Opcional) SSL con Certbot
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

---

## ✅ Verificar Deploy

```bash
# Desde el servidor
curl http://localhost:5008/

# Ver status
pm2 status
sudo systemctl status nginx
```

**Desde tu navegador:**
```
http://tu-dominio.com/
http://tu-dominio.com/webhook/generate-all
```

---

## 🔧 Comandos Esenciales

### PM2
```bash
pm2 status                    # Ver estado
pm2 logs wondertech-pricelist # Ver logs
pm2 restart wondertech-pricelist # Reiniciar
pm2 monit                     # Monitoreo en tiempo real
```

### Nginx
```bash
sudo systemctl status nginx   # Status
sudo systemctl restart nginx  # Reiniciar
sudo nginx -t                 # Probar config
sudo tail -f /var/log/nginx/pricelist-error.log  # Ver errores
```

---

## 🐛 Problemas Comunes

### ❌ Aplicación no inicia
```bash
pm2 logs wondertech-pricelist --err
source /var/www/pricelist/venv/bin/activate
python /var/www/pricelist/api_wondertech.py
```

### ❌ Error 502 Bad Gateway
```bash
# Verificar que PM2 está corriendo
pm2 status

# Verificar Nginx config
sudo nginx -t

# Reiniciar todo
pm2 restart wondertech-pricelist
sudo systemctl restart nginx
```

### ❌ Puerto ya en uso
```bash
sudo lsof -i :5008
sudo kill -9 <PID>
```

---

## 📁 Estructura de Archivos

```
/var/www/pricelist/
├── api_wondertech.py          # Aplicación principal
├── wondertech_pricelist_env.py # Lógica de generación
├── ecosystem.config.js        # Config PM2
├── requirements.txt           # Dependencias Python
├── .env                       # Credenciales (¡PROTEGER!)
├── venv/                      # Entorno virtual
├── PDFs/
│   ├── output/                # PDFs generados
│   └── img/                   # Imágenes header/footer
└── logs/                      # Logs de PM2
```

---

## 🔐 Seguridad

```bash
# Proteger archivo .env
chmod 600 /var/www/pricelist/.env

# Firewall básico
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

---

## 📞 ¿Necesitas Ayuda?

- 📖 Guía completa: `DEPLOYMENT.md`
- 🔍 Logs: `pm2 logs wondertech-pricelist`
- 📊 Status: `pm2 status`
- 🌐 Docs Nginx: https://nginx.org/en/docs/
- 🚀 Docs PM2: https://pm2.keymetrics.io/docs/usage/quick-start/

---

**¡Listo! Tu generador de listas de precios está corriendo 🎉**
