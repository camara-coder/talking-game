#!/usr/bin/env pwsh
# Script to start the Voice Game with Web Frontend

Write-Host "🎮 Starting Voice Conversational Kids Game (Web Version)..." -ForegroundColor Cyan
Write-Host ""

# Set error action
$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

# Check if Ollama is running
Write-Host "1. Checking Ollama..." -ForegroundColor Yellow
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://127.0.0.1:11434" -Method Get -TimeoutSec 5
    if ($ollamaResponse -match "Ollama is running") {
        Write-Host "   ✓ Ollama is running" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Ollama may not be running properly" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Ollama is not running" -ForegroundColor Red
    Write-Host "   Starting Ollama..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Write-Host "   Waiting for Ollama to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

# Check if Ollama model is available
Write-Host "2. Checking Ollama model..." -ForegroundColor Yellow
try {
    $models = ollama list
    if ($models -match "qwen2.5:0.5b-instruct") {
        Write-Host "   ✓ Model qwen2.5:0.5b-instruct is available" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Model not found. Pulling qwen2.5:0.5b-instruct..." -ForegroundColor Yellow
        ollama pull qwen2.5:0.5b-instruct
    }
} catch {
    Write-Host "   ⚠ Could not check models" -ForegroundColor Yellow
}

# Check eSpeak NG
Write-Host "3. Checking eSpeak NG..." -ForegroundColor Yellow
$espeakPath = "C:\Program Files\eSpeak NG\espeak-ng.exe"
if (Test-Path $espeakPath) {
    Write-Host "   ✓ eSpeak NG is installed" -ForegroundColor Green
} else {
    Write-Host "   ✗ eSpeak NG is not installed" -ForegroundColor Red
    Write-Host "   Please install eSpeak NG from https://github.com/espeak-ng/espeak-ng/releases" -ForegroundColor Yellow
}

# Start Voice Service (Python backend)
Write-Host "4. Starting Voice Service (Python backend)..." -ForegroundColor Yellow
$voiceServicePath = Join-Path $RootDir "voice_service"
$venvPath = Join-Path $voiceServicePath ".venv\Scripts\Activate.ps1"

if (Test-Path $venvPath) {
    Write-Host "   Starting backend on http://127.0.0.1:8008..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$voiceServicePath'; & '$venvPath'; uvicorn app.main:app --host 127.0.0.1 --port 8008"
    ) -WindowStyle Normal
    Start-Sleep -Seconds 3
} else {
    Write-Host "   ✗ Python virtual environment not found" -ForegroundColor Red
    Write-Host "   Please run: cd voice_service && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Start Web Frontend (React/Vite)
Write-Host "5. Starting Web Frontend (React)..." -ForegroundColor Yellow
$webClientPath = Join-Path $RootDir "web-client"

if (Test-Path (Join-Path $webClientPath "package.json")) {
    Write-Host "   Starting frontend on http://localhost:5173..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$webClientPath'; npm run dev"
    ) -WindowStyle Normal
} else {
    Write-Host "   ✗ Web client not found" -ForegroundColor Red
    Write-Host "   Please ensure web-client folder exists and npm install has been run" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🎉 Services are starting!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Web Frontend:    http://localhost:5173" -ForegroundColor Cyan
Write-Host "🔧 Voice Service:   http://127.0.0.1:8008" -ForegroundColor Cyan
Write-Host "🧠 Ollama:          http://127.0.0.1:11434" -ForegroundColor Cyan
Write-Host ""
Write-Host "Opening browser in 5 seconds..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Start-Sleep -Seconds 5
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Press Ctrl+C to stop this script (services will continue running)" -ForegroundColor Gray
Write-Host "To stop services, close the PowerShell windows that were opened" -ForegroundColor Gray
Write-Host ""

# Keep script running
while ($true) {
    Start-Sleep -Seconds 1
}
