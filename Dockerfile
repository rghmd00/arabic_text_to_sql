# =============================================================
# Stages:
#   base        – system deps + uv + Python dependencies
#   backend     – FastAPI / uvicorn  (target: backend)
#   frontend    – Streamlit          (target: frontend)
# =============================================================


# ── Stage 1: base (shared) ────────────────────────────────
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y \
    curl \
    && (apt-get install -y libaio1t64 || apt-get install -y libaio1) \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Install deps first — cached as long as lockfile doesn't change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source after deps are cached
COPY . .
RUN uv sync --frozen --no-dev


# ── Stage 2: backend ──────────────────────────────────────
FROM base AS backend

RUN mkdir -p data/files

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# ── Stage 3: frontend ─────────────────────────────────────
FROM base AS frontend

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "front.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]







     
