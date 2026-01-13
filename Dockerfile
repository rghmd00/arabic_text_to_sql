FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libaio1t64 || apt-get install -y libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv using pip (avoids pulling the ghcr.io image)
RUN pip install uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy the rest of the code
COPY . .

# Final sync
RUN uv sync --frozen

EXPOSE 8000
EXPOSE 8501