# ============================================
# Deploy Script - Wondertech PriceList
# Soporta: GitHub, pscp (PuTTY), plink
# Ejecutar desde PowerShell
# ============================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

# Configuracion
$LOCAL_PATH = "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios"
$REMOTE_USER = "cristianwonder"
$REMOTE_HOST = "143.244.180.163"
$REMOTE_WEBHOOKS = "/var/www/webhooks"
$PROJECT_NAME = "WEBHOOK_PRICELIST"
$REMOTE_PATH = "$REMOTE_WEBHOOKS/$PROJECT_NAME"
$SSH_KEY = "C:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\cristianwonder.ppk"
$PLINK = "C:\Program Files\PuTTY\plink.exe"
$PSCP = "C:\Program Files\PuTTY\pscp.exe"
$PORT = 5000

# ──── Funciones visuales ────

function Header($title) {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  $title" -ForegroundColor Cyan
    $padding = 58 - $title.Length
    Write-Host ("║" + " " * $padding + "║") -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Section($title) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════" -ForegroundColor DarkCyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════" -ForegroundColor DarkCyan
    Write-Host ""
}

function Step($num, $title) {
    Write-Host "  [$num] $title" -ForegroundColor White
}

function Success($msg) {
    Write-Host "  ✓ " -ForegroundColor Green -NoNewline
    Write-Host $msg -ForegroundColor Green
}

function Warning($msg) {
    Write-Host "  ⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $msg -ForegroundColor Yellow
}

function Error($msg) {
    Write-Host "  ✗ " -ForegroundColor Red -NoNewline
    Write-Host $msg -ForegroundColor Red
}

function Info($msg) {
    Write-Host "  → " -ForegroundColor DarkGray -NoNewline
    Write-Host $msg -ForegroundColor DarkGray
}

function Progress($file, $total) {
    $pct = [math]::Round(($file / $total) * 100)
    $filled = [math]::Round($pct / 5)
    $empty = 20 - $filled
    $bar = ("█" * $filled) + ("░" * $empty)
    Write-Host "`r  [$bar] $pct%" -ForegroundColor Cyan -NoNewline
}

function FinishProgress {
    Write-Host ""
}

# ──── Header ────

Header "WONDERTECH - Deploy v2.0"

Step "📁" "Directorio: $(Split-Path $LOCAL_PATH -Leaf)"
Step "🖥 " "Servidor: $REMOTE_USER@$REMOTE_HOST"
Step "📂" "Remoto:    $REMOTE_PATH"
Write-Host ""

# ──── Verificar herramientas ────

Section "Verificando herramientas"

$hasGit = Get-Command git -ErrorAction SilentlyContinue
$hasPlink = Test-Path $PLINK
$hasPscp = Test-Path $PSCP
$hasKey = Test-Path $SSH_KEY

if ($hasGit) { Success "Git instalado" } else { Error "Git no encontrado" }
if ($hasPlink) { Success "PuTTY plink disponible" } else { Warning "plink no encontrado en: $PLINK" }
if ($hasPscp) { Success "PuTTY pscp disponible" } else { Warning "pscp no encontrado en: $PSCP" }
if ($hasKey) { Success "SSH key encontrada" } else { Error "SSH key NO encontrada: $SSH_KEY" }

if (-not $hasKey) {
    Write-Host ""
    Error "No se encontro la key SSH"
    exit 1
}

# ──── Verificar archivos ────

Section "Verificando archivos del proyecto"

$requiredFiles = @(
    "api_wondertech.py",
    "wondertech_pricelist_env.py",
    "requirements.txt",
    "ecosystem.config.js",
    ".env",
    "install.sh"
)

$missingFiles = @()
$fileCount = $requiredFiles.Count
$i = 0

foreach ($file in $requiredFiles) {
    $i++
    if (Test-Path $file) {
        Success "$file"
    } else {
        Error "$file - FALTA"
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Error "Faltan $($missingFiles.Count) archivo(s): $($missingFiles -join ', ')"
    exit 1
}

# ──── Elegir metodo de deploy ────

Section "Selecciona el metodo de deploy"

$options = @()
$optionNum = 1

if ($hasGit) {
    Write-Host "  $optionNum) 🔄 Git clone/pull en el servidor" -ForegroundColor White
    $options += "git"
    $optionNum++
}

if ($hasPscp -and $hasPlink) {
    Write-Host "  $optionNum) 📤 pscp (PuTTY - subir archivos)" -ForegroundColor White
    $options += "pscp"
    $optionNum++
}

Write-Host "  $optionNum) 🔧 Solo configurar (archivos ya subidos)" -ForegroundColor White
$options += "configurar"
Write-Host ""

$choice = Read-Host "  Opcion (1-$($options.Count))"
$choiceNum = [int]$choice - 1

if ($choiceNum -lt 0 -or $choiceNum -ge $options.Count) {
    Write-Host ""
    Error "Opcion no valida"
    exit 1
}

$selectedMethod = $options[$choiceNum]

# ──── OPCION: Git ────

if ($selectedMethod -eq "git") {
    Section "Deploy via Git"

    Write-Host "  Ingresa la URL de tu repositorio GitHub:" -ForegroundColor Yellow
    Write-Host "  Ejemplo: git@github.com:usuario/repo.git" -ForegroundColor DarkGray
    Write-Host ""
    $REPO_URL = Read-Host "  URL del repo"

    if ([string]::IsNullOrWhiteSpace($REPO_URL)) {
        Error "URL vacia"
        exit 1
    }

    Write-Host ""
    Success "Descargando codigo en el servidor..."

    $commands = @(
        "mkdir -p $REMOTE_PATH",
        "cd $REMOTE_PATH",
        "if [ -d '.git' ]; then git pull; else git clone $REPO_URL .; fi",
        "ls -la"
    )

    $cmdString = $commands -join " && "
    & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" $cmdString

    if ($LASTEXITCODE -eq 0) {
        Success "Codigo descargado/actualizado via Git"
        Write-Host ""
        Success "Ejecutando instalacion en el servidor..."
        Write-Host ""
        & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" "bash $REMOTE_PATH/install.sh"
    } else {
        Error "Hubo algun problema. Verifica la conexion y permisos."
    }
}

# ──── OPCION: pscp ────

elseif ($selectedMethod -eq "pscp") {
    Section "Deploy via pscp (PuTTY)"

    Write-Host ""
    Success "Creando directorios en el servidor..."
    & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ${REMOTE_PATH}/PDFs/output ${REMOTE_PATH}/PDFs/img ${REMOTE_PATH}/logs"

    $filesToUpload = @(
        "api_wondertech.py",
        "wondertech_pricelist_env.py",
        "requirements.txt",
        "ecosystem.config.js",
        ".env",
        "install.sh"
    )

    Write-Host "  Subiendo archivos..." -ForegroundColor Cyan
    Write-Host ""

    $totalFiles = $filesToUpload.Count
    $uploadedFiles = 0

    foreach ($file in $filesToUpload) {
        Progress $uploadedFiles $totalFiles
        Write-Host "  $\ " -ForegroundColor DarkGray -NoNewline
        Write-Host $file -ForegroundColor White
        & $PSCP -batch -i $SSH_KEY $file "$REMOTE_USER@${REMOTE_HOST}:${REMOTE_PATH}/"
        $uploadedFiles++
    }

    FinishProgress

    # Subir imagenes si existen
    if (Test-Path "PDFs\img") {
        Write-Host "  📁 PDFs\img\" -ForegroundColor Cyan
        & $PSCP -batch -i $SSH_KEY -r "PDFs\img\*" "$REMOTE_USER@${REMOTE_HOST}:${REMOTE_PATH}/PDFs/img/"
    }

    Success "Todos los archivos subidos exitosamente"
    Write-Host ""
    Success "Ejecutando instalacion en el servidor..."
    Write-Host ""
    & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" "bash $REMOTE_PATH/install.sh"
}

# ──── OPCION: Solo configurar ────

elseif ($selectedMethod -eq "configurar") {
    Write-Host ""
    Warning "Saltando subida de archivos"
    Write-Host ""
    Info "Conecta al servidor con:"
    Write-Host "  plink -i `"$SSH_KEY`" $REMOTE_USER@$REMOTE_HOST" -ForegroundColor Cyan
    Write-Host ""
    Info "Luego sigue los pasos en DEPLOYMENT_SERVER.md"
    exit 0
}

# ──── Final ────

Header "Deploy completado!"

Write-Host "  📋 Lo que sigue:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ┌─ 1. Verificar que PM2 esta corriendo:" -ForegroundColor DarkCyan
Write-Host "  │   pm2 status" -ForegroundColor Cyan
Write-Host "  │   pm2 logs WEBHOOK_PRICELIST" -ForegroundColor Cyan
Write-Host "  │" -ForegroundColor DarkCyan
Write-Host "  ├─ 2. Probar que responde:" -ForegroundColor DarkCyan
Write-Host "  │   curl http://localhost:$PORT/" -ForegroundColor Cyan
Write-Host "  │" -ForegroundColor DarkCyan
Write-Host "  ├─ 3. Enviar al admin para configurar nginx:" -ForegroundColor DarkCyan
Write-Host "  │   Revisar: ADMIN_REQUEST_TEMPLATE.md" -ForegroundColor Cyan
Write-Host "  │" -ForegroundColor DarkCyan
Write-Host "  └─ 4. Despues de configurar nginx, probar:" -ForegroundColor DarkCyan
Write-Host "      curl https://TU_DOMINIO/pricelist/" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ─────────────────────────────────────────────────" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  📚 Documentacion:" -ForegroundColor Yellow
Write-Host "  ┌─ Guia completa:        DEPLOYMENT_SERVER.md" -ForegroundColor White
Write-Host "  ├─ Resumen rapido:       README_DEPLOY.md" -ForegroundColor White
Write-Host "  ├─ Template para admin:  ADMIN_REQUEST_TEMPLATE.md" -ForegroundColor White
Write-Host "  └─ Deploy sin sudo:      DEPLOY_NO_SUDO.md" -ForegroundColor White
Write-Host ""
