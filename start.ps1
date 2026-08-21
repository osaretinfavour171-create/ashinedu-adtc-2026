# PidginPharma - PowerShell startup script
# Starts all services and opens the REPL.
#
# Usage: powershell -ExecutionPolicy Bypass -File start.ps1
#   or:  .\start.ps1

$ErrorActionPreference = "Stop"

$HERE = Split-Path -Parent $MyInvocation.MyCommand.Path
$TOOLS = Join-Path $HERE "tools"
$MODELS = Join-Path $HERE "model"
$DATA = Join-Path $HERE "app\data"
$LLAMA_BIN = Join-Path $TOOLS "llamacpp\llama-server.exe"
$DOCREADER_BIN = Join-Path $TOOLS "docreader.exe"
$DR_PORT = 8765
$LLM_PORT = 8080

# Helper: wait for HTTP health endpoint
function Wait-ForService {
    param([string]$Url, [int]$MaxSeconds = 15)
    for ($i = 0; $i -lt $MaxSeconds; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) { return $true }
        } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

# Helper: check if a port is in use
function Test-Port {
    param([int]$Port)
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "  PidginPharma Starting..." -ForegroundColor Cyan
Write-Host ""

# --- 1. DocReader ---
if (-not (Test-Path $DOCREADER_BIN)) {
    Write-Host "  ERROR: docreader.exe not found at $DOCREADER_BIN" -ForegroundColor Red
    Write-Host "  Please ask your ICT support person to reinstall PidginPharma." -ForegroundColor Yellow
    Write-Host "  If this is an emergency, please refer the patient to hospital." -ForegroundColor Red
    exit 1
}

if (Test-Port -Port $DR_PORT) {
    Write-Host "  [OK] Data server already running." -ForegroundColor Green
} else {
    Write-Host "  Starting the data server..."
    # Quote the data path to handle spaces in folder names
    $drArgs = "-addr 127.0.0.1:$DR_PORT -data `"$DATA`""
    Start-Process -FilePath $DOCREADER_BIN -ArgumentList $drArgs -WindowStyle Hidden -RedirectStandardOutput "$TOOLS\docreader.log" -RedirectStandardError "$TOOLS\docreader_err.log"
    
    if (Wait-ForService -Url "http://127.0.0.1:$DR_PORT/health" -MaxSeconds 15) {
        Write-Host "  [OK] Data server is ready." -ForegroundColor Green
    } else {
        Write-Host "  ERROR: Data server failed to start." -ForegroundColor Red
        if (Test-Path "$TOOLS\docreader_err.log") {
            Get-Content "$TOOLS\docreader_err.log" | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
        if (Test-Path "$TOOLS\docreader.log") {
            Get-Content "$TOOLS\docreader.log" | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
        exit 1
    }
}

# --- 2. Model server ---
function Pick-Model {
    $primary = Join-Path $MODELS "medgemma-1.5-4b-it-Q8_0.gguf"
    $fallback = Join-Path $MODELS "qwen2.5-1.5b-instruct-q8_0.gguf"
    if (Test-Path $primary) { return "medgemma-1.5-4b-it-Q8_0.gguf" }
    if (Test-Path $fallback) { return "qwen2.5-1.5b-instruct-q8_0.gguf" }
    return $null
}

if (-not (Test-Path $LLAMA_BIN)) {
    Write-Host "  WARNING: llama-server.exe not found. General questions won't work." -ForegroundColor Yellow
    Write-Host "  Drug interaction lookups still work." -ForegroundColor DarkGray
} elseif (Test-Port -Port $LLM_PORT) {
    Write-Host "  [OK] Model server already running." -ForegroundColor Green
} else {
    $model = Pick-Model
    if ($null -eq $model) {
        Write-Host "  WARNING: No clinical model found. Run download_model.sh first." -ForegroundColor Yellow
        Write-Host "  Drug interaction lookups still work." -ForegroundColor DarkGray
    } else {
        $modelPath = Join-Path $MODELS $model
        Write-Host "  Loading the clinical brain (this may take a minute)..."
        # Quote model path to handle spaces
        $llmArgs = "-m `"$modelPath`" --host 127.0.0.1 --port $LLM_PORT -c 2048 --threads 4 --no-webui"
        Start-Process -FilePath $LLAMA_BIN -ArgumentList $llmArgs -WindowStyle Hidden -RedirectStandardOutput "$TOOLS\llama.log" -RedirectStandardError "$TOOLS\llama_err.log"
        
        if (Wait-ForService -Url "http://127.0.0.1:$LLM_PORT/health" -MaxSeconds 120) {
            Write-Host "  [OK] Clinical brain is ready." -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Model server took too long. Drug lookups still work." -ForegroundColor Yellow
        }
    }
}

# --- 3. Launch REPL ---
Write-Host ""
Write-Host "  All systems are ready." -ForegroundColor Green
Write-Host ""

Set-Location (Join-Path $HERE "app")
python orchestrator.py @args
