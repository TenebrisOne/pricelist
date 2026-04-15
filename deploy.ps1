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
$PORT = 5008

# ──── Funciones visuales ────

function Get-Timestamp {
    return Get-Date -Format "HH:mm:ss"
}

function Log-Info($msg) {
    Write-Host "[$(Get-Timestamp)] " -ForegroundColor DarkGray -NoNewline
    Write-Host "INFO  " -ForegroundColor Cyan -NoNewline
    Write-Host "│ $msg" -ForegroundColor White
}

function Log-Success($msg) {
    Write-Host "[$(Get-Timestamp)] " -ForegroundColor DarkGray -NoNewline
    Write-Host "OK    " -ForegroundColor Green -NoNewline
    Write-Host "│ $msg" -ForegroundColor Green
}

function Log-Warn($msg) {
    Write-Host "[$(Get-Timestamp)] " -ForegroundColor DarkGray -NoNewline
    Write-Host "WARN  " -ForegroundColor Yellow -NoNewline
    Write-Host "│ $msg" -ForegroundColor Yellow
}

function Log-Error($msg) {
    Write-Host "[$(Get-Timestamp)] " -ForegroundColor DarkGray -NoNewline
    Write-Host "ERROR " -ForegroundColor Red -NoNewline
    Write-Host "│ $msg" -ForegroundColor Red
}

function Log-Step($step, $total, $msg) {
    $stepStr = "[$step/$total]"
    Write-Host "[$(Get-Timestamp)] " -ForegroundColor DarkGray -NoNewline
    Write-Host "STEP  " -ForegroundColor Magenta -NoNewline
    Write-Host "│ $stepStr " -ForegroundColor Magenta -NoNewline
    Write-Host $msg -ForegroundColor White
}

function Header($title) {
    Write-Host ""
    Write-Host "┌─────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host "│" -ForegroundColor Cyan -NoNewline
    Write-Host "  WONDERTECH - $title" -ForegroundColor White -NoNewline
    $spaces = 54 - $title.Length
    Write-Host (" " * $spaces) + "│" -ForegroundColor Cyan
    Write-Host "│" -ForegroundColor Cyan -NoNewline
    Write-Host "  $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')" -ForegroundColor DarkGray -NoNewline
    Write-Host (" " * 33) + "│" -ForegroundColor Cyan
    Write-Host "└─────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
    Write-Host ""
}

function Section($title) {
    Write-Host ""
    Write-Host "╭──────────────────────────────────────────────────────────╮" -ForegroundColor DarkCyan
    Write-Host "│" -ForegroundColor DarkCyan -NoNewline
    Write-Host " $title" -ForegroundColor Cyan -NoNewline
    $spaces = 57 - $title.Length
    Write-Host (" " * $spaces) + "│" -ForegroundColor DarkCyan
    Write-Host "╰──────────────────────────────────────────────────────────╯" -ForegroundColor DarkCyan
}

function Divider {
    Write-Host "  ─────────────────────────────────────────────────────" -ForegroundColor DarkGray
}

function Progress($current, $total, $file) {
    $pct = [math]::Round(($current / $total) * 100)
    $filled = [math]::Round($pct / 5)
    $empty = 20 - $filled
    $bar = "█" * $filled + "░" * $empty
    Write-Host "`r  " -NoNewline
    Write-Host "[$bar]" -ForegroundColor Cyan -NoNewline
    Write-Host " $pct%" -ForegroundColor White -NoNewline
    Write-Host "  → " -ForegroundColor DarkGray -NoNewline
    Write-Host "$file" -ForegroundColor White -NoNewline
}

function FinishProgress {
    Write-Host ""
}

function Separator {
    Write-Host ""
    Write-Host "  " -NoNewline
    Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor DarkGray
    Write-Host ""
}

function SummaryTable($items) {
    Write-Host "  ┌─────────────────────────────────────────────────────┐" -ForegroundColor DarkCyan
    foreach ($item in $items) {
        $key = $item.Key
        $val = $item.Value
        $keyPad = 20 - $key.Length
        $valPad = 31 - $val.Length
        if ($valPad -lt 0) { $valPad = 0; $val = $val.Substring(0, 31) }
        Write-Host "  │ " -ForegroundColor DarkCyan -NoNewline
        Write-Host $key -ForegroundColor Cyan -NoNewline
        Write-Host (" " * $keyPad + "│ ") -ForegroundColor DarkCyan -NoNewline
        Write-Host $val -ForegroundColor White -NoNewline
        Write-Host (" " * $valPad + "│") -ForegroundColor DarkCyan
    }
    Write-Host "  └─────────────────────────────────────────────────────┘" -ForegroundColor DarkCyan
}

# ──── Header ────

Header "Deploy v2.0"

Log-Info "Directorio : $PROJECT_NAME"
Log-Info "Servidor   : $REMOTE_USER@$REMOTE_HOST"
Log-Info "Remoto     : $REMOTE_PATH"
Log-Info "Puerto     : $PORT"
Write-Host ""

# ──── Verificar herramientas ────

Section "  Verificando herramientas"

$hasGit = Get-Command git -ErrorAction SilentlyContinue
$hasPlink = Test-Path $PLINK
$hasPscp = Test-Path $PSCP
$hasKey = Test-Path $SSH_KEY

if ($hasGit) { Log-Success "Git instalado" } else { Log-Error "Git no encontrado" }
if ($hasPlink) { Log-Success "PuTTY plink disponible" } else { Log-Warn "plink no encontrado" }
if ($hasPscp) { Log-Success "PuTTY pscp disponible" } else { Log-Warn "pscp no encontrado" }
if ($hasKey) { Log-Success "SSH key encontrada" } else { Log-Error "SSH key NO encontrada" }

if (-not $hasKey) {
    Log-Error "No se encontro la key SSH. Verifica: $SSH_KEY"
    exit 1
}

# ──── Verificar archivos ────

Section "  Verificando archivos del proyecto"

$requiredFiles = @(
    "api_wondertech.py",
    "wondertech_pricelist_env.py",
    "requirements.txt",
    "ecosystem.config.js",
    ".env",
    "install.sh"
)

$missingFiles = @()
$i = 0

foreach ($file in $requiredFiles) {
    $i++
    if (Test-Path $file) {
        Log-Success "$file  ($([math]::Round((Get-Item $file).Length / 1KB, 1)) KB)"
    } else {
        Log-Error "$file - FALTA"
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Separator
    Log-Error "Faltan $($missingFiles.Count) archivo(s): $($missingFiles -join ', ')"
    exit 1
}

# ──── Elegir metodo de deploy ────

Section "  Selecciona el metodo de deploy"

$options = @()
$optionNum = 1

if ($hasGit) {
    Write-Host "  [$optionNum] " -ForegroundColor Cyan -NoNewline
    Write-Host "Git clone/pull en el servidor" -ForegroundColor White
    $options += "git"
    $optionNum++
}

if ($hasPscp -and $hasPlink) {
    Write-Host "  [$optionNum] " -ForegroundColor Cyan -NoNewline
    Write-Host "pscp - Subir archivos con PuTTY" -ForegroundColor White
    $options += "pscp"
    $optionNum++
}

Write-Host "  [$optionNum] " -ForegroundColor Cyan -NoNewline
Write-Host "Solo configurar (archivos ya subidos)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "  Opcion (1-$($options.Count))"
$choiceNum = [int]$choice - 1

if ($choiceNum -lt 0 -or $choiceNum -ge $options.Count) {
    Log-Error "Opcion no valida"
    exit 1
}

$selectedMethod = $options[$choiceNum]

# ──── OPCION: Git ────

if ($selectedMethod -eq "git") {
    Section "  Deploy via Git"

    Write-Host "  Ingresa la URL de tu repositorio GitHub:" -ForegroundColor Yellow
    Write-Host "  Ejemplo: git@github.com:usuario/repo.git" -ForegroundColor DarkGray
    Write-Host ""
    $REPO_URL = Read-Host "  URL del repo"

    if ([string]::IsNullOrWhiteSpace($REPO_URL)) {
        Log-Error "URL vacia"
        exit 1
    }

    Log-Info "Clonando/actualizando codigo en el servidor..."

    $commands = @(
        "mkdir -p $REMOTE_PATH",
        "cd $REMOTE_PATH",
        "if [ -d '.git' ]; then git pull; else git clone $REPO_URL .; fi",
        "ls -la"
    )

    $cmdString = $commands -join " && "
    & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" $cmdString

    if ($LASTEXITCODE -eq 0) {
        Log-Success "Codigo descargado/actualizado via Git"
        Log-Info "Ejecutando instalacion en el servidor..."
        Write-Host ""
        & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" "bash $REMOTE_PATH/install.sh"
    } else {
        Log-Error "Hubo algun problema. Verifica la conexion y permisos."
    }
}

# ──── OPCION: pscp ────

elseif ($selectedMethod -eq "pscp") {
    Section "  Deploy via pscp (PuTTY)"

    Log-Info "Creando directorios en el servidor..."
    & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ${REMOTE_PATH}/PDFs/output ${REMOTE_PATH}/PDFs/img ${REMOTE_PATH}/logs"
    Log-Success "Directorios remotos creados"

    $filesToUpload = @(
        "api_wondertech.py",
        "wondertech_pricelist_env.py",
        "requirements.txt",
        "ecosystem.config.js",
        ".env",
        "install.sh"
    )

    Write-Host ""
    Log-Info "Subiendo archivos..."
    Write-Host ""

    $totalFiles = $filesToUpload.Count
    $uploadedFiles = 0

    foreach ($file in $filesToUpload) {
        Progress $uploadedFiles $totalFiles $file
        & $PSCP -batch -i $SSH_KEY $file "$REMOTE_USER@${REMOTE_HOST}:${REMOTE_PATH}/" >$null 2>&1
        $uploadedFiles++
    }

    FinishProgress
    Log-Success "$($filesToUpload.Count)/$($filesToUpload.Count) archivos subidos"

    # Subir imagenes si existen
    if (Test-Path "PDFs\img") {
        Log-Info "Subiendo imagenes..."
        & $PSCP -batch -i $SSH_KEY -r "PDFs\img\*" "$REMOTE_USER@${REMOTE_HOST}:${REMOTE_PATH}/PDFs/img/" >$null 2>&1
        $imgCount = (Get-ChildItem "PDFs\img").Count
        Log-Success "$imgCount imagen(es) subida(s)"
    }

    # ──── Resumen de subida ────
    Separator

    $uploadSummary = @(
        @{Key = "Archivos subidos"; Value = "$($filesToUpload.Count) archivos"},
        @{Key = "Imagenes"; Value = "$(if ($imgCount) { $imgCount } else { 0 }) archivos"},
        @{Key = "Destino"; Value = "$REMOTE_PATH"},
        @{Key = "Metodo"; Value = "pscp (PuTTY)"}
    )
    SummaryTable $uploadSummary
    Separator

    Log-Info "Ejecutando instalacion en el servidor..."
    Write-Host ""
    & $PLINK -batch -i $SSH_KEY "$REMOTE_USER@$REMOTE_HOST" "bash $REMOTE_PATH/install.sh"
}

# ──── OPCION: Solo configurar ────

elseif ($selectedMethod -eq "configurar") {
    Log-Warn "Saltando subida de archivos"
    Log-Info "Conecta al servidor con: plink -i `"$SSH_KEY`" $REMOTE_USER@$REMOTE_HOST"
    Log-Info "Luego sigue los pasos en DEPLOYMENT_SERVER.md"
    exit 0
}

# ──── Final ────

Header "Deploy completado"

Write-Host "  Lo que sigue:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ┌─ 1. Verificar PM2:" -ForegroundColor DarkCyan
Write-Host "  │   pm2 status" -ForegroundColor Cyan
Write-Host "  │   pm2 logs WEBHOOK_PRICELIST" -ForegroundColor Cyan
Write-Host "  │" -ForegroundColor DarkCyan
Write-Host "  ├─ 2. Probar endpoint local:" -ForegroundColor DarkCyan
Write-Host "  │   curl http://localhost:$PORT/" -ForegroundColor Cyan
Write-Host "  │" -ForegroundColor DarkCyan
Write-Host "  ├─ 3. Configurar nginx (admin):" -ForegroundColor DarkCyan
Write-Host "  │   Revisar: ADMIN_REQUEST_TEMPLATE.md" -ForegroundColor Cyan
Write-Host "  │" -ForegroundColor DarkCyan
Write-Host "  └─ 4. Probar con nginx:" -ForegroundColor DarkCyan
Write-Host "      curl https://TU_DOMINIO/pricelist/" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ─────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Documentacion:" -ForegroundColor Yellow
Write-Host "  ┌─ Guia completa:        DEPLOYMENT_SERVER.md" -ForegroundColor White
Write-Host "  ├─ Resumen rapido:       README_DEPLOY.md" -ForegroundColor White
Write-Host "  ├─ Template para admin:  ADMIN_REQUEST_TEMPLATE.md" -ForegroundColor White
Write-Host "  └─ Deploy sin sudo:      DEPLOY_NO_SUDO.md" -ForegroundColor White
Write-Host ""
