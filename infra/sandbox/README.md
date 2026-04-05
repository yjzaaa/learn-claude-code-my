# Sandbox 启动指南

## 快速启动

双击 `start.bat` 即可一键启动 PostgreSQL 容器，并等待数据库就绪。

## 手动启动

```powershell
docker-compose up -d
```

## 验证数据库

```powershell
docker exec finance-postgres pg_isready -U postgres -d cost_allocation
```

## 停止

```powershell
docker-compose down
```

## 下一步

回到项目根目录构建 Agent Sandbox 镜像：

```powershell
cd D:\learn-claude-code-my
docker build -t deep-agent-sandbox:latest -f infra/sandbox/Dockerfile .
```

然后在 `.env` 中设置：

```env
AGENT_SANDBOX=docker
```
