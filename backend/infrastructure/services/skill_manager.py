"""
Skill Manager - 技能管理器

管理技能的加载、注册和执行。
技能是可复用的 Agent 能力模块。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from backend.domain.models.agent.skill import Skill, SkillDefinition
from backend.domain.models.agent.tool import ActiveToolInfo
from backend.domain.models.api.stats import SkillStats
from backend.domain.models.shared.config import SkillManagerConfig
from backend.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from backend.infrastructure.event_bus import EventBus
    from backend.infrastructure.services.tool_manager import ToolManager

logger = get_logger(__name__)


class SkillManager:
    """
    技能管理器

    职责:
    - 加载和注册技能
    - 管理技能生命周期
    - 提供技能工具给 Agent

    依赖:
    - EventBus: 发射技能相关事件
    - ToolManager: 注册技能工具
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        tool_manager: ToolManager | None = None,
        config: SkillManagerConfig | None = None,
    ):
        self._event_bus = event_bus
        self._tool_mgr = tool_manager
        self._config = config or SkillManagerConfig()

        # 已加载的技能
        self._skills: dict[str, Skill] = {}

        # 技能目录
        self._skills_dir = Path(self._config.skills_dir or "skills")

        # 技能工具注册表
        self._skill_tools: dict[str, list[str]] = {}  # skill_id -> [tool_names]

    def register_skill(
        self,
        skill_id: str,
        definition: SkillDefinition,
        tools: list[dict[str, Any]] | None = None,
        handler: Callable | None = None,
    ) -> Skill:
        """
        注册技能

        Args:
            skill_id: 技能 ID
            definition: 技能定义
            tools: 技能提供的工具列表
            handler: 技能主处理函数

        Returns:
            技能实例
        """
        skill = Skill(
            id=skill_id,
            definition=definition,
            metadata={"tools": tools or [], "has_handler": handler is not None},
        )

        self._skills[skill_id] = skill

        # 注册技能工具
        if tools and self._tool_mgr:
            tool_names = []
            for tool_info in tools:
                tool_name = f"{skill_id}.{tool_info['name']}"
                self._tool_mgr.register(
                    name=tool_name,
                    handler=tool_info.get("handler", handler),
                    description=tool_info.get("description", ""),
                    parameters=tool_info.get("parameters", {}),
                )
                tool_names.append(tool_name)

            self._skill_tools[skill_id] = tool_names

        logger.info(f"[SkillManager] Registered skill: {skill_id}")
        return skill

    def load_skill_from_directory(self, skill_path: str) -> Skill | None:
        """
        从目录加载技能。支持 SKILL.md 格式（含 YAML front-matter）和旧版 skill.json。

        SKILL.md 格式示例:
            ---
            name: code-review
            description: Perform code reviews.
            ---
            # 技能说明...
        """
        path = Path(skill_path)
        if not path.exists():
            logger.warning(f"[SkillManager] Skill path not found: {skill_path}")
            return None

        # 查找 SKILL.md：先找当前目录，再找一级子目录（兼容 finance/finance/ 结构）
        skill_md_path: Path | None = None
        actual_path: Path = path
        if (path / "SKILL.md").exists():
            skill_md_path = path / "SKILL.md"
        else:
            for subdir in path.iterdir():
                if subdir.is_dir() and (subdir / "SKILL.md").exists():
                    skill_md_path = subdir / "SKILL.md"
                    actual_path = subdir
                    break

        if skill_md_path:
            try:
                content = skill_md_path.read_text(encoding="utf-8")
                metadata, _ = self._parse_skill_md(content)
                skill_id = metadata.get("name") or path.name
                definition = SkillDefinition(
                    name=metadata.get("name", path.name),
                    description=metadata.get("description", ""),
                    version=metadata.get("version", "1.0.0"),
                    author=metadata.get("author"),
                    parameters={},
                )
                skill = self.register_skill(skill_id=skill_id, definition=definition)
                skill.path = str(actual_path)
                logger.info(f"[SkillManager] Loaded skill '{skill_id}' from {skill_md_path}")
                return skill
            except Exception as e:
                logger.exception(
                    f"[SkillManager] Failed to load SKILL.md from {skill_md_path}: {e}"
                )
                return None

        # 兼容旧版 skill.json
        config_file = path / "skill.json"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = json.load(f)
                definition = SkillDefinition(
                    name=config.get("name", path.name),
                    description=config.get("description", ""),
                    version=config.get("version", "1.0.0"),
                    author=config.get("author"),
                    parameters=config.get("parameters", {}),
                )
                skill_id = config.get("id", path.name)
                tools = config.get("tools", [])
                skill = self.register_skill(skill_id=skill_id, definition=definition, tools=tools)
                skill.path = str(path)
                logger.info(f"[SkillManager] Loaded skill '{skill_id}' from skill.json")
                return skill
            except Exception as e:
                logger.exception(f"[SkillManager] Failed to load skill.json from {skill_path}: {e}")
                return None

        logger.warning(f"[SkillManager] No SKILL.md or skill.json found in {skill_path}")
        return None

    def _parse_skill_md(self, content: str):
        """解析 SKILL.md 的 YAML front-matter，返回 (metadata_dict, body_str)。"""
        if not content.startswith("---"):
            return {}, content
        end = content.find("---", 3)
        if end < 0:
            return {}, content
        front_matter_str = content[3:end].strip()
        body = content[end + 3 :].strip()
        metadata: dict[str, Any] = {}
        for line in front_matter_str.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip()] = v.strip()
        return metadata, body

    def unload_skill(self, skill_id: str) -> bool:
        """
        卸载技能

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功卸载
        """
        if skill_id not in self._skills:
            return False

        # 注销工具
        if skill_id in self._skill_tools and self._tool_mgr:
            for tool_name in self._skill_tools[skill_id]:
                self._tool_mgr.unregister(tool_name)
            del self._skill_tools[skill_id]

        # 移除技能
        del self._skills[skill_id]

        logger.info(f"[SkillManager] Unloaded skill: {skill_id}")
        return True

    def get_skill(self, skill_id: str) -> Skill | None:
        """
        获取技能

        Args:
            skill_id: 技能 ID

        Returns:
            技能实例或 None
        """
        return self._skills.get(skill_id)

    def list_skills(self) -> list[Skill]:
        """
        列出所有技能

        Returns:
            技能列表
        """
        return list(self._skills.values())

    def load_builtin_skills(self):
        """加载内置技能"""
        if not self._skills_dir.exists():
            logger.info(f"[SkillManager] Skills directory not found: {self._skills_dir}")
            return

        for skill_dir in self._skills_dir.iterdir():
            if skill_dir.is_dir():
                self.load_skill_from_directory(str(skill_dir))

    def _load_scripts(self, skill: Skill) -> None:
        """懒加载技能脚本"""
        from .skill_loader import SkillScriptLoader

        loader = SkillScriptLoader(self._tool_mgr)
        loader.load_scripts(skill)

    def get_skill_prompt(self, skill_id: str) -> str | None:
        """
        获取技能的系统提示词，首次调用时触发脚本懒加载。

        Args:
            skill_id: 技能 ID

        Returns:
            提示词或 None
        """
        skill = self._skills.get(skill_id)
        if not skill or not skill.path:
            return None

        # 懒加载 scripts/
        if not skill.scripts_loaded:
            self._load_scripts(skill)

        # Prefer SKILL.md body content
        skill_md = Path(skill.path) / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            _, body = self._parse_skill_md(content)
            if body:
                return body

        # Fallback to legacy prompt.md
        prompt_file = Path(skill.path) / "prompt.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")

        return None

    def get_active_tools(self) -> list[ActiveToolInfo]:
        """
        获取所有激活的工具

        Returns:
            工具定义列表
        """
        tools = []
        for skill in self._skills.values():
            skill_tools = skill.metadata.get("tools", [])
            for tool in skill_tools:
                tools.append(
                    ActiveToolInfo(
                        skill_id=skill.id,
                        skill_name=skill.name,
                        tool=tool,
                    )
                )
        return tools

    def is_loaded(self, skill_id: str) -> bool:
        """检查技能是否已加载"""
        return skill_id in self._skills

    def get_stats(self) -> SkillStats:
        """获取统计信息"""
        return SkillStats(
            loaded_skills=len(self._skills),
            skill_ids=list(self._skills.keys()),
            total_tools=sum(len(tools) for tools in self._skill_tools.values()),
        )
