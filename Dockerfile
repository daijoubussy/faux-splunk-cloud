# Faux Splunk Cloud - Backend API
FROM python:3.12-slim

# Install system dependencies including Docker CLI for container orchestration
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://get.docker.com | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Create data directory
RUN mkdir -p /data

# Set environment variables
ENV FSC_HOST=0.0.0.0
ENV FSC_PORT=8800
ENV FSC_DATA_DIR=/data
ENV FSC_DATABASE_URL=sqlite+aiosqlite:///data/fsc.db

# Expose API port
EXPOSE 8800

# Run the API server
CMD ["uvicorn", "faux_splunk_cloud.api.app:app", "--host", "0.0.0.0", "--port", "8800"]
