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
MAGENTA='\033[0;35m'
DARK='\033[2;37m'
NC='\033[0m'
BOLD='\033[1m'

APP_DIR="/var/www/webhooks/WEBHOOK_PRICELIST"
APP_NAME="WEBHOOK_PRICELIST"
PORT=5008

# ──── Funciones visuales ────

timestamp() {
    date +%H:%M:%S
}

header() {
    echo ""
    echo -e "${CYAN}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}  ${BOLD}WONDERTECH - $1${NC}"
    echo -e "${CYAN}│${NC}  ${DARK}$(date '+%d/%m/%Y %H:%M:%S')${NC}"
    echo -e "${CYAN}│${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

section() {
    echo ""
    echo -e "${CYAN}╭──────────────────────────────────────────────────────────╮${NC}"
    printf "${CYAN}│${NC} %-56s${CYAN}│${NC}\n" " $1"
    echo -e "${CYAN}╰──────────────────────────────────────────────────────────╯${NC}"
}

log_ok() {
    echo -e "[$(timestamp)] ${GREEN}OK    │${NC} ${GREEN}$1${NC}"
}

log_info() {
    echo -e "[$(timestamp)] ${CYAN}INFO  │${NC} ${WHITE:- }$1${NC}"
}

log_warn() {
    echo -e "[$(timestamp)] ${YELLOW}WARN  │${NC} ${YELLOW}$1${NC}"
}

log_error() {
    echo -e "[$(timestamp)] ${RED}ERROR │${NC} ${RED}$1${NC}"
}

log_step() {
    echo -e "[$(timestamp)] ${MAGENTA}STEP  │${NC} ${MAGENTA}[$1/$2]${NC} ${WHITE:- }$3${NC}"
}

separator() {
    echo ""
    echo -e "  ${DARK}══════════════════════════════════════════════════════════${NC}"
    echo ""
}

summary_line() {
    key="$1"
    val="$2"
    printf "  ${CYAN}%-20s${NC} │ %s\n" "$key" "$val"
}

# ──── Header ────

header "Instalacion de PriceList"

log_info "App      : $APP_NAME"
log_info "Directorio: $APP_DIR"
log_info "Puerto   : $PORT"

# ──── Paso 1: Verificar directorio ────

section "Paso 1 de 8 - Verificando directorio"

if [ ! -d "$APP_DIR" ]; then
    log_error "No se encontro: $APP_DIR"
    echo "   Haz el deploy primero"
    exit 1
fi

cd "$APP_DIR"
log_ok "Directorio encontrado: $APP_DIR"

# ──── Paso 2: Verificar archivos ────

section "Paso 2 de 8 - Verificando archivos"

REQUIRED_FILES=("api_wondertech.py" "wondertech_pricelist_env.py" "requirements.txt" "ecosystem.config.js" ".env" "install.sh")
MISSING=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" 2>/dev/null | cut -f1)
        log_ok "$file  ($size)"
    else
        log_error "$file - FALTA"
        MISSING+=("$file")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    separator
    log_error "Faltan ${#MISSING[@]} archivo(s): ${MISSING[*]}"
    exit 1
fi

# ──── Paso 3: Verificar Python ────

section "Paso 3 de 8 - Verificando Python"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PY_VER=$($PYTHON_CMD --version 2>&1)
    log_ok "Python3 encontrado: $PY_VER"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PY_VER=$($PYTHON_CMD --version 2>&1)
    log_ok "Python encontrado: $PY_VER"
else
    log_error "Python no esta instalado"
    echo ""
    echo "   Ejecuta: sudo apt install -y python3 python3-pip python3-venv"
    exit 1
fi

# ──── Paso 4: Verificar .env ────

section "Paso 4 de 8 - Verificando .env"

if ! grep -q "USE_PRODUCTION" .env 2>/dev/null; then
    log_error "El .env no tiene la configuracion esperada"
    echo ""
    echo "   Asegurate de que el .env fue subido correctamente"
    exit 1
fi

if grep -q "TU_API_KEY\|TU_TOKEN_SECRETO" .env 2>/dev/null; then
    log_warn "El .env parece tener credenciales de ejemplo"
    echo ""
    echo "   Edita el .env con las credenciales reales de produccion"
    exit 1
fi

log_ok ".env configurado correctamente (credenciales validas)"

# ──── Paso 5: Entorno virtual ────

section "Paso 5 de 8 - Configurando entorno virtual"

if [ ! -d "venv" ]; then
    log_info "Creando entorno virtual..."
    $PYTHON_CMD -m venv venv
    log_ok "Entorno virtual creado: venv/"
else
    log_ok "Entorno virtual ya existe: venv/"
fi

log_info "Activando entorno virtual..."
source venv/bin/activate
log_ok "Entorno virtual activado"

# ──── Paso 6: Dependencias ────

section "Paso 6 de 8 - Instalando dependencias"

log_info "Actualizando pip..."
pip install --upgrade pip --quiet 2>/dev/null

log_info "Instalando dependencias de requirements.txt..."
pip install -r requirements.txt --quiet 2>/dev/null
log_ok "Dependencias instaladas ($([ -f requirements.txt ] && wc -l < requirements.txt || echo '?') paquetes)"

# ──── Paso 7: Directorios ────

section "Paso 7 de 8 - Creando directorios"

mkdir -p PDFs/output PDFs/img logs
chmod 600 .env
chmod -R 755 PDFs

log_ok "PDFs/output/  - PDFs generados"
log_ok "PDFs/img/     - Imagenes header/footer"
log_ok "logs/         - Logs de PM2"
log_ok ".env chmod 600 (protegido)"

# ──── Paso 8: PM2 ────

section "Paso 8 de 8 - Iniciando con PM2"

if ! command -v pm2 &> /dev/null; then
    log_warn "PM2 no esta instalado"
    if command -v npm &> /dev/null; then
        log_info "Instalando PM2..."
        npm install -g pm2 --quiet 2>/dev/null
        log_ok "PM2 instalado"
    else
        log_error "npm no disponible"
        echo ""
        echo "   Ejecuta: sudo apt install -y nodejs npm"
        exit 1
    fi
else
    PM2_VER=$(pm2 --version 2>/dev/null)
    log_ok "PM2 ya esta instalado (v$PM2_VER)"
fi

# Verificar puerto
if lsof -i :$PORT &> /dev/null 2>&1; then
    log_warn "Puerto $PORT ya en uso - limpiando proceso anterior..."
    pm2 delete "$APP_NAME" 2>/dev/null || true
    log_ok "Proceso anterior eliminado"
else
    log_ok "Puerto $PORT disponible"
fi

log_info "Iniciando aplicacion..."
cd "$APP_DIR"
pm2 start ecosystem.config.js --name "$APP_NAME" --silent 2>/dev/null
pm2 save --silent 2>/dev/null
log_ok "Aplicacion iniciada como: $APP_NAME"

# ──── Verificacion ────

echo ""
log_info "Esperando 2 segundos para que inicie..."
sleep 2

if curl -s http://localhost:$PORT/ 2>/dev/null | grep -q "ok"; then
    log_ok "Aplicacion respondiendo correctamente en http://localhost:$PORT/"
else
    log_warn "La aplicacion no responde aun (puede estar iniciando)"
    log_info "Verifica con: curl http://localhost:$PORT/"
fi

# ──── Resumen final ────

separator

header "Instalacion completada"

echo -e "  ${BOLD}Estado de PM2:${NC}"
echo ""
pm2 status "$APP_NAME"

separator

echo -e "  ${BOLD}Endpoints locales:${NC}"
echo ""
echo -e "    ${CYAN}Health check${NC}        http://localhost:$PORT/"
echo -e "    ${CYAN}Webhook Odoo${NC}        http://localhost:$PORT/webhook/odoo"
echo -e "    ${CYAN}Generar todas${NC}       http://localhost:$PORT/webhook/generate-all"
echo -e "    ${CYAN}Generar una${NC}         http://localhost:$PORT/webhook/generate/Lista_Business"

separator

echo -e "  ${BOLD}Proximos pasos:${NC}"
echo ""
echo -e "    ${BLUE}[1]${NC} Verificar logs:"
echo -e "        ${CYAN}pm2 logs WEBHOOK_PRICELIST --lines 50${NC}"
echo ""
echo -e "    ${BLUE}[2]${NC} Enviar al admin para configurar nginx:"
echo -e "        ${CYAN}ADMIN_REQUEST_TEMPLATE.md${NC}"
echo ""
echo -e "    ${BLUE}[3]${NC} Despues de configurar nginx, probar:"
echo -e "        ${CYAN}curl https://TU_DOMINIO/pricelist/${NC}"

separator

echo -e "  ${BOLD}Documentacion:${NC}"
echo ""
echo -e "    Guia completa        ${DARK}DEPLOYMENT_SERVER.md${NC}"
echo -e "    Resumen rapido       ${DARK}README_DEPLOY.md${NC}"
echo -e "    Template para admin  ${DARK}ADMIN_REQUEST_TEMPLATE.md${NC}"
echo -e "    Deploy sin sudo      ${DARK}DEPLOY_NO_SUDO.md${NC}"

separator

echo -e "  ${GREEN}${BOLD}¡Listo! El webhook esta corriendo 🚀${NC}"
echo ""
