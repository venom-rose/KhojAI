# ==============================================================================
# KHOJAI Backend - Production Dockerfile (FastAPI + Python 3.11/3.14)
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build dependencies for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

# Runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root system user for security
RUN groupadd -r khojai && useradd -r -g khojai -d /app -s /sbin/nologin khojai

# Create media directory with appropriate permissions
RUN mkdir -p /app/media/documents && chown -R khojai:khojai /app

# Copy application source
COPY backend /app/backend
COPY alembic.ini /app/alembic.ini
RUN chown -R khojai:khojai /app

USER khojai

EXPOSE 8000

ENV PYTHONPATH="/app"
ENV APP_ENV="production"
ENV DEBUG="False"
ENV HOST="0.0.0.0"
ENV PORT="8000"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
