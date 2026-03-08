#!/usr/bin/env python3
"""
SkillPlugin - 技能加载插件

将 s05_skill_loading 重构为插件形式
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

from loguru import logger

from . import AgentPlugin

try:
    from ..base import tool
    from ..s05_skill_loading import SkillLoader, SKILL_LOADER, WORKDIR
except ImportError:
    from agents.base import tool
    from agents.s05_skill_loading import SkillLoader, SKILL_LOADER, WORKDIR


class SkillPlugin(AgentPlugin):
    """
    技能加载插件

    提供技能加载、查询、更新等功能
    """

    name = "skill_plugin"
    description = "Skill Loading"
    enabled = True

    def __init__(self, agent: Any):
        super().__init__(agent)
        self.skill_loader = SKILL_LOADER
        self._pending_skill_content: str = ""  # 用于暂存加载的技能内容

    def get_additional_tools(self) -> List[Callable]:
        """返回技能加载相关工具"""
        return [
            self._load_skill_tool,
            self._load_skill_reference_tool,
            self._load_skill_script_tool,
            self._update_skill_tool,
            self._list_skills_tool,
        ]

    def get_system_prompt_addon(self) -> str:
        """返回技能描述作为系统提示词追加"""
        descriptions = self.skill_loader.get_descriptions()
        if descriptions == "(no skills available)":
            return ""

        return f"""## Available Skills
{descriptions}

When you need specialized knowledge:
1. Call load_skill(name) to get detailed instructions
2. Follow the loaded skill to answer user questions
3. Use load_skill_reference() or load_skill_script() for additional resources
"""

    def on_tool_result(self, name: str, result: str) -> None:
        """
        处理工具结果，暂存加载的技能内容

        这样可以在后续的消息生成中使用技能内容
        """
        if name == "load_skill" and not result.startswith("Error:"):
            self._pending_skill_content = result
            logger.info(f"[SkillPlugin] Loaded skill content (length: {len(result)})")

    def _extract_skill_from_messages(self, messages: List[Dict]) -> str:
        """
        从消息历史中提取最近一次加载的技能内容

        检查 tool 角色的消息，找到 load_skill 的结果
        """
        for msg in reversed(messages):
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if "<skill name=" in content and "</skill>" in content:
                    return content
        return ""

    @tool(name="load_skill", description="Load specialized knowledge by name. Always call this first when the task matches a skill domain.")
    def _load_skill_tool(self, name: str) -> str:
        """加载指定名称的技能"""
        return self.skill_loader.get_content(name)

    @tool(name="load_skill_reference", description="Load a reference document from a skill. Omit path to list available docs.")
    def _load_skill_reference_tool(self, name: str, path: str = "") -> str:
        """加载技能的参考文档"""
        return self.skill_loader.get_references_content(name, path)

    @tool(name="load_skill_script", description="Load a script from a skill. Omit path to list available scripts.")
    def _load_skill_script_tool(self, name: str, path: str = "") -> str:
        """加载技能的脚本"""
        return self.skill_loader.get_scripts_content(name, path)

    @tool(name="update_skill", description="Update a skill file. Use old_text+new_text for incremental edits, or full_content for complete replacement.")
    def _update_skill_tool(
        self,
        name: str,
        old_text: str = "",
        new_text: str = "",
        full_content: str = "",
        reason: str = ""
    ) -> str:
        """更新技能文件"""
        return self.skill_loader.update_skill(
            name,
            old_text or None,
            new_text or None,
            full_content or None,
            reason
        )

    @tool(name="list_skills", description="List all available skills with descriptions.")
    def _list_skills_tool(self) -> str:
        """列出所有可用技能"""
        return self.skill_loader.get_descriptions()
