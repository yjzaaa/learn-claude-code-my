"""Deep Skill Loader Mixin - 技能加载功能

从 deep_legacy.py 提取的技能加载逻辑。
"""

import importlib.util
import sys
from pathlib import Path

from loguru import logger

from backend.infrastructure.runtime.base.runtime import ToolCache
from backend.infrastructure.tools.toolkit import scan_tools


class DeepSkillLoaderMixin:
    """技能加载 Mixin"""

    _tools: dict[str, ToolCache]

    def _load_skill_scripts(self) -> None:
        """加载技能脚本中的工具（如 run_sql_query）"""
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
        skills_dir = project_root / "skills"

        if not skills_dir.exists():
            logger.warning("[DeepAgentRuntime] Skills directory not found: %s", skills_dir)
            return

        tool_count = 0
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            scripts_dir = skill_dir / "scripts"
            if not scripts_dir.exists():
                continue

            # 将 scripts 目录添加到 sys.path 以支持相对导入
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            for py_file in sorted(scripts_dir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"skills.{skill_dir.name}.{py_file.stem}"
                try:
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    if spec is None or spec.loader is None:
                        continue

                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    for tool_item in scan_tools(module):
                        self._tools[tool_item["name"]] = ToolCache(
                            handler=tool_item["handler"],
                            description=tool_item["description"],
                            parameters_schema=tool_item.get("parameters", {}),
                        )
                        tool_count += 1
                        logger.info("[DeepAgentRuntime] Loaded skill tool: %s", tool_item["name"])
                except Exception as e:
                    # 记录警告但继续加载其他脚本
                    logger.warning(
                        "[DeepAgentRuntime] Failed to load skill script %s: %s", py_file, e
                    )

        logger.info("[DeepAgentRuntime] Loaded %d skill tools", tool_count)
