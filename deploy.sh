#!/bin/bash

# ============================================
# Script de Deploy Rápido - Wondertech Pricelist
# ============================================
# Uso: bash deploy.sh
# ============================================

set -e  # Detener en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
APP_DIR="/var/www/pricelist"
APP_NAME="wondertech-pricelist"

echo -e "${BLUE}"
echo "================================================"
echo "  WONDERTECH - Deploy Automático"
echo "================================================"
echo -e "${NC}"

# Verificar que se está ejecutando como root o con sudo
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}⚠️  Advertencia: Este script debe ejecutarse como usuario normal con sudo${NC}"
    echo -e "${YELLOW}   No lo ejecutes directamente como root${NC}"
    exit 1
fi

# Función para imprimir mensajes
print_step() {
    echo -e "\n${BLUE}📦 $1${NC}"
    echo "------------------------------------------------"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Paso 1: Verificar dependencias
print_step "Verificando dependencias..."

check_package() {
    if dpkg -s "$1" 2>/dev/null | grep -q "Status: install ok installed"; then
        print_success "$1 está instalado"
        return 0
    else
        echo -e "${YELLOW}⚠️  $1 no está instalado${NC}"
        return 1
    fi
}

PACKAGES_NEEDED=("python3" "python3-pip" "python3-venv" "nginx" "nodejs" "npm")
MISSING_PACKAGES=()

for pkg in "${PACKAGES_NEEDED[@]}"; do
    if ! check_package "$pkg"; then
        MISSING_PACKAGES+=("$pkg")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}📦 Instalando paquetes faltantes: ${MISSING_PACKAGES[*]}${NC}"
    sudo apt update
    sudo apt install -y "${MISSING_PACKAGES[@]}"
fi

# Verificar PM2
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}📦 Instalando PM2...${NC}"
    sudo npm install -g pm2
fi

print_success "Dependencias verificadas"

# Paso 2: Crear directorio de la aplicación
print_step "Creando directorio de la aplicación..."

if [ ! -d "$APP_DIR" ]; then
    sudo mkdir -p "$APP_DIR"
    sudo chown $USER:$USER "$APP_DIR"
    print_success "Directorio creado: $APP_DIR"
else
    print_success "Directorio ya existe: $APP_DIR"
fi

# Paso 3: Configurar entorno virtual
print_step "Configurando entorno virtual de Python..."

cd "$APP_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Entorno virtual creado"
else
    print_success "Entorno virtual ya existe"
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias de Python
if [ -f "requirements.txt" ]; then
    print_step "Instalando dependencias de Python..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Dependencias de Python instaladas"
else
    print_error "No se encontró requirements.txt"
    echo "   Asegúrate de haber subido el código al directorio $APP_DIR"
    exit 1
fi

# Paso 4: Verificar archivo .env
print_step "Verificando configuración..."

if [ ! -f ".env" ]; then
    print_error "No se encontró el archivo .env"
    echo "   Debes crear el archivo .env con las credenciales de Odoo"
    echo "   Ejemplo: nano $APP_DIR/.env"
    exit 1
else
    print_success "Archivo .env encontrado"
fi

# Paso 5: Crear directorios necesarios
print_step "Creando directorios necesarios..."

mkdir -p PDFs/output PDFs/img logs
print_success "Directorios creados"

# Paso 6: Verificar PM2 config
print_step "Configurando PM2..."

if [ ! -f "ecosystem.config.js" ]; then
    print_error "No se encontró ecosystem.config.js"
    echo "   Debes subir el archivo ecosystem.config.js a $APP_DIR"
    exit 1
fi

# Paso 7: Iniciar/reiniciar aplicación con PM2
print_step "Iniciando aplicación con PM2..."

# Detener si ya está corriendo
pm2 delete "$APP_NAME" 2>/dev/null || true

# Iniciar aplicación
pm2 start ecosystem.config.js

# Guardar configuración de PM2
pm2 save

print_success "Aplicación iniciada con PM2"

# Paso 8: Configurar Nginx
print_step "Configurando Nginx..."

if [ -f "nginx.conf" ]; then
    echo "   ¿Deseas configurar Nginx ahora? (s/n)"
    read -r CONFIGURE_NGINX
    
    if [ "$CONFIGURE_NGINX" = "s" ] || [ "$CONFIGURE_NGINX" = "S" ]; then
        echo "   Ingresa tu dominio (o deja vacío para usar IP):"
        read -r DOMAIN
        
        if [ -n "$DOMAIN" ]; then
            # Actualizar dominio en la configuración de Nginx
            sed "s/pricelist.wondertech.com.co/$DOMAIN/g" nginx.conf > "/tmp/nginx-pricelist.conf"
            sudo cp "/tmp/nginx-pricelist.conf" /etc/nginx/sites-available/wondertech-pricelist
        else
            sudo cp nginx.conf /etc/nginx/sites-available/wondertech-pricelist
        fi
        
        # Crear enlace simbólico
        sudo ln -sf /etc/nginx/sites-available/wondertech-pricelist /etc/nginx/sites-enabled/
        
        # Probar configuración
        if sudo nginx -t; then
            sudo systemctl restart nginx
            print_success "Nginx configurado y reiniciado"
        else
            print_error "Error en la configuración de Nginx"
            echo "   Verifica el archivo: /etc/nginx/sites-available/wondertech-pricelist"
            exit 1
        fi
    else
        echo -e "${YELLOW}⏭️  Saltando configuración de Nginx${NC}"
        echo "   Puedes configurarlo manualmente más tarde con:"
        echo "   sudo cp nginx.conf /etc/nginx/sites-available/wondertech-pricelist"
        echo "   sudo ln -s /etc/nginx/sites-available/wondertech-pricelist /etc/nginx/sites-enabled/"
        echo "   sudo nginx -t && sudo systemctl restart nginx"
    fi
else
    echo -e "${YELLOW}⚠️  No se encontró nginx.conf${NC}"
    echo "   Puedes configurarlo manualmente más tarde"
fi

# Paso 9: Mostrar información final
print_step "¡Deploy completado!"

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}  ✅ Deploy exitoso!${NC}"
echo -e "${GREEN}================================================${NC}"

echo -e "\n📊 Estado de la aplicación:"
pm2 status

echo -e "\n🔗 Endpoints disponibles:"
echo "   - http://localhost:5008/"
echo "   - http://localhost:5008/webhook/odoo"
echo "   - http://localhost:5008/webhook/generate-all"
echo "   - http://localhost:5008/webhook/generate/Lista_Business"

if command -v pm2-logrotate &> /dev/null; then
    echo -e "\n📝 Logs disponibles en:"
    echo "   - PM2 logs: pm2 logs $APP_NAME"
    echo "   - Archivos: $APP_DIR/logs/"
else
    echo -e "\n📝 Para ver logs: pm2 logs $APP_NAME"
fi

echo -e "\n${YELLOW}📌 Próximos pasos:${NC}"
echo "   1. Verifica que la aplicación está corriendo: curl http://localhost:5008/"
echo "   2. Configura Nginx si no lo hiciste"
echo "   3. Configura SSL con Certbot (recomendado): sudo certbot --nginx"
echo "   4. Abre los puertos en el firewall si es necesario"

echo -e "\n${BLUE}📖 Guía completa disponible en: DEPLOYMENT.md${NC}"
echo -e "${BLUE}================================================${NC}"

# Mostrar comandos útiles
echo -e "\n${YELLOW}💡 Comandos útiles:${NC}"
echo -e "   Ver status:     ${GREEN}pm2 status${NC}"
echo -e "   Ver logs:       ${GREEN}pm2 logs $APP_NAME${NC}"
echo -e "   Reiniciar:      ${GREEN}pm2 restart $APP_NAME${NC}"
echo -e "   Detener:        ${GREEN}pm2 stop $APP_NAME${NC}"
echo -e "   Ver monitoreo:  ${GREEN}pm2 monit${NC}"

echo -e "\n${GREEN}¡Listo! Tu aplicación está corriendo.${NC}"
