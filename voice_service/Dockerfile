# Multi-stage build for Voice Service with Ollama
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    ca-certificates \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/audio data/logs

# Expose ports
# Port 8008 for FastAPI
# Port 11434 for Ollama
EXPOSE 8008 11434

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "=== Starting Voice Service ==="\n\
\n\
# Start Ollama in background\n\
echo "Starting Ollama service..."\n\
ollama serve > /tmp/ollama.log 2>&1 &\n\
OLLAMA_PID=$!\n\
\n\
# Wait for Ollama to be ready\n\
echo "Waiting for Ollama to be ready..."\n\
sleep 5\n\
\n\
# Pull model in background (dont block server startup)\n\
echo "Downloading Ollama model in background..."\n\
(ollama pull qwen2.5:0.5b-instruct && echo "Model download complete") > /tmp/model-download.log 2>&1 &\n\
\n\
# Start FastAPI server immediately\n\
echo "Starting FastAPI server..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8008}\n\
' > /app/start.sh && chmod +x /app/start.sh

# Health check
# Server starts quickly now, model downloads in background
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8008}/health || exit 1

# Run startup script
CMD ["/app/start.sh"]
