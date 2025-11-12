# Manus AI Clone - Multi-stage Docker Build

# Stage 1: Base
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies
FROM base as dependencies

COPY manus_ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers for web automation
RUN playwright install --with-deps chromium

# Stage 3: Application
FROM dependencies as application

# Copy application code
COPY manus_ai/ /app/manus_ai/

# Create non-root user
RUN useradd -m -u 1000 manusai && \
    chown -R manusai:manusai /app

USER manusai

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "manus_ai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
