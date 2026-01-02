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

# Install Ollama manually (download binary directly)
RUN curl -fsSL https://ollama.com/download/ollama-linux-amd64.tgz -o ollama.tgz && \
    tar -xzf ollama.tgz -C /usr/local/bin && \
    rm ollama.tgz && \
    chmod +x /usr/local/bin/ollama

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

# Copy and setup startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Health check
# Server starts quickly now, model downloads in background
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8008}/health || exit 1

# Run startup script
# Using shell form to ensure proper execution
CMD /app/start.sh
