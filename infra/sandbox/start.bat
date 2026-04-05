@echo off
chcp 65001 >nul
echo ===================================
echo  Finance PostgreSQL Sandbox 启动脚本
echo ===================================
echo.

echo [1/3] 启动 PostgreSQL 容器...
docker-compose up -d
if %errorlevel% neq 0 (
    echo 错误: docker-compose 启动失败，请确认 Docker Desktop 已运行。
    pause
    exit /b 1
)

echo.
echo [2/3] 等待数据库就绪（最多 30 秒）...
set /a count=0
:wait_loop
docker exec finance-postgres pg_isready -U postgres -d cost_allocation >nul 2>&1
if %errorlevel% equ 0 goto ready
set /a count+=1
if %count% gtr 30 (
    echo 超时: 数据库未在 30 秒内就绪，请检查日志: docker logs finance-postgres
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_loop

:ready
echo 数据库已就绪。

echo.
echo [3/3] 当前运行状态:
docker-compose ps

echo.
echo ===================================
echo 启动完成！
echo ===================================
echo.
echo 接下来请执行以下步骤:
echo   1. 构建 Agent Sandbox 镜像:
echo      cd D:\learn-claude-code-my ^&^& docker build -t deep-agent-sandbox:latest -f infra/sandbox/Dockerfile .
echo   2. 在 .env 中设置 AGENT_SANDBOX=docker
echo   3. 启动后端服务
echo.
pause
