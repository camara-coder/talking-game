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
echo "Starting Ollama service..."\n\
ollama serve &\n\
OLLAMA_PID=$!\n\
\n\
echo "Waiting for Ollama to be ready..."\n\
sleep 5\n\
\n\
echo "Pulling Ollama model..."\n\
ollama pull qwen2.5:0.5b-instruct || echo "Model pull failed, will retry on first request"\n\
\n\
echo "Starting FastAPI server..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8008}\n\
' > /app/start.sh && chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8008}/health || exit 1

# Run startup script
CMD ["/app/start.sh"]
