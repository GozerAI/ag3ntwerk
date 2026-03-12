# C-Suite Ollama Setup Script for Windows
# ========================================
# This script helps set up Ollama for use with C-Suite

Write-Host "=== C-Suite Ollama Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is installed
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaPath) {
    Write-Host "Ollama not found. Please install from: https://ollama.ai" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installation steps:" -ForegroundColor Yellow
    Write-Host "1. Download Ollama from https://ollama.ai/download"
    Write-Host "2. Run the installer"
    Write-Host "3. Restart this script"
    exit 1
}

Write-Host "[OK] Ollama is installed at: $($ollamaPath.Source)" -ForegroundColor Green

# Check if Ollama is running
$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $ollamaRunning = $true
    }
} catch {
    $ollamaRunning = $false
}

if (-not $ollamaRunning) {
    Write-Host ""
    Write-Host "Ollama server is not running. Starting..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -NoNewWindow
    Start-Sleep -Seconds 3
    Write-Host "[OK] Ollama server started" -ForegroundColor Green
} else {
    Write-Host "[OK] Ollama server is already running" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Pulling Recommended Models ===" -ForegroundColor Cyan
Write-Host ""

# Define recommended models
$models = @(
    @{name="llama3.2:3b"; desc="Primary reasoning model (2GB)"},
    @{name="phi3:mini"; desc="Fast inference model (2GB)"}
)

# Optional models (larger)
$optionalModels = @(
    @{name="deepseek-coder:6.7b"; desc="Code generation (4GB)"},
    @{name="nomic-embed-text"; desc="Embeddings (500MB)"}
)

foreach ($model in $models) {
    Write-Host "Pulling $($model.name) - $($model.desc)" -ForegroundColor Yellow
    & ollama pull $model.name
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $($model.name) ready" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Failed to pull $($model.name)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "=== Optional Models ===" -ForegroundColor Cyan
Write-Host "The following models are optional but recommended for specific tasks:"
Write-Host ""

foreach ($model in $optionalModels) {
    Write-Host "  $($model.name) - $($model.desc)" -ForegroundColor Gray
}

Write-Host ""
$pullOptional = Read-Host "Would you like to pull optional models? (y/N)"

if ($pullOptional -eq "y" -or $pullOptional -eq "Y") {
    foreach ($model in $optionalModels) {
        Write-Host "Pulling $($model.name)..." -ForegroundColor Yellow
        & ollama pull $model.name
        Write-Host ""
    }
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Available models:" -ForegroundColor Cyan
& ollama list

Write-Host ""
Write-Host "You can now use C-Suite with Ollama!" -ForegroundColor Green
Write-Host ""
Write-Host "Quick test:" -ForegroundColor Yellow
Write-Host "  csuite status"
Write-Host "  csuite models"
Write-Host ""
