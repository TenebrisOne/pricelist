# Mensaje para el Administrador del Servidor

---

## 📧 Template: Solicitud de Configuración Nginx

**Asunto:** Solicitud de ruta en Nginx para webhook de generación de listas de precios

---

Hola!

He desplegado una aplicación de generación de listas de precios en el servidor y necesito 
que agregues una ruta en la configuración de Nginx para hacerla accesible vía webhook.

### 📍 Estado Actual
- ✅ La aplicación ya está corriendo con PM2 en: `/home/TU_USUARIO/apps/pricelist`
- ✅ Escuchando en: `http://127.0.0.1:5008`
- ✅ Proceso PM2 activo y monitoreado

### 🔧 Lo que necesito

**Opción A (Recomendada):** Agregar como subruta en el server block existente

```nginx
# En el server block de nginx.conf (ej: /etc/nginx/sites-available/default o el que use)
location /pricelist/ {
    proxy_pass http://127.0.0.1:5008/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeouts para generación de PDFs (puede tardar)
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
}
```

**Opción B:** Crear un subdominio dedicado

```nginx
server {
    listen 80;
    server_name pricelist.TU_DOMINIO_ACTUAL.com;

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

### 🔗 Endpoints que quedarán disponibles

Con la **Opción A** (subruta):
- `https://TU_DOMINIO/pricelist/` - Health check
- `https://TU_DOMINIO/pricelist/webhook/odoo` - Webhook principal (para Odoo)
- `https://TU_DOMINIO/pricelist/webhook/generate-all` - Generar todas las listas
- `https://TU_DOMINIO/pricelist/webhook/generate/Lista_Business` - Generar lista específica

Con la **Opción B** (subdominio):
- `https://pricelist.TU_DOMINIO.com/` - Health check
- `https://pricelist.TU_DOMINIO.com/webhook/odoo` - Webhook principal
- `https://pricelist.TU_DOMINIO.com/webhook/generate-all` - Generar todas
- `https://pricelist.TU_DOMINIO.com/webhook/generate/Lista_Business` - Generar específica

### 📝 Notas
- Es una aplicación Flask (Python) corriendo con Gunicorn a través de PM2
- No necesita archivos estáticos públicos
- Genera PDFs que se guardan en el servidor (no necesita acceso público a ellos)
- El webhook será llamado desde Odoo (sistema ERP) y ocasionalmente manualmente
- La generación de PDFs puede tardar 10-30 segundos dependiendo de la cantidad de productos

### 🧪 Verificación después de configurar

Una vez agregues la configuración, por favor ejecuta:
```bash
sudo nginx -t  # Verificar que la configuración es válida
sudo systemctl reload nginx  # Aplicar cambios
```

Yo verificaré desde mi lado con:
```bash
curl https://TU_DOMINIO/pricelist/
```

¿Puedes avisarme cuando lo configures para que pueda probarlo?

¡Gracias!

---

## 📞 Información de Contacto

Si necesitas más detalles o hay algún problema:
- La app está en: `/home/TU_USUARIO/apps/pricelist`
- Logs de PM2: `pm2 logs wondertech-pricelist`
- Puedes verificar que está corriendo con: `curl http://127.0.0.1:5008/`

---

## 🔐 Seguridad (opcional mencionar)

Si el webhook necesita protección:
- Puedo agregar autenticación por token en la app
- O podemos agregar basic auth en nginx si es necesario
- El webhook de Odoo puede enviar un token en los headers

---

**Versión:** 1.0  
**Fecha:** Abril 2026
