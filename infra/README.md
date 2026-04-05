# Agent Sandbox 运行指南

本文档说明如何启动 Docker 容器化环境，使 Agent 的代码执行、文件操作与数据库查询完全隔离在容器内运行，不再依赖宿主机的 Python 环境。

## 前置要求

- Windows 10/11
- Docker Desktop 已安装并启用 WSL2 后端
- 当前工作目录为项目根目录 `D:\learn-claude-code-my`

## 步骤 1：启动 Docker Desktop

确保 Docker Desktop 正在运行（系统托盘图标正常显示，无红色错误提示）。

## 步骤 2：构建 Agent Sandbox 镜像

镜像预装了 Python、Node.js、npm、uv、PostgreSQL 驱动等常用依赖。

```powershell
cd D:\learn-claude-code-my
docker build -t deep-agent-sandbox:latest -f infra/sandbox/Dockerfile .
```

构建成功后，可通过以下命令验证容器内工具版本：

```powershell
docker run --rm deep-agent-sandbox:latest python --version
docker run --rm deep-agent-sandbox:latest node --version
```

## 步骤 3：启动 PostgreSQL 数据库容器

项目已将本地 PostgreSQL 数据导出并容器化。启动后会自动加载 `cost_allocation` 数据库。

```powershell
cd D:\learn-claude-code-my\infra\sandbox
docker-compose up -d
```

验证数据库是否就绪：

```powershell
docker exec finance-postgres pg_isready -U postgres -d cost_allocation
```

 expected output: `accepting connections`

## 步骤 4：配置后端使用 Docker Sandbox

在 `.env` 文件（或系统环境变量）中设置：

```env
AGENT_SANDBOX=docker
```

如果不设置，默认值为 `local`，Agent 将回退到宿主机的 `LocalShellBackend`。

## 步骤 5：启动后端服务

使用你平时的方式启动后端（如 uvicorn / python main.py）。服务端启动后会自动检测 Docker daemon 状态：

- Docker 可用时，创建 `deep-agent-sandbox` 守护容器，文件与 Shell 操作均在其中执行。
- Docker 不可用时，自动降级到 `LocalShellBackend`，日志中会有 `falling back` 提示。

## 验证 Agent 是否在容器内运行

发送一条测试消息（如询问 finance 技能的预算分析），在服务端日志中应看到：

```
[DeepAgentRuntime] Using sandbox backend for skills_dir=...
[DeepAgentRuntime] Proxied run_sql_query to sandbox
```

如果 `run_sql_query` 成功返回数据而不是 `No module named 'psycopg2'`，说明容器化环境已正常工作。

## 常见问题

### Q: `docker build` 报错 `error during connect: open //./pipe/dockerDesktopLinuxEngine`
A: Docker Desktop 未启动。请先打开 Docker Desktop，等待其状态变为 "Engine running"。

### Q: 数据库连接失败
A: 确认 `skills/finance/.env` 中的 `DB_HOST` 为 `host.docker.internal`，且 PostgreSQL 容器已启动（`docker-compose up -d`）。

### Q: 如何停止容器
A:
```powershell
cd D:\learn-claude-code-my\infra\sandbox
docker-compose down
```

要同时删除 sandbox 守护容器：
```powershell
docker rm -f deep-agent-sandbox
```

### Q: 如何在容器内手动安装新的 Python 包
A: 进入 sandbox 容器后直接使用 pip 或 uv：
```powershell
docker exec -it deep-agent-sandbox bash
pip install <package>
```

## 目录说明

| 路径 | 说明 |
|------|------|
| `infra/sandbox/Dockerfile` | Agent Sandbox 镜像构建文件 |
| `infra/sandbox/docker-compose.yml` | PostgreSQL 容器编排配置 |
| `infra/sandbox/init_cost_allocation.sql` | finance 技能数据库初始化脚本 |
