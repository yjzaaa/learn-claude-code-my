# 使用 DaoCloud 镜像（国内访问更快）
FROM m.daocloud.io/docker.io/library/python:3.11-slim

# 使用国内 apt 源（清华）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# Install system dependencies: git, curl, build tools, postgres libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 配置国内 pip 源（清华）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# Install uv via pip（国内源）
RUN pip install --no-cache-dir uv

# Pre-install common Python packages used by skills (finance, sql, etc.)
RUN pip install --no-cache-dir \
    psycopg2-binary \
    pyodbc \
    python-dotenv \
    requests \
    sqlalchemy

WORKDIR /workspace/skills

# Keep container running so docker exec can be used
CMD ["sleep", "infinity"]
