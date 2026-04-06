"""Agent Lifecycle Manager - Agent 生命周期管理

处理 Deep Agent 的初始化、技能加载和清理。
"""

import sys
from pathlib import Path
from typing import Any

from backend.infrastructure.logging import get_logger
from backend.infrastructure.tools.toolkit import scan_tools

from .types import DeepAgentConfig, ToolCache

logger = get_logger(__name__)


class AgentLifecycleManager:
    """Agent 生命周期管理器

    职责:
    - 初始化 Agent 配置
    - 加载技能脚本
    - 代理 sandbox 工具
    - 构建 Agent
    """

    def __init__(self, agent_id: str, config: DeepAgentConfig):
        self.agent_id = agent_id
        self.config = config
        self._tools: dict[str, ToolCache] = {}

    def load_skill_scripts(self) -> int:
        """加载技能脚本中的工具

        Returns:
            加载的工具数量
        """
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        skills_dir = project_root / "skills"

        if not skills_dir.exists():
            logger.warning("[AgentLifecycle] Skills directory not found: %s", skills_dir)
            return 0

        tool_count = 0
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            scripts_dir = skill_dir / "scripts"
            if not scripts_dir.exists():
                continue

            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            for py_file in sorted(scripts_dir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue

                tool_count += self._load_skill_file(py_file, skill_dir.name)

        logger.info("[AgentLifecycle] Loaded %d skill tools", tool_count)
        return tool_count

    def _load_skill_file(self, py_file: Path, skill_name: str) -> int:
        """加载单个技能文件"""
        import importlib.util

        module_name = f"skills.{skill_name}.{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                return 0

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            count = 0
            for tool_item in scan_tools(module):
                self._tools[tool_item["name"]] = ToolCache(
                    handler=tool_item["handler"],
                    description=tool_item["description"],
                    parameters_schema=tool_item.get("parameters", {}),
                )
                count += 1
                logger.info("[AgentLifecycle] Loaded skill tool: %s", tool_item["name"])
            return count

        except Exception as e:
            logger.warning("[AgentLifecycle] Failed to load skill script %s: %s", py_file, e)
            return 0

    def proxy_sandbox_tools(self, backend: Any) -> None:
        """将需要特定运行环境的工具代理到 sandbox 容器"""
        import base64
        import json

        if "run_sql_query" in self._tools:
            original = self._tools["run_sql_query"]

            def proxy_run_sql_query(sql: str, limit: int = 200) -> str:
                payload = json.dumps({"sql": sql, "limit": limit})
                b64 = base64.b64encode(payload.encode()).decode()
                cmd = (
                    f'python -c "import base64, json, sys; '
                    f"p=json.loads(base64.b64decode('{b64}').decode()); "
                    f"sys.path.insert(0, 'finance/scripts'); "
                    f"from sql_query import run_sql_query; "
                    f'print(run_sql_query(**p))"'
                )
                result = backend.execute(cmd)
                return result.output

            self._tools["run_sql_query"] = ToolCache(
                handler=proxy_run_sql_query,
                description=original.description,
                parameters_schema=original.parameters_schema,
            )
            logger.info("[AgentLifecycle] Proxied run_sql_query to sandbox")

    @property
    def tools(self) -> dict[str, ToolCache]:
        """获取工具字典"""
        return self._tools

    def register_tool(
        self,
        name: str,
        handler: Any,
        description: str,
        parameters_schema: dict | None = None,
    ) -> None:
        """注册工具"""
        self._tools[name] = ToolCache(
            handler=handler,
            description=description,
            parameters_schema=parameters_schema or {},
        )
        logger.debug("[AgentLifecycle] Registered tool: %s", name)

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.debug("[AgentLifecycle] Unregistered tool: %s", name)


__all__ = ["AgentLifecycleManager"]
