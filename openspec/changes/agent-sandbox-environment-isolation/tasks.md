## 1. 实现 DockerSandboxBackend

- [ ] 1.1 新建 `backend/infrastructure/runtime/services/docker_sandbox_backend.py`
- [ ] 1.2 实现 `DockerSandboxBackend` 继承 `BaseSandbox`
- [ ] 1.3 实现 `_ensure_container_running()`：检测容器状态，未启动则 `docker run -d`
- [ ] 1.4 实现 `execute()`：通过 `docker exec` 执行命令，处理 timeout、exit code、stdout/stderr 合并
- [ ] 1.5 实现 `id` property 返回容器名
- [ ] 1.6 实现 Docker daemon 未启动时的自动降级逻辑（回退到 `LocalShellBackend`）
- [ ] 1.7 添加 `__all__` 与类型注解
- [ ] 1.8 运行 `python -m py_compile` 验证语法

## 2. 构建 Sandbox 镜像

- [ ] 2.1 新建 `infra/sandbox/Dockerfile`
- [ ] 2.2 基础镜像选用 `python:3.11-slim`
- [ ] 2.3 Dockerfile 中安装 `git curl build-essential nodejs npm`
- [ ] 2.4 Dockerfile 中安装 `uv`
- [ ] 2.5 设置 `WORKDIR /workspace/skills`
- [ ] 2.6 构建镜像并打标签：`docker build -t deep-agent-sandbox:latest -f infra/sandbox/Dockerfile .`
- [ ] 2.7 验证镜像构建成功，容器内 `python`、`node`、`npm`、`uv` 均可调用

## 3. Deep Runtime 集成 Backend 切换

- [ ] 3.1 修改 `backend/infrastructure/runtime/deep.py`，导入 `DockerSandboxBackend`
- [ ] 3.2 读取 `AGENT_SANDBOX` 环境变量（默认 `local`）
- [ ] 3.3 当 `AGENT_SANDBOX=docker` 时，实例化 `DockerSandboxBackend(root_dir=str(skills_dir), ...)`
- [ ] 3.4 当 `AGENT_SANDBOX=local` 或 Docker 不可用时，继续使用 `LocalShellBackend`
- [ ] 3.5 保留 `virtual_mode=True` 与 skills 目录挂载逻辑
- [ ] 3.6 移除（或缩减）系统提示词中关于 Windows 环境路径的冗长约束说明

## 4. 路径与 Volume 适配

- [ ] 4.1 确认 Docker Desktop WSL2 backend 能将 `D:\learn-claude-code-my\skills` 正确挂载到 `/workspace/skills`
- [ ] 4.2 验证容器内 `read_file("/finance/SKILL.md")` 可正常读取
- [ ] 4.3 验证容器内 `write_file` 写入的文件在宿主磁盘可见
- [ ] 4.4 验证 `glob("**/*.py", path="/finance")` 能在容器内正确返回结果

## 5. 环境变量透传

- [ ] 5.1 定义默认 `env_allowlist`：`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`DB_*`、`MODEL_ID`、`ANTHROPIC_BASE_URL`
- [ ] 5.2 实现 `execute()` 将 allowlist 中的环境变量通过 `-e KEY=VALUE` 传入容器
- [ ] 5.3 验证 `run_sql_query` 在容器内仍能读取数据库连接环境变量

## 6. 回归测试与验证

- [ ] 6.1 `AGENT_SANDBOX=local` 时，确认现有行为完全不变
- [ ] 6.2 `AGENT_SANDBOX=docker` 时，运行 finance 技能测试对话
- [ ] 6.3 在容器内执行 `pip install psycopg2-binary`，随后 `run_sql_query` 成功返回数据
- [ ] 6.4 检查 `logs/deep/tool_results.jsonl`，确认无 `No module named 'psycopg2'` 错误
- [ ] 6.5 验证 Docker 未启动时自动降级到 LocalShellBackend，且服务不崩溃
- [ ] 6.6 在 `.env.example` 中追加 `AGENT_SANDBOX` 配置说明
