# Multi-stage Dockerfile for Voice Game Backend
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    espeak-ng \
    libespeak-ng1 \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama (for LLM)
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy requirements
COPY voice_service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY voice_service/app ./app
COPY voice_service/data ./data

# Create necessary directories
RUN mkdir -p data/audio data/logs

# Expose ports
EXPOSE 8008

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Start Ollama in background and run the application
CMD ollama serve & \
    sleep 5 && \
    ollama pull qwen2.5:0.5b-instruct && \
    uvicorn app.main:app --host 0.0.0.0 --port 8008
