FROM python:3.11-slim

# Install system dependencies: nodejs, npm, git, curl, build tools, postgres libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    nodejs \
    npm \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Pre-install common Python packages used by skills (finance, sql, etc.)
RUN pip install --no-cache-dir \
    psycopg2-binary \
    pyodbc \
    python-dotenv \
    requests

WORKDIR /workspace/skills

# Keep container running so docker exec can be used
CMD ["sleep", "infinity"]
