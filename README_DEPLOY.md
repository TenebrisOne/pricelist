# README - Wondertech PriceList Webhook

## 🚀 Deploy Rápido

### Opción 1: Script automático (Windows PowerShell)
```powershell
cd "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios"
.\deploy.ps1
```

### Opción 2: Manual
Sigue la guía completa en **DEPLOYMENT_SERVER.md**

---

## 📁 Archivos de Deploy

| Archivo | Propósito |
|---------|-----------|
| `DEPLOYMENT_SERVER.md` | Guía completa paso a paso para tu servidor |
| `deploy.ps1` | Script de PowerShell para subir archivos automáticamente |
| `ADMIN_REQUEST_TEMPLATE.md` | Mensaje para enviar al admin del servidor (configurar nginx) |
| `ecosystem.config.js` | Configuración de PM2 (ya lista para usar) |
| `DEPLOY_NO_SUDO.md` | Guía general para deploys sin permisos sudo |
| `QUICK_START.md` | Resumen rápido de 5 pasos |

---

## 🎯 Tu Configuración

- **Local:** `c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios`
- **Servidor:** `cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01`
- **Remoto:** `/var/www/webhooks/WEBHOOK_PRICELIST`
- **Puerto:** 5000

---

## 📋 Pasos para Deploy

### En tu Windows (PowerShell):
```powershell
# Ejecutar el script de deploy
cd "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios"
.\deploy.ps1
```

### En el servidor (SSH):
```bash
# Conectar
ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01
cd /home/cristianwonder/apps/pricelist

# Crear .env
nano .env

# Configurar Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Crear directorios
mkdir -p PDFs/output PDFs/img logs

# Iniciar con PM2
pm2 start ecosystem.config.js
pm2 save

# Verificar
curl http://localhost:5000/
```

### Enviar al Admin:
Envía el contenido de `ADMIN_REQUEST_TEMPLATE.md` al administrador del servidor para que configure nginx.

---

## 🔗 Endpoints del Webhook

Una vez configurado nginx:

- `https://TU_DOMINIO/pricelist/` - Health check
- `https://TU_DOMINIO/pricelist/webhook/odoo` - Webhook para Odoo
- `https://TU_DOMINIO/pricelist/webhook/generate-all` - Generar todas las listas
- `https://TU_DOMINIO/pricelist/webhook/generate/Lista_Business` - Generar lista específica

---

## 🔧 Comandos Útiles

### PM2 (en el servidor):
```bash
pm2 status                    # Ver estado
pm2 logs wondertech-pricelist # Ver logs
pm2 restart wondertech-pricelist # Reiniciar
pm2 monit                     # Monitoreo
```

### Actualizar código:
```powershell
# Desde Windows PowerShell
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude 'venv' --exclude '.env' \
  "./" cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01:/home/cristianwonder/apps/pricelist/

# Luego en el servidor:
ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01
cd /home/cristianwonder/apps/pricelist
source venv/bin/activate
pm2 restart wondertech-pricelist
```

---

## 🐛 Troubleshooting

Ver **DEPLOYMENT_SERVER.md** sección de Troubleshooting para soluciones completas.

### Problemas comunes:

| Problema | Solución |
|----------|----------|
| Permission denied | Verifica permisos con `ls -la` |
| python3 no encontrado | Pide al admin que instale python3 |
| Puerto 5000 en uso | Cambia el puerto en `.env` y `ecosystem.config.js` |
| App no inicia | Revisa logs: `pm2 logs wondertech-pricelist` |

---

## 📞 Soporte

- 📖 Guía completa: `DEPLOYMENT_SERVER.md`
- 🔍 Logs del servidor: `ssh cristianwonder@ubuntu-s-1vcpu-1gb-sfo3-01`
- 💡 Docs: `DEPLOY_NO_SUDO.md`

---

**Versión:** 1.0  
**Fecha:** Abril 2026
