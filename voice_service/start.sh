#!/bin/bash
set -ex  # -e: exit on error, -x: print commands as they execute

# Create a marker file to prove this script is running
touch /tmp/startup-script-executed

echo "=== Starting Voice Service ==="

# Start Ollama in background
echo "Starting Ollama service..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
sleep 5

# Pull model in background (don't block server startup)
echo "Downloading Ollama model in background..."
(ollama pull qwen2.5:0.5b-instruct && echo "Model download complete") > /tmp/model-download.log 2>&1 &

# Start FastAPI server immediately
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8008}
