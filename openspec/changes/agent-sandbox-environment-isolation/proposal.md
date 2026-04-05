## 提案：使用 Sandbox Backend 隔离 Agent 运行时环境

### 背景

当前 `DeepAgentRuntime` 使用 `WindowsShellBackend`（继承 `LocalShellBackend`）在宿主 Windows 系统上直接执行工具调用与 Shell 命令。这导致以下问题：

1. **Python 环境漂移**：Agent 调用 `pip install` 时，命令落在系统默认的 Python（miniconda3），而 Runtime 本身运行在 `.venv-new` 中，导致包安装到了错误的环境。
2. **跨语言环境问题**：今后如果引入 Node.js、Java、Go 等技能，宿主机的 PATH、版本、依赖难以可控地交给 LLM 自行管理。
3. **Prompt 提示词不可持续**：寄希望于在系统提示词里不断追加 "使用 .venv-new\\Scripts\\python.exe" 等说明，是一种脆弱且不可扩展的临时方案。

### 目标

将 Agent 的文件系统操作与 Shell 命令执行迁移到**受控的 Sandbox 环境**中，使 LLM 能够在一个独立、完整、可自服务的环境中自行安装依赖、管理版本、执行任意语言代码，而不依赖宿主机的提示词约定。

### 核心思路

1. **实现 `DockerSandboxBackend`**：继承 `deepagents.backends.sandbox.BaseSandbox`，将 `execute()` 转发到 Docker 容器内执行。
2. **容器镜像预置多语言运行时**：基础镜像同时携带 Python（含 pip/uv）、Node.js（npm）、Git 等常用工具，满足当前及未来技能需求。
3. **挂载 Skills 目录**：将宿主机的 `skills/` 目录挂载进容器的固定工作目录（如 `/workspace/skills`），保证文件操作持久化。
4. **Deep Runtime 切换 Backend**：在 `deep.py` 中将 `AgentBuilder.with_backend(...)` 从 `WindowsShellBackend` 替换为 `DockerSandboxBackend`。
5. **CompositeBackend 保留文件路由**（可选）：若未来需要同时访问项目源代码和 skills 目录，可继续使用 `CompositeBackend` 将 Docker Sandbox 作为其中一路 backend。

### 预期收益

- 彻底解决 Python 虚拟环境隔离问题，Agent 的 `pip install` 直接落在容器内部环境。
- 支持 Node.js / Java / Go 等未来技能：LLM 可自行在容器内 `npm install`、`apt-get install` 等。
- 安全性提升：即使 Agent 执行了危险命令，影响范围也仅限于容器。
- 无需再在系统提示词中维护冗长的 Windows 环境使用说明。

### 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Docker Desktop 当前未启动 | 高 | 设计方案需包含启动检测与自动拉起/提示机制 |
| 容器启动耗时增加首次响应延迟 | 中 | 使用 `docker run --rm` 复用已启动的守护容器，或采用 `docker exec` 模式 |
| Windows Docker 路径挂载兼容性 | 中 | 使用 Docker Desktop 的 WSL2 后端，Windows 路径自动转换 |
| 镜像体积增大部署成本 | 低 | 基础镜像控制在合理大小（如 `python:3.11-slim` + 少量工具层） |
