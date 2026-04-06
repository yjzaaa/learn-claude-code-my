"""Deep Sandbox Mixin - 沙箱工具代理

从 deep_legacy.py 提取的沙箱代理逻辑。
"""

import base64
import json
from typing import Any

from loguru import logger

from backend.infrastructure.runtime.base.runtime import ToolCache


class DeepSandboxMixin:
    """沙箱代理 Mixin"""

    _tools: dict[str, ToolCache]

    def _proxy_sandbox_tools(self, backend: Any) -> None:
        """将需要特定运行环境的工具代理到 sandbox 容器中执行。

        这样自定义 Python 工具（如 run_sql_query）不再受限于宿主机 .venv-new
        的依赖环境，而是在容器内统一执行。
        """
        if "run_sql_query" in self._tools:
            original = self._tools["run_sql_query"]

            def proxy_run_sql_query(sql: str, limit: int = 200) -> str:
                # 使用 base64 内嵌 Python 脚本，彻底避免 Windows + Docker + shlex 引号地狱
                payload = json.dumps({"sql": sql, "limit": limit})
                b64 = base64.b64encode(payload.encode()).decode()
                # 使用绝对路径，因为容器工作目录是 /workspace/skills
                cmd = (
                    f"python -c 'import base64, json, sys; "
                    f'p=json.loads(base64.b64decode("{b64}").decode()); '
                    f'sys.path.insert(0, "/workspace/skills/finance/scripts"); '
                    f"from sql_query import run_sql_query; "
                    f"print(run_sql_query(**p))'"
                )
                result = backend.execute(cmd)
                return result.output

            self._tools["run_sql_query"] = ToolCache(
                handler=proxy_run_sql_query,
                description=original.description,
                parameters_schema=original.parameters_schema,
            )
            logger.info("[DeepAgentRuntime] Proxied run_sql_query to sandbox")
