# syntax=docker/dockerfile:1
# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY pyproject.toml ./

# Install runtime deps into an isolated prefix so we can copy just that layer
RUN pip install --prefix=/install .

# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production

# Copy only the installed site-packages from the builder stage
COPY --from=builder /install /usr/local

WORKDIR /app

# Application source — no test files or dev tooling in the final image
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Non-root user for least-privilege execution
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /home/appuser appuser && \
    chown -R appuser:appgroup /app

USER appuser
ENV HOME=/home/appuser

EXPOSE 8000

# exec-form CMD — uvicorn is PID 1 and receives SIGTERM cleanly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
