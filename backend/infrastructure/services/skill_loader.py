"""
Skill Loader - 技能脚本加载器

处理技能脚本的懒加载和工具注册。
"""

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from backend.domain.models import Skill


class SkillScriptLoader:
    """技能脚本加载器"""

    def __init__(self, tool_manager=None):
        self._tool_mgr = tool_manager

    def load_scripts(self, skill: "Skill") -> None:
        """懒加载：导入 scripts/ 下的 .py 文件，注册 @tool 函数。"""
        from backend.infrastructure.tools.toolkit import scan_tools

        if not skill.path:
            skill.scripts_loaded = True
            return

        scripts_dir = Path(skill.path) / "scripts"
        if not scripts_dir.exists():
            skill.scripts_loaded = True
            return

        tool_count = 0
        for py_file in sorted(scripts_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"skills.{skill.id}.{py_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                for tool_item in scan_tools(module):
                    if self._tool_mgr:
                        self._tool_mgr.register(
                            name=tool_item["name"],
                            handler=tool_item["handler"],
                            description=tool_item["description"],
                            parameters=tool_item["parameters"],
                        )
                        tool_count += 1
            except Exception:
                logger.exception("[SkillManager] Failed to load script %s", py_file)

        skill.scripts_loaded = True
        logger.info("[SkillManager] Lazy-loaded %d tools for skill '%s'", tool_count, skill.id)
