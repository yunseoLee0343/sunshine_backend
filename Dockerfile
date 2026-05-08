# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# --- system hygiene --------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# --- dependencies ----------------------------------------------------------
COPY pyproject.toml ./
# Install runtime deps only (no [dev] extras in the production image)
RUN pip install --no-cache-dir .

# --- application source ----------------------------------------------------
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY tests/ ./tests/

# --- non-root user ---------------------------------------------------------
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /home/appuser appuser && \
    chown -R appuser:appgroup /app

USER appuser
ENV HOME=/home/appuser

EXPOSE 8000

# exec-form CMD — uvicorn runs as PID 1 and receives SIGTERM cleanly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
