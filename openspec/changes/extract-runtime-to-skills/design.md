# 设计文档：将 Runtime 业务逻辑提取为 Skills

## Context

当前 `SimpleRuntime` (635 行) 混合了框架代码和业务逻辑。业务逻辑分散在以下方法中：

- `_build_system_prompt()` (行 350-378): 构建系统提示词
- `setup_workspace_tools()` (行 567-587): 注册工作区工具
- `close_dialog()` (行 409-426): 记忆总结
- HITL API (行 532-561): Skill 编辑和 Todo 管理

## Goals

1. **单一职责**: Runtime 专注于流程编排，Skills 专注于业务逻辑
2. **可复用**: 相同的 skill 可用于 SimpleRuntime 和 DeepRuntime
3. **可配置**: 通过 YAML 配置启用/禁用 skills
4. **向后兼容**: 现有 API 保持不变

## Non-Goals

- 不修改底层工具系统 (ToolManager)
- 不修改 Provider 系统
- 不修改事件总线
- 不修改对话存储格式

## Design Decisions

### 1. Skill 接口设计

```python
# skills/base.py
class BusinessSkill(ABC):
    """业务技能基类"""

    @property
    @abstractmethod
    def skill_id(self) -> str:
        """Skill 唯一标识"""

    @property
    @abstractmethod
    def system_prompt(self) -> Optional[str]:
        """系统提示词片段（可选）"""

    @property
    def tools(self) -> List[Callable]:
        """Skill 提供的工具（可选）"""
        return []

    async def on_dialog_start(self, dialog_id: str) -> None:
        """对话开始时的钩子"""
        pass

    async def on_dialog_end(self, dialog_id: str, messages: List[Message]) -> None:
        """对话结束时的钩子"""
        pass

    async def before_tool_call(self, tool_name: str, args: dict) -> dict:
        """工具调用前的钩子"""
        return args

    async def after_tool_call(self, tool_name: str, result: Any) -> Any:
        """工具调用后的钩子"""
        return result
```

### 2. Skill 注册机制

Runtime 通过 `SkillRegistry` 发现和加载 skills：

```python
# core/agent/skill_registry.py
class SkillRegistry:
    """Skill 注册表"""

    def __init__(self, skills_dir: str):
        self._skills_dir = Path(skills_dir)
        self._skills: Dict[str, BusinessSkill] = {}

    def discover(self) -> List[BusinessSkill]:
        """发现并加载所有 skills"""
        for skill_dir in self._skills_dir.iterdir():
            if skill_dir.is_dir():
                skill = self._load_skill(skill_dir)
                if skill:
                    self._skills[skill.skill_id] = skill
        return list(self._skills.values())

    def get_system_prompt(self) -> str:
        """聚合所有 skills 的系统提示词"""
        prompts = []
        for skill in self._skills.values():
            if skill.system_prompt:
                prompts.append(f"[{skill.skill_id}]\n{skill.system_prompt}")
        return "\n\n".join(prompts)

    def get_tools(self) -> List[Callable]:
        """聚合所有 skills 的工具"""
        tools = []
        for skill in self._skills.values():
            tools.extend(skill.tools)
        return tools
```

### 3. 具体 Skill 设计

#### system-prompt-builder

```python
# skills/system-prompt-builder/__init__.py
from .skill import SystemPromptBuilderSkill

__all__ = ["SystemPromptBuilderSkill"]
```

```python
# skills/system-prompt-builder/skill.py
class SystemPromptBuilderSkill(BusinessSkill):
    """系统提示词构建 Skill"""

    @property
    def skill_id(self) -> str:
        return "system-prompt-builder"

    @property
    def system_prompt(self) -> str:
        # 返回基础系统提示词
        return """You are a helpful AI assistant."""

    def build_full_prompt(
        self,
        base_prompt: str,
        memory: Optional[str],
        skill_prompts: List[str],
        plugin_prompt: Optional[str]
    ) -> str:
        """构建完整系统提示词"""
        parts = [base_prompt]

        if memory:
            parts.append(f"\n# Long-term Memory\n{memory}")

        if skill_prompts:
            parts.append("\nActive skills:")
            parts.append("\n\n".join(skill_prompts))

        if plugin_prompt:
            parts.append(plugin_prompt)

        return "\n".join(parts)
```

#### workspace-tools

```python
# skills/workspace-tools/skill.py
class WorkspaceToolsSkill(BusinessSkill):
    """工作区工具 Skill"""

    def __init__(self, workdir: Path):
        self._workspace = WorkspaceOps(workdir)

    @property
    def skill_id(self) -> str:
        return "workspace-tools"

    @property
    def system_prompt(self) -> str:
        return """You have access to workspace tools for file operations.
Use these tools to read, write, and search files in the workspace."""

    @property
    def tools(self) -> List[Callable]:
        return list(self._workspace.get_tools())
```

#### memory-manager

```python
# skills/memory-manager/skill.py
class MemoryManagerSkill(BusinessSkill):
    """记忆管理 Skill"""

    @property
    def skill_id(self) -> str:
        return "memory-manager"

    async def on_dialog_end(self, dialog_id: str, messages: List[Message]) -> None:
        """对话结束时总结并保存记忆"""
        # 调用原有的记忆管理逻辑
        await self._summarize_and_store(dialog_id, messages)

    def load_memory(self) -> str:
        """加载长期记忆"""
        memory_file = Path(".workspace/memory.md")
        if memory_file.exists():
            return memory_file.read_text(encoding="utf-8")
        return ""
```

#### hitl-manager

```python
# skills/hitl-manager/skill.py
class HITLManagerSkill(BusinessSkill):
    """HITL 管理 Skill"""

    @property
    def skill_id(self) -> str:
        return "hitl-manager"

    def get_skill_edit_proposals(self, dialog_id: Optional[str] = None) -> list[dict]:
        """获取待处理的 Skill 编辑提案"""
        if not is_skill_edit_hitl_enabled():
            return []
        return skill_edit_hitl_store.list_pending(dialog_id)

    def get_todos(self, dialog_id: str) -> TodoStateDTO:
        """获取对话的 Todo 列表"""
        if not is_todo_hook_enabled():
            return TodoStateDTO(dialog_id=dialog_id, items=[], rounds_since_todo=0, updated_at=0.0)
        return todo_store.get_todos(dialog_id)

    def update_todos(self, dialog_id: str, items: list[dict]) -> tuple[bool, str]:
        """更新对话的 Todo 列表"""
        if not is_todo_hook_enabled():
            return False, "Todo HITL disabled"
        return todo_store.update_todos(dialog_id, items)
```

### 4. Runtime 重构

#### SimpleRuntime 变更

```python
class SimpleRuntime(AgentRuntime):
    async def initialize(self, config: dict) -> None:
        # ... 现有初始化代码 ...

        # 加载业务 skills
        self._skill_registry = SkillRegistry(
            config.get("skills_dir", "skills")
        )
        self._business_skills = self._skill_registry.discover()

        # 注册 skills 的工具
        for skill in self._business_skills:
            for tool in skill.tools:
                self.register_tool_from_skill(skill, tool)

    def _build_system_prompt(self) -> str:
        """新的系统提示词构建 - 使用 skill registry"""
        base_prompt = "You are a helpful AI assistant."

        # 使用 memory-manager skill 加载记忆
        memory_skill = self._skill_registry.get("memory-manager")
        memory = memory_skill.load_memory() if memory_skill else ""

        # 使用 system-prompt-builder skill 构建完整提示词
        builder = self._skill_registry.get("system-prompt-builder")
        if builder:
            return builder.build_full_prompt(
                base_prompt=base_prompt,
                memory=memory,
                skill_prompts=self._get_skill_prompts(),
                plugin_prompt=self._plugin_mgr.get_combined_system_prompt()
            )

        # 回退到简单实现
        return self._build_system_prompt_legacy()

    def setup_workspace_tools(self, workdir: Any) -> None:
        """使用 workspace-tools skill"""
        from skills.workspace_tools import WorkspaceToolsSkill

        skill = WorkspaceToolsSkill(Path(workdir))
        for tool in skill.tools:
            self.register_tool_from_skill(skill, tool)

    async def close_dialog(self, dialog_id: str, reason: str = "completed"):
        """使用 memory-manager skill 总结记忆"""
        messages = self._dialog_mgr.get_messages_for_llm(dialog_id)

        # 调用所有 skills 的 on_dialog_end 钩子
        for skill in self._business_skills:
            await skill.on_dialog_end(dialog_id, messages)

        await self._dialog_mgr.close(dialog_id, reason)
```

### 5. Skill 配置

每个 skill 目录包含 `skill.yaml` 配置文件：

```yaml
# skills/workspace-tools/skill.yaml
id: workspace-tools
name: Workspace Tools
description: File operations and workspace management
version: 1.0.0
author: system

system_prompt: |
  You have access to workspace tools for file operations.
  Use these tools to read, write, and search files.

tools:
  - read_file
  - write_file
  - list_directory
  - search_code

dependencies: []
```

## Migration Plan

### Phase 1: 创建 Skill 基类和注册表
1. 创建 `skills/base.py` - BusinessSkill 基类
2. 创建 `core/agent/skill_registry.py` - SkillRegistry 注册表

### Phase 2: 实现业务 Skills
1. 创建 `skills/system-prompt-builder/` - 系统提示词构建
2. 创建 `skills/workspace-tools/` - 工作区工具
3. 创建 `skills/memory-manager/` - 记忆管理
4. 创建 `skills/hitl-manager/` - HITL 管理

### Phase 3: 重构 SimpleRuntime
1. 更新 `SimpleRuntime.initialize()` 加载 skills
2. 更新 `_build_system_prompt()` 使用 skill registry
3. 更新 `setup_workspace_tools()` 使用 skill
4. 更新 `close_dialog()` 使用 skill hooks

### Phase 4: 重构 DeepRuntime
1. 更新 `DeepRuntime.initialize()` 接受 skills 参数
2. 传递技能工具到 deep agent

### Phase 5: 测试和验证
1. 为每个 skill 编写单元测试
2. 验证 SimpleRuntime 功能等价
3. 验证 DeepRuntime 功能等价

## Risks

| Risk | Mitigation |
|------|------------|
| 技能加载失败导致 runtime 无法启动 | 添加技能加载错误处理和降级策略 |
| 技能间循环依赖 | 明确的依赖声明和拓扑排序加载 |
| 性能退化 | 技能注册表缓存，避免重复计算 |
| API 破坏性变更 | 保持向后兼容，提供迁移指南 |
