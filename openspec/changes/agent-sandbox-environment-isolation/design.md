## Context

当前 `DeepAgentRuntime` 通过 `AgentBuilder.with_backend(backend)` 注入了一个 `WindowsShellBackend` 实例。该 backend 继承自 `deepagents.backends.local_shell.LocalShellBackend`，本质上是在宿主 Windows 系统上直接执行 subprocess。这带来以下问题：

- **环境不可控**：宿主系统上存在多个 Python 发行版（miniconda3、系统 Python、`.venv-new` 内的 uv Python），Agent 通过 `execute("pip install ...")` 安装的依赖往往落在与 Runtime 不一致的环境中，导致 `run_sql_query` 等工具反复出现 `No module named 'psycopg2'`。
- **提示词驱动不可扩展**：为缓解环境问题，系统提示词里不断追加 "使用 `py` 而不是 `python`"、".venv 路径在 xxx" 等说明。随着技能增加（Node.js、Java、Go），这种靠提示词约束的方案将迅速失控。
- **deepagents 原生支持 Sandbox**：`deepagents.backends.protocol.SandboxBackendProtocol` 定义了完整的隔离执行接口，`BaseSandbox` 提供了基于 `execute()` 的默认文件操作实现。我们只需要提供一个把 `execute()` 映射到 Docker 容器的具体子类即可。

## Goals / Non-Goals

**Goals：**
- 设计并实现一个 `DockerSandboxBackend`，使 Agent 的 shell 命令与文件操作在 Docker 容器内完成。
- 容器内预置多语言运行时（Python + pip/uv、Node.js + npm、Git、常用 build tools），让 LLM 自行安装依赖而无需提示词干预。
- 将 `skills/` 目录作为 volume 挂载进容器，保证文件修改持久化。
- 在 `DeepAgentRuntime` 中完成 backend 切换，保持 `SimpleRuntime` 不受影响。
- 提供 Docker 未启动时的优雅降级方案（如回退到 `LocalShellBackend` 或抛出明确错误）。

**Non-Goals：**
- 不修改 `deepagents` 框架源码（仅使用其公开的 `BaseSandbox` 和 `SandboxBackendProtocol`）。
- 不将主后端服务本身容器化（仅容器化 Agent 的工具执行层）。
- 不强制要求所有技能使用同一镜像（先提供单一通用镜像，未来可按技能拆分）。

## Decisions

### 1. 使用 `docker exec` 复用守护容器模式

**选择**：启动一个长期运行的守护容器（`docker run -d --name deep-agent-sandbox ... sleep infinity`），所有 `execute()` 调用通过 `docker exec` 进入该容器执行命令。

**理由**：
- 避免每次命令都 `docker run --rm` 的启动开销（Windows 下尤其明显）。
- 容器内的文件系统状态（如已安装的 pip 包、npm 模块）可以持续保留。
- `BaseSandbox` 的文件操作协议方法（`read`/`write`/`glob`/`grep` 等）内部也会调用 `self.execute()`，因此统一走 `docker exec` 即可获得一致的容器内视图。

**替代方案**：`docker run --rm` 每次新建容器 — 更干净，但性能差，不适合高频 tool call。

### 2. 镜像基于 `python:3.11-slim` 并叠加工具层

**选择**：使用 `python:3.11-slim` 作为基础镜像，Dockerfile 中安装 `nodejs`、`npm`、`git`、`build-essential`、`curl` 以及 `uv`。

**理由**：
- 覆盖当前 Python 技能（finance、code-review）和可预见的 Node.js 技能需求。
- slim 版本镜像体积可控（约 200–300MB 叠加后）。
- `uv` 作为现代 Python 包管理器，比 pip 更快，Agent 也能使用。

**替代方案**：`ubuntu:22.04` 从零安装 Python — 更通用但镜像更大，构建更慢。

### 3. 挂载点设计：`/workspace/skills` 映射到宿主 `skills/`

**选择**：容器内固定工作目录为 `/workspace/skills`，对应宿主机 `D:\learn-claude-code-my\skills`。

**理由**：
- 与现有 `WindowsShellBackend` 的 `root_dir=skills_dir` 语义对齐。
- `virtual_mode=True` 时，Agent 继续使用 `/finance/SKILL.md` 风格路径，只是这些路径现在在容器内解析。
- 挂载 volume 后，Agent 在容器内写入的文件会实时同步到宿主磁盘，持久化无虞。

### 4. 环境变量继承：默认携带宿主 `os.environ` + 覆盖 `PATH`

**选择**：`DockerSandboxBackend` 的 `execute()` 在调用 `docker exec` 时，通过 `-e` 传递关键环境变量（如 `ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`DB_*` 等数据库连接信息）。

**理由**：
- 当前 `finance` 技能的 `sql_query.py` 依赖环境变量读取数据库凭据，隔离后仍需可用。
- 但 `PATH` 等环境变量应指向容器内部路径，不应使用宿主 Windows PATH。

### 5. Deep Runtime Backend 切换逻辑

**选择**：在 `deep.py` 中新增 `AGENT_SANDBOX=docker|local` 环境变量控制：
- `docker`：使用 `DockerSandboxBackend`
- `local`（默认）：继续使用 `LocalShellBackend`（即当前行为）

**理由**：
- 允许开发者在本地快速测试时不需要 Docker。
- 生产/演示环境启用 Docker Sandbox，获得一致隔离性。
- 降低迁移风险，可逐步验证。

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DeepAgentRuntime                           │
│                     (host Python .venv-new)                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ AgentBuilder.with_backend(backend)
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              DockerSandboxBackend / LocalShellBackend               │
│              (selected by AGENT_SANDBOX env var)                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            │ docker exec                                      │ local subprocess
            ▼                                                   ▼
┌─────────────────────────────┐                    ┌─────────────────────────────┐
│   deep-agent-sandbox        │                    │   Host Windows Shell        │
│   (Docker container)        │                    │   (miniconda3 / system)     │
│                             │                    │                             │
│  /workspace/skills  ◄───────┤◄── volume mount ───┤►  D:\learn-claude-code-my   │
│                             │                    │     \skills                 │
│  python, node, npm, uv, git │                    │  python, node (unreliable)  │
└─────────────────────────────┘                    └─────────────────────────────┘
```

### `DockerSandboxBackend` 类设计

```python
from deepagents.backends.sandbox import BaseSandbox
from deepagents.backends.protocol import ExecuteResponse

class DockerSandboxBackend(BaseSandbox):
    def __init__(
        self,
        root_dir: str,
        image: str = "deep-agent-sandbox:latest",
        container_name: str = "deep-agent-sandbox",
        env_allowlist: list[str] | None = None,
    ) -> None:
        self.root_dir = str(Path(root_dir).resolve())
        self.image = image
        self.container_name = container_name
        self.env_allowlist = env_allowlist or ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DB_*"]
        self._ensure_container_running()

    def _ensure_container_running(self) -> None:
        """检查容器是否存活，未启动则自动创建并启动。"""
        ...

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        """通过 docker exec 在容器内执行命令。"""
        ...

    @property
    def id(self) -> str:
        return self.container_name
```

### Dockerfile 设计（`infra/sandbox/Dockerfile`）

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git curl build-essential nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /workspace/skills
CMD ["sleep", "infinity"]
```

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Docker Desktop 未启动导致创建失败 | 高 | `__init__` 中检测 Docker daemon 状态；未启动时自动降级到 `LocalShellBackend` 并记录 warning |
| 容器内缺失特定系统库导致工具失败 | 中 | 基础镜像预置常见 build tools；Agent 可在容器内执行 `apt-get install` |
| Volume 挂载的 Windows 路径兼容性 | 中 | 依赖 Docker Desktop WSL2 backend（已安装）；路径 `/d/learn-claude-code-my/skills` 形式由 Docker 自动映射 |
| 镜像构建/拉取延迟首次对话 | 中 | 构建脚本提供 `docker build` 命令；镜像构建为一次性操作 |
| 向后兼容性 | 低 | 通过 `AGENT_SANDBOX=local` 保留现有行为 |

## Migration Plan

1. **新增 `DockerSandboxBackend` 模块**：`backend/infrastructure/runtime/services/docker_sandbox_backend.py`
2. **新增 Dockerfile**：`infra/sandbox/Dockerfile`
3. **修改 `deep.py`**：读取 `AGENT_SANDBOX` 环境变量，条件注入 `DockerSandboxBackend`
4. **构建镜像**：运行 `docker build -t deep-agent-sandbox:latest -f infra/sandbox/Dockerfile .`
5. **验证**：启动后端并测试 finance 技能对话，确认 `pip install psycopg2-binary` 后 `run_sql_query` 正常执行
6. **文档更新**：在 `.env.example` 中新增 `AGENT_SANDBOX=docker` 配置项

## 与 finance 技能日志问题的关系

`tool_results.jsonl` 中观察到的大量 `No module named 'psycopg2'` 错误，直接根因就是**宿主 Windows 的 Shell 环境与 Runtime 的 Python 环境不一致**。采用本设计方案后：
- `run_sql_query` 和 `execute` 都将在同一个 Docker 容器内运行。
- Agent 只需 `pip install psycopg2-binary` 一次，后续 tool 调用即可命中同一环境。
- 无需再修改系统提示词来约束 LLM 使用哪个 Python 解释器。
