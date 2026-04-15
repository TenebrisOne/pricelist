#!/bin/bash
# ============================================
# Install Script - Wondertech PriceList
# Ejecutar EN el servidor despues del deploy
# ============================================

set -e

# ──── Colores ────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
DARK='\033[2;37m'
NC='\033[0m'

APP_DIR="/var/www/webhooks/WEBHOOK_PRICELIST"
APP_NAME="WEBHOOK_PRICELIST"
PORT=5000

# ──── Funciones visuales ────
header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    padding=$((58 - ${#1}))
    echo -e "${CYAN}║$(printf '%*s' $padding '')║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
    echo ""
}

ok() {
    echo -e "  ${GREEN}✓ $1${NC}"
}

warn() {
    echo -e "  ${YELLOW}⚠ $1${NC}"
}

fail() {
    echo -e "  ${RED}✗ $1${NC}"
}

info() {
    echo -e "  ${DARK}→ $1${NC}"
}

# ──── Header ────

header "WONDERTECH - Instalacion de PriceList"

# ──── Paso 1: Verificar directorio ────

section "Paso 1 de 8 - Verificando directorio"

if [ ! -d "$APP_DIR" ]; then
    fail "No se encontro: $APP_DIR"
    echo "   Haz el deploy primero"
    exit 1
fi

cd "$APP_DIR"
ok "Directorio encontrado: $APP_DIR"

# ──── Paso 2: Verificar archivos ────

section "Paso 2 de 8 - Verificando archivos"

REQUIRED_FILES=("api_wondertech.py" "wondertech_pricelist_env.py" "requirements.txt" "ecosystem.config.js" ".env" "install.sh")
MISSING=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        ok "$file"
    else
        fail "$file - FALTA"
        MISSING+=("$file")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    fail "Faltan archivos: ${MISSING[*]}"
    exit 1
fi

# ──── Paso 3: Verificar Python ────

section "Paso 3 de 8 - Verificando Python"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    ok "Python3 encontrado: $($PYTHON_CMD --version 2>&1)"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    ok "Python encontrado: $($PYTHON_CMD --version 2>&1)"
else
    fail "Python no esta instalado"
    echo "   Pide al admin: sudo apt install -y python3 python3-pip python3-venv"
    exit 1
fi

# ──── Paso 4: Verificar .env ────

section "Paso 4 de 8 - Verificando .env"

if ! grep -q "USE_PRODUCTION" .env 2>/dev/null; then
    fail "El .env no tiene la configuracion esperada"
    exit 1
fi

ok ".env configurado correctamente"

# ──── Paso 5: Entorno virtual ────

section "Paso 5 de 8 - Configurando entorno virtual"

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    ok "Entorno virtual creado"
else
    ok "Entorno virtual ya existe"
fi

info "Activando entorno virtual..."
source venv/bin/activate

# ──── Paso 6: Dependencias ────

section "Paso 6 de 8 - Instalando dependencias"

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "Dependencias instaladas"

# ──── Paso 7: Directorios ────

section "Paso 7 de 8 - Creando directorios"

mkdir -p PDFs/output PDFs/img logs
chmod 600 .env
chmod -R 755 PDFs
ok "Directorios creados: PDFs/output, PDFs/img, logs"

# ──── Paso 8: PM2 ────

section "Paso 8 de 8 - Iniciando con PM2"

if ! command -v pm2 &> /dev/null; then
    warn "PM2 no esta instalado"
    if command -v npm &> /dev/null; then
        info "Instalando PM2..."
        npm install -g pm2 --quiet
        ok "PM2 instalado"
    else
        fail "npm no disponible"
        echo "   Pide al admin: sudo apt install -y nodejs npm"
        exit 1
    fi
else
    ok "PM2 ya esta instalado"
fi

# Verificar puerto
if lsof -i :$PORT &> /dev/null 2>&1; then
    warn "Puerto $PORT ya en uso - reiniciando..."
    pm2 delete "$APP_NAME" 2>/dev/null || true
fi

info "Iniciando aplicacion..."
pm2 start ecosystem.config.js --name "$APP_NAME" --silent
pm2 save --silent
ok "Aplicacion iniciada como: $APP_NAME"

# ──── Verificacion ────

sleep 2
if curl -s http://localhost:$PORT/ | grep -q "ok" 2>/dev/null; then
    echo ""
    ok "Aplicacion respondiendo correctamente en puerto $PORT"
else
    echo ""
    warn "La aplicacion no responde aun (puede estar iniciando)"
fi

# ──── Resumen final ────

header "Instalacion completada!"

echo -e "  ${YELLOW}📊 Estado actual:${NC}"
pm2 status "$APP_NAME"

echo ""
echo -e "  ${YELLOW}🔗 Endpoints locales:${NC}"
echo -e "  ${CYAN}     http://localhost:$PORT/${NC}"
echo -e "  ${CYAN}     http://localhost:$PORT/webhook/odoo${NC}"
echo -e "  ${CYAN}     http://localhost:$PORT/webhook/generate-all${NC}"
echo -e "  ${CYAN}     http://localhost:$PORT/webhook/generate/Lista_Business${NC}"

echo ""
echo -e "  ${YELLOW}📋 Proximos pasos:${NC}"
echo ""
echo -e "  ${BLUE}  ┌─ 1. Verificar logs:${NC}"
echo -e "  ${BLUE}  │   ${CYAN}pm2 logs WEBHOOK_PRICELIST${NC}"
echo -e "  ${BLUE}  │"
echo -e "  ${BLUE}  ├─ 2. Enviar al admin para nginx:${NC}"
echo -e "  ${BLUE}  │   ${CYAN}ADMIN_REQUEST_TEMPLATE.md${NC}"
echo -e "  ${BLUE}  │"
echo -e "  ${BLUE}  └─ 3. Despues de nginx, probar:${NC}"
echo -e "  ${BLUE}      ${CYAN}curl https://TU_DOMINIO/pricelist/${NC}"

echo ""
echo -e "  ${DARK}─────────────────────────────────────────────────${NC}"
echo ""
echo -e "  ${GREEN}¡Listo! El webhook esta corriendo 🚀${NC}"
echo ""
