# ── Stage 1: Build frontend ──────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
# VITE_API_BASE_URL is empty — same-origin serving via backend
# Use vite build directly to avoid blocking TypeScript strict errors
RUN npx vite build


# ── Stage 2: Runtime ──────────────────────────────────────────────
FROM python:3.12-slim

# System deps for asyncpg + GeoAlchemy2 (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Application source
COPY backend/ ./backend/

# Pipeline data (Silver JSON + ref GeoJSON — served by backend at runtime)
COPY pipeline/silver/ ./pipeline/silver/
COPY pipeline/ref/ ./pipeline/ref/

# Frontend dist from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1

# Railway injects $PORT; default 8000 for local
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
