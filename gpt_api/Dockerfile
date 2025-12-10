# TELEGLAS GPT API Dockerfile
# Multi-stage build for production deployment

# Use Python 3.9 slim image
FROM python:3.9-slim

# Set metadata
LABEL maintainer="TELEGLAS Team"
LABEL description="TELEGLAS GPT API - Market data API for GPT Actions"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r gptapi && useradd -r -g gptapi gptapi

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs \
    && chown -R gptapi:gptapi /app

# Switch to non-root user
USER gptapi

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "gpt_api_main.py"]

# Build arguments for customization
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Add build labels
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="teleglas-gpt-api" \
      org.label-schema.description="TELEGLAS GPT API" \
      org.label-schema.url="https://github.com/rcz87/TELEGLAS" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/rcz87/TELEGLAS.git" \
      org.label-schema.vendor="TELEGLAS" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"
