# Mensaje para el Administrador del Servidor

---

## 📧 Template: Solicitud de Ruta en Nginx

**Asunto:** Agregar location para WEBHOOK_PRICELIST en nginx

---

Hola!

Desplegué un nuevo webhook en el servidor y necesito que agregues una `location` en el
server block de nginx para hacerlo accesible.

### 📍 Estado Actual
- ✅ El webhook está en: `/var/www/webhooks/WEBHOOK_PRICELIST`
- ✅ Escuchando en: `http://127.0.0.1:5000`
- ✅ Proceso PM2 activo y monitoreado

### 🔧 Lo que necesito

Agregar esta `location` en el server block de nginx que ya compartimos:

```nginx
location /pricelist/ {
    proxy_pass http://127.0.0.1:5000/;
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

### 🔗 Endpoints que quedarán disponibles

- `https://TU_DOMINIO/pricelist/` — Health check
- `https://TU_DOMINIO/pricelist/webhook/odoo` — Webhook principal (para Odoo)
- `https://TU_DOMINIO/pricelist/webhook/generate-all` — Generar todas las listas
- `https://TU_DOMINIO/pricelist/webhook/generate/Lista_Business` — Generar lista específica

### 📝 Notas
- Es una aplicación Flask (Python) corriendo con PM2
- Genera PDFs que se guardan en el servidor
- El webhook será llamado desde Odoo y ocasionalmente manualmente
- La generación de PDFs puede tardar 10-30 segundos

### 🧪 Verificación

Una vez agregues la location, ejecuta:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

Yo verificaré desde mi lado con:
```bash
curl https://TU_DOMINIO/pricelist/
```

¡Gracias!

---

## 📞 Info para el Admin

Si necesitas verificar:
- El webhook está en: `/var/www/webhooks/WEBHOOK_PRICELIST`
- Logs PM2: `pm2 logs WEBHOOK_PRICELIST`
- Verificar que corre: `curl http://127.0.0.1:5000/`

---
