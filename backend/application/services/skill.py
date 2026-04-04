"""
SkillService - 技能应用服务

职责:
- 技能加载、卸载用例
- 技能生命周期管理
- 技能工具注册协调
"""

from typing import Optional, Callable, Any
from pathlib import Path
from dataclasses import dataclass

from backend.domain.models import Skill, SkillDefinition
from backend.application.dto.responses import LoadSkillResult, SkillInfoDTO
from backend.domain.models.events import SkillLoaded, SkillUnloaded


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    handler: Callable[..., Any]
    description: str
    schema: Optional[Any] = None


class SkillNotFoundError(Exception):
    """技能不存在错误"""
    pass


class SkillService:
    """技能应用服务

    提供技能生命周期管理的高级用例接口，
    协调技能加载、工具注册等操作。

    Attributes:
        _repo: 技能仓库接口
        _event_bus: 事件总线接口
        _tool_mgr: 工具管理器接口
        _skills_dir: 技能目录路径
    """

    def __init__(
        self,
        skill_repo,
        event_bus,
        tool_manager,
        skills_dir: Path = Path("skills")
    ):
        """初始化 SkillService

        Args:
            skill_repo: 实现 ISkillRepository 接口的对象
            event_bus: 实现 IEventBus 接口的对象
            tool_manager: 实现 IToolManager 接口的对象
            skills_dir: 技能目录路径（默认 "skills"）
        """
        self._repo = skill_repo
        self._event_bus = event_bus
        self._tool_mgr = tool_manager
        self._skills_dir = skills_dir

    async def load_skill_from_directory(
        self,
        skill_path: Path
    ) -> LoadSkillResult:
        """从目录加载技能

        流程:
        1. 读取 SKILL.md
        2. 解析技能定义
        3. 加载工具脚本
        4. 注册到 ToolManager
        5. 保存技能实体

        Args:
            skill_path: 技能目录路径

        Returns:
            LoadSkillResult: 加载结果

        Raises:
            SkillNotFoundError: SKILL.md 不存在时
        """
        # 1. 读取技能定义
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise SkillNotFoundError(f"SKILL.md not found in {skill_path}")

        metadata, body = self._parse_skill_md(skill_md.read_text(encoding="utf-8"))
        definition = SkillDefinition(
            name=metadata.get("name", skill_path.name),
            description=metadata.get("description", ""),
            version=metadata.get("version", "0.1.0"),
            author=metadata.get("author"),
        )

        # 2. 加载工具
        tools = []
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            for script in scripts_dir.glob("*.py"):
                tool = self._load_tool_from_script(script)
                if tool:
                    tools.append(tool)

        # 3. 创建技能实体
        skill_id = skill_path.name
        skill = Skill(
            id=skill_id,
            definition=definition,
            metadata={
                "source_path": str(skill_path),
                "body": body,
            },
            scripts_loaded=len(tools) > 0,
        )

        # 4. 注册工具
        for tool in tools:
            self._tool_mgr.register(
                name=f"{skill_id}.{tool.name}",
                handler=tool.handler,
                description=tool.description,
                parameters_schema=tool.schema,
            )

        # 5. 保存技能
        await self._repo.save(skill)

        # 6. 发射事件
        self._event_bus.emit(SkillLoaded(
            skill_id=skill_id,
            name=definition.name,
            tool_count=len(tools),
        ))

        return LoadSkillResult(
            skill_id=skill_id,
            name=definition.name,
            tool_count=len(tools),
            loaded=True
        )

    async def unload_skill(self, skill_id: str) -> bool:
        """卸载技能

        流程:
        1. 注销工具
        2. 删除技能
        3. 发射事件

        Args:
            skill_id: 技能 ID

        Returns:
            bool: 是否成功卸载
        """
        skill = await self._repo.get(skill_id)
        if not skill:
            return False

        # 1. 注销工具（从元数据中获取工具列表）
        tools = skill.metadata.get("tools", [])
        for tool_name in tools:
            self._tool_mgr.unregister(f"{skill_id}.{tool_name}")

        # 2. 删除技能
        await self._repo.delete(skill_id)

        # 3. 发射事件
        self._event_bus.emit(SkillUnloaded(skill_id=skill_id))

        return True

    async def list_skills(self) -> list[SkillInfoDTO]:
        """列出所有技能

        Returns:
            list[SkillInfoDTO]: 技能信息列表
        """
        skills = await self._repo.list_all()
        return [
            SkillInfoDTO(
                id=s.id,
                name=s.definition.name,
                description=s.definition.description,
                tools=s.metadata.get("tools", []),
                active=s.scripts_loaded,
            )
            for s in skills
        ]

    async def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能实体

        Args:
            skill_id: 技能 ID

        Returns:
            Skill: 技能实体，不存在时返回 None
        """
        return await self._repo.get(skill_id)

    async def activate_skill(self, skill_id: str) -> bool:
        """激活技能（确保已加载）

        Args:
            skill_id: 技能 ID

        Returns:
            bool: 是否成功激活
        """
        skill = await self._repo.get(skill_id)
        if skill:
            return True  # 已加载

        # 尝试从目录加载
        skill_path = self._skills_dir / skill_id
        if skill_path.exists():
            try:
                await self.load_skill_from_directory(skill_path)
                return True
            except SkillNotFoundError:
                pass

        return False

    def _parse_skill_md(self, content: str) -> tuple[dict, str]:
        """解析 SKILL.md 的 YAML front-matter

        Args:
            content: SKILL.md 文件内容

        Returns:
            tuple[dict, str]: (元数据字典, 正文内容)
        """
        if not content.startswith("---"):
            return {}, content

        end = content.find("---", 3)
        if end < 0:
            return {}, content

        front_matter = content[3:end].strip()
        body = content[end + 3:].strip()

        metadata = {}
        for line in front_matter.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        return metadata, body

    def _load_tool_from_script(self, script_path: Path) -> Optional[ToolInfo]:
        """从 Python 脚本加载工具

        Args:
            script_path: 脚本文件路径

        Returns:
            ToolInfo: 工具信息，加载失败时返回 None
        """
        # 简化实现：返回占位工具信息
        # 实际实现需要动态导入模块并提取 @tool 装饰的函数
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                script_path.stem, script_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 查找 @tool 装饰的函数
                for name in dir(module):
                    obj = getattr(module, name)
                    if callable(obj) and hasattr(obj, '_is_tool'):
                        return ToolInfo(
                            name=name,
                            handler=obj,
                            description=getattr(obj, '_description', ''),
                            schema=getattr(obj, '_schema', None),
                        )
        except Exception:
            pass

        return None
