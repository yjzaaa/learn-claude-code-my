# 使用阿里云镜像源
FROM registry.cn-hangzhou.aliyuncs.com/python/python:3.11-slim

# 更换 APT 源为阿里云镜像
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

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

# 更换 pip 源为阿里云镜像
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# Pre-install common Python packages used by skills (finance, sql, etc.)
RUN pip install --no-cache-dir \
    psycopg2-binary \
    pyodbc \
    python-dotenv \
    requests

WORKDIR /workspace/skills

# Keep container running so docker exec can be used
CMD ["sleep", "infinity"]
