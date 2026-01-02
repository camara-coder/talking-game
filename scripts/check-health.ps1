#!/usr/bin/env pwsh
# Health check script for Voice Game services

Write-Host "🏥 Voice Game Health Check" -ForegroundColor Cyan
Write-Host ""

$allHealthy = $true

# Check Ollama
Write-Host "Checking Ollama..." -ForegroundColor Yellow
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://127.0.0.1:11434" -Method Get -TimeoutSec 5
    if ($ollamaResponse -match "Ollama is running") {
        Write-Host "  ✓ Ollama is running on http://127.0.0.1:11434" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Ollama responded but with unexpected message" -ForegroundColor Yellow
        $allHealthy = $false
    }
} catch {
    Write-Host "  ✗ Ollama is not running" -ForegroundColor Red
    Write-Host "    Start with: ollama serve" -ForegroundColor Gray
    $allHealthy = $false
}

# Check Voice Service
Write-Host "Checking Voice Service..." -ForegroundColor Yellow
try {
    $voiceResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8008/health" -Method Get -TimeoutSec 5
    Write-Host "  ✓ Voice Service is running on http://127.0.0.1:8008" -ForegroundColor Green
    Write-Host "    Status: $($voiceResponse | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Voice Service is not running" -ForegroundColor Red
    Write-Host "    Start with: cd voice_service && uvicorn app.main:app" -ForegroundColor Gray
    $allHealthy = $false
}

# Check Web Frontend
Write-Host "Checking Web Frontend..." -ForegroundColor Yellow
try {
    $webResponse = Invoke-WebRequest -Uri "http://localhost:5173" -Method Get -TimeoutSec 5
    if ($webResponse.StatusCode -eq 200) {
        Write-Host "  ✓ Web Frontend is running on http://localhost:5173" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Web Frontend responded with status: $($webResponse.StatusCode)" -ForegroundColor Yellow
        $allHealthy = $false
    }
} catch {
    Write-Host "  ✗ Web Frontend is not running" -ForegroundColor Red
    Write-Host "    Start with: cd web-client && npm run dev" -ForegroundColor Gray
    $allHealthy = $false
}

# Check eSpeak NG
Write-Host "Checking eSpeak NG..." -ForegroundColor Yellow
$espeakPath = "C:\Program Files\eSpeak NG\espeak-ng.exe"
if (Test-Path $espeakPath) {
    Write-Host "  ✓ eSpeak NG is installed at $espeakPath" -ForegroundColor Green
} else {
    Write-Host "  ✗ eSpeak NG not found at $espeakPath" -ForegroundColor Red
    Write-Host "    Install from: https://github.com/espeak-ng/espeak-ng/releases" -ForegroundColor Gray
    $allHealthy = $false
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
if ($allHealthy) {
    Write-Host "✅ All services are healthy!" -ForegroundColor Green
} else {
    Write-Host "❌ Some services are not running properly" -ForegroundColor Red
    Write-Host "   Run scripts\start-web-game.ps1 to start all services" -ForegroundColor Yellow
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
