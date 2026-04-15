# ============================================
# Deploy Script - Wondertech PriceList
# Ejecutar desde PowerShell
# ============================================

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  WONDERTECH - Deploy a Servidor" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Configuración
$LOCAL_PATH = "c:\Users\CristianRuiz\OneDrive - WONDERTECH 365\Documentos\Python Projects\lista de precios"
$REMOTE_USER = "cristianwonder"
$REMOTE_HOST = "ubuntu-s-1vcpu-1gb-sfo3-01"
$REMOTE_PATH = "/var/www/webhooks"

# Cambiar al directorio local
Set-Location -Path $LOCAL_PATH
Write-Host "📁 Directorio local: $LOCAL_PATH" -ForegroundColor Green
Write-Host ""

# Paso 1: Verificar que los archivos existen
Write-Host "🔍 Verificando archivos locales..." -ForegroundColor Yellow

$requiredFiles = @(
    "api_wondertech.py",
    "wondertech_pricelist_env.py",
    "requirements.txt",
    "ecosystem.config.js"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file - NO ENCONTRADO" -ForegroundColor Red
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "❌ Faltan archivos necesarios: $($missingFiles -join ', ')" -ForegroundColor Red
    Write-Host "   Asegúrate de estar en el directorio correcto del proyecto." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "✅ Todos los archivos necesarios están presentes" -ForegroundColor Green
Write-Host ""

# Paso 2: Elegir método de deploy
Write-Host "Selecciona el método de deploy:" -ForegroundColor Cyan
Write-Host "  1) rsync (recomendado - solo archivos modificados)" -ForegroundColor White
Write-Host "  2) scp (sube todo)" -ForegroundColor White
Write-Host "  3) Solo configurar (archivos ya subidos)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Opción (1/2/3)"

if ($choice -eq "3") {
    Write-Host ""
    Write-Host "⏭️ Saltando subida de archivos..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Conecta al servidor y sigue la guía:" -ForegroundColor Cyan
    Write-Host "  ssh $REMOTE_USER@$REMOTE_HOST" -ForegroundColor White
    Write-Host "  cd $REMOTE_PATH" -ForegroundColor White
    Write-Host ""
    Write-Host "Luego sigue los pasos en DEPLOYMENT_SERVER.md" -ForegroundColor Yellow
    exit 0
}

# Paso 3: Subir archivos
Write-Host ""
Write-Host "📦 Subiendo archivos al servidor..." -ForegroundColor Yellow
Write-Host "   Remoto: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH" -ForegroundColor White
Write-Host ""

if ($choice -eq "1") {
    # rsync
    Write-Host "Usando rsync..." -ForegroundColor Cyan
    Write-Host ""
    
    $rsyncArgs = @(
        "-avz",
        "--exclude", ".git",
        "--exclude", "__pycache__",
        "--exclude", "*.pyc",
        "--exclude", "venv",
        "--exclude", ".env",
        "--exclude", "PDFs/output/*",
        "--exclude", "logs/*",
        "./",
        "$REMOTE_USER@$REMOTE_HOST`:$REMOTE_PATH/"
    )
    
    try {
        rsync @rsyncArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Archivos subidos exitosamente con rsync" -ForegroundColor Green
        } else {
            throw "rsync failed"
        }
    } catch {
        Write-Host ""
        Write-Host "❌ rsync no está disponible en tu sistema" -ForegroundColor Red
        Write-Host "   Instala Git Bash o usa la opción 2 (scp)" -ForegroundColor Yellow
        exit 1
    }
} elseif ($choice -eq "2") {
    # scp
    Write-Host "Usando scp..." -ForegroundColor Cyan
    Write-Host ""
    
    # Archivos individuales primero
    $filesToUpload = @(
        "api_wondertech.py",
        "wondertech_pricelist_env.py",
        "requirements.txt",
        "ecosystem.config.js"
    )
    
    foreach ($file in $filesToUpload) {
        Write-Host "  📤 Subiendo $file..."
        scp $file "$REMOTE_USER@$REMOTE_HOST`:$REMOTE_PATH/"
    }
    
    # Crear directorios en el servidor
    Write-Host "  📁 Creando directorios..."
    ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH/{PDFs/output,PDFs/img,logs}"
    
    # Subir imágenes si existen
    if (Test-Path "PDFs\img") {
        Write-Host "  🖼️ Subiendo imágenes..."
        scp "PDFs\img\*" "$REMOTE_USER@$REMOTE_HOST`:$REMOTE_PATH/PDFs/img/"
    }
    
    Write-Host ""
    Write-Host "✅ Archivos subidos exitosamente con scp" -ForegroundColor Green
} else {
    Write-Host "❌ Opción no válida" -ForegroundColor Red
    exit 1
}

# Paso 4: Instrucciones siguientes
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  ✅ Deploy de archivos completado!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 Próximos pasos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Conecta al servidor:" -ForegroundColor White
Write-Host "   ssh $REMOTE_USER@$REMOTE_HOST" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Ir al directorio:" -ForegroundColor White
Write-Host "   cd $REMOTE_PATH" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Crear archivo .env:" -ForegroundColor White
Write-Host "   nano .env" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Configurar Python:" -ForegroundColor White
Write-Host "   python3 -m venv venv" -ForegroundColor Cyan
Write-Host "   source venv/bin/activate" -ForegroundColor Cyan
Write-Host "   pip install -r requirements.txt" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Iniciar con PM2:" -ForegroundColor White
Write-Host "   pm2 start ecosystem.config.js" -ForegroundColor Cyan
Write-Host "   pm2 save" -ForegroundColor Cyan
Write-Host ""
Write-Host "📖 Guía completa disponible en: DEPLOYMENT_SERVER.md" -ForegroundColor Yellow
Write-Host ""
