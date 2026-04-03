# Service 层详细设计

## 1. 设计原则

### 1.1 职责划分

| 层级 | 职责 | 示例 |
|------|------|------|
| **Service** | 编排用例，协调多个 Domain 对象 | `DialogService.create_and_run()` |
| **Manager** | 管理单一资源的生命周期 | `DialogManager.create()`, `SkillManager.load()` |
| **Repository** | 数据访问抽象 | `DialogRepository.save()` |

### 1.2 设计模式

- **Application Service**: 处理业务用例，无业务规则
- **Domain Service**: 处理跨实体的业务逻辑
- **Repository Pattern**: 数据访问抽象

## 2. Service 类设计

### 2.1 DialogService - 对话用例编排

```python
# core/application/services/dialog_service.py
from typing import AsyncIterator, Optional
from dataclasses import dataclass

from core.domain.entities.dialog import Dialog, Message
from core.domain.repositories.dialog_repository import IDialogRepository
from core.runtime.interfaces import IAgentRuntime
from core.infrastructure.messaging.event_bus import IEventBus


@dataclass
class CreateDialogResult:
    """创建对话结果"""
    dialog_id: str
    title: str
    created_at: str


@dataclass
class SendMessageResult:
    """发送消息结果"""
    message_id: str
    content: str
    token_count: int


class DialogService:
    """
    对话应用服务

    职责:
    - 编排对话生命周期用例
    - 协调 Dialog, Message, Runtime
    - 不直接操作底层存储，通过 Repository

    与 DialogManager 区别:
    - DialogManager: 底层管理，直接操作内存/存储
    - DialogService: 高层编排，面向用例
    """

    def __init__(
        self,
        dialog_repo: IDialogRepository,
        event_bus: IEventBus,
        runtime: IAgentRuntime,
    ):
        self._repo = dialog_repo
        self._event_bus = event_bus
        self._runtime = runtime

    async def create_dialog(
        self,
        user_input: str,
        title: Optional[str] = None
    ) -> CreateDialogResult:
        """
        创建对话用例

        流程:
        1. 创建 Dialog 实体
        2. 添加用户消息
        3. 保存到 Repository
        4. 发射领域事件
        """
        # 1. 创建领域对象
        dialog = Dialog.create(title=title or "New Dialog")
        message = Message.user(content=user_input)
        dialog.add_message(message)

        # 2. 持久化
        await self._repo.save(dialog)

        # 3. 发射事件
        self._event_bus.emit(DialogCreatedEvent(
            dialog_id=dialog.id,
            title=dialog.title,
            user_input=user_input
        ))

        return CreateDialogResult(
            dialog_id=dialog.id,
            title=dialog.title,
            created_at=dialog.created_at.isoformat()
        )

    async def send_message(
        self,
        dialog_id: str,
        content: str,
        stream: bool = True
    ) -> AsyncIterator[str]:
        """
        发送消息用例

        流程:
        1. 获取对话
        2. 添加用户消息
        3. 调用 Runtime 生成回复
        4. 流式返回内容
        5. 保存助手消息
        """
        # 1. 获取对话
        dialog = await self._repo.get(dialog_id)
        if not dialog:
            raise DialogNotFoundError(dialog_id)

        # 2. 添加用户消息
        user_msg = Message.user(content=content)
        dialog.add_message(user_msg)
        await self._repo.save(dialog)

        # 3. 发射事件
        self._event_bus.emit(MessageReceivedEvent(
            dialog_id=dialog_id,
            message_id=user_msg.id,
            content=content
        ))

        # 4. 调用 Runtime 生成回复
        full_content = []
        async for chunk in self._runtime.send_message(dialog_id, content):
            full_content.append(chunk)
            if stream:
                yield chunk

        # 5. 保存助手消息
        assistant_content = "".join(full_content)
        assistant_msg = Message.assistant(content=assistant_content)
        dialog.add_message(assistant_msg)
        await self._repo.save(dialog)

        # 6. 发射完成事件
        self._event_bus.emit(MessageCompletedEvent(
            dialog_id=dialog_id,
            message_id=assistant_msg.id,
            content=assistant_content,
            token_count=dialog.estimate_tokens()
        ))

    async def get_dialog_history(
        self,
        dialog_id: str,
        limit: int = 100
    ) -> list[MessageDTO]:
        """获取对话历史"""
        dialog = await self._repo.get(dialog_id)
        if not dialog:
            raise DialogNotFoundError(dialog_id)

        messages = dialog.messages[-limit:]
        return [MessageDTO.from_entity(m) for m in messages]

    async def close_dialog(self, dialog_id: str) -> None:
        """关闭对话"""
        dialog = await self._repo.get(dialog_id)
        if dialog:
            dialog.close()
            await self._repo.save(dialog)
            self._event_bus.emit(DialogClosedEvent(
                dialog_id=dialog_id
            ))
```

### 2.2 SkillService - 技能管理用例

```python
# core/application/services/skill_service.py
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from core.domain.entities.skill import Skill, SkillDefinition
from core.domain.repositories.skill_repository import ISkillRepository
from core.infrastructure.messaging.event_bus import IEventBus
from core.capabilities.interfaces import IToolManager


@dataclass
class LoadSkillResult:
    """加载技能结果"""
    skill_id: str
    name: str
    tool_count: int
    loaded: bool


@dataclass
class SkillInfoDTO:
    """技能信息 DTO"""
    id: str
    name: str
    description: str
    tools: list[str]
    active: bool


class SkillService:
    """
    技能应用服务

    职责:
    - 技能加载、卸载用例
    - 技能生命周期管理
    - 技能工具注册协调
    """

    def __init__(
        self,
        skill_repo: ISkillRepository,
        event_bus: IEventBus,
        tool_manager: IToolManager,
        skills_dir: Path = Path("skills")
    ):
        self._repo = skill_repo
        self._event_bus = event_bus
        self._tool_mgr = tool_manager
        self._skills_dir = skills_dir

    async def load_skill_from_directory(
        self,
        skill_path: Path
    ) -> LoadSkillResult:
        """
        从目录加载技能

        流程:
        1. 读取 SKILL.md
        2. 解析技能定义
        3. 加载工具脚本
        4. 注册到 ToolManager
        5. 保存技能实体
        """
        # 1. 读取技能定义
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise SkillNotFoundError(f"SKILL.md not found in {skill_path}")

        metadata, body = self._parse_skill_md(skill_md.read_text())
        definition = SkillDefinition(
            name=metadata.get("name", skill_path.name),
            description=metadata.get("description", ""),
            version=metadata.get("version", "0.1.0")
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
            tools=tools,
            source_path=str(skill_path)
        )

        # 4. 注册工具
        for tool in tools:
            self._tool_mgr.register(
                name=f"{skill_id}.{tool.name}",
                handler=tool.handler,
                description=tool.description,
                schema=tool.schema
            )

        # 5. 保存技能
        await self._repo.save(skill)

        # 6. 发射事件
        self._event_bus.emit(SkillLoadedEvent(
            skill_id=skill_id,
            name=definition.name,
            tool_count=len(tools)
        ))

        return LoadSkillResult(
            skill_id=skill_id,
            name=definition.name,
            tool_count=len(tools),
            loaded=True
        )

    async def unload_skill(self, skill_id: str) -> bool:
        """卸载技能"""
        skill = await self._repo.get(skill_id)
        if not skill:
            return False

        # 1. 注销工具
        for tool in skill.tools:
            self._tool_mgr.unregister(f"{skill_id}.{tool.name}")

        # 2. 删除技能
        await self._repo.delete(skill_id)

        # 3. 发射事件
        self._event_bus.emit(SkillUnloadedEvent(skill_id=skill_id))

        return True

    async def list_skills(self) -> list[SkillInfoDTO]:
        """列出所有技能"""
        skills = await self._repo.list_all()
        return [
            SkillInfoDTO(
                id=s.id,
                name=s.definition.name,
                description=s.definition.description,
                tools=[t.name for t in s.tools],
                active=s.active
            )
            for s in skills
        ]

    def _parse_skill_md(self, content: str) -> tuple[dict, str]:
        """解析 SKILL.md 的 YAML front-matter"""
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
        """从 Python 脚本加载工具"""
        # 实现工具加载逻辑
        pass
```

### 2.3 MemoryService - 记忆管理用例

```python
# core/application/services/memory_service.py
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.domain.entities.dialog import Dialog
from core.infrastructure.llm.base import ILLMProvider


@dataclass
class MemorySummary:
    """记忆摘要"""
    content: str
    created_at: datetime
    dialog_count: int


class MemoryService:
    """
    记忆应用服务

    职责:
    - 对话总结生成
    - 长期记忆管理
    - 记忆注入上下文
    """

    def __init__(
        self,
        llm_provider: ILLMProvider,
        memory_file: Path = Path("memory.md")
    ):
        self._llm = llm_provider
        self._memory_file = memory_file

    async def summarize_dialog(self, dialog: Dialog) -> str:
        """
        总结单个对话

        流程:
        1. 提取关键消息
        2. 调用 LLM 生成总结
        3. 格式化输出
        """
        # 1. 构建总结提示
        messages = dialog.get_messages_for_llm()
        history_text = self._format_history(messages)

        prompt = f"""请总结以下对话的关键信息（不超过200字）：

{history_text}

总结要点：
- 用户的核心需求
- 关键决策或结论
- 待办事项（如有）"""

        # 2. 调用 LLM
        summary_parts = []
        async for chunk in self._llm.chat_stream(
            messages=[{"role": "user", "content": prompt}]
        ):
            if chunk.is_content:
                summary_parts.append(chunk.content)

        summary = "".join(summary_parts).strip()

        # 3. 保存到记忆文件
        await self._append_memory(dialog.id, summary)

        return summary

    async def get_relevant_memories(
        self,
        query: str,
        limit: int = 3
    ) -> list[str]:
        """
        获取与查询相关的记忆

        简化实现：返回最近的记忆
        未来可接入向量搜索
        """
        if not self._memory_file.exists():
            return []

        content = self._memory_file.read_text()
        entries = content.split("\n## ")

        # 返回最近的条目
        return entries[-limit:] if len(entries) > 1 else []

    async def _append_memory(self, dialog_id: str, summary: str) -> None:
        """追加记忆到文件"""
        timestamp = datetime.now().isoformat()
        entry = f"""\n## {timestamp} - Dialog {dialog_id}\n\n{summary}\n"""

        with open(self._memory_file, "a", encoding="utf-8") as f:
            f.write(entry)

    def _format_history(self, messages: list[dict]) -> str:
        """格式化消息历史"""
        lines = []
        for m in messages[-20:]:  # 最近20条
            role = "用户" if m["role"] == "user" else "助手"
            content = m.get("content", "")[:300]
            lines.append(f"{role}：{content}")
        return "\n".join(lines)
```

### 2.4 AgentOrchestrationService - Agent 编排服务

```python
# core/application/services/agent_orchestration_service.py
from typing import AsyncIterator, Optional
from dataclasses import dataclass

from core.application.services.dialog_service import DialogService
from core.application.services.skill_service import SkillService
from core.application.services.memory_service import MemoryService
from core.runtime.interfaces import IAgentRuntime


@dataclass
class ChatRequest:
    """聊天请求"""
    dialog_id: Optional[str]
    user_input: str
    stream: bool = True
    use_memory: bool = True
    skill_ids: Optional[list[str]] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    dialog_id: str
    message_id: str
    content: str
    tool_calls: list[dict]
    tokens_used: int


class AgentOrchestrationService:
    """
    Agent 编排服务 - 高层业务用例

    职责:
    - 协调多个 Service 完成复杂用例
    - 处理对话、技能、记忆的整合
    - 提供简化的统一入口

    这是最高层的 Service，面向具体业务场景。
    """

    def __init__(
        self,
        dialog_service: DialogService,
        skill_service: SkillService,
        memory_service: MemoryService,
        runtime: IAgentRuntime
    ):
        self._dialog_svc = dialog_service
        self._skill_svc = skill_service
        self._memory_svc = memory_service
        self._runtime = runtime

    async def chat(
        self,
        request: ChatRequest
    ) -> AsyncIterator[str]:
        """
        统一聊天用例

        流程:
        1. 创建或获取对话
        2. 加载相关技能
        3. 注入相关记忆
        4. 发送消息并流式返回
        5. 保存总结（如对话结束）
        """
        # 1. 创建或获取对话
        if not request.dialog_id:
            result = await self._dialog_svc.create_dialog(
                user_input=request.user_input
            )
            dialog_id = result.dialog_id
        else:
            dialog_id = request.dialog_id

        # 2. 加载技能（如果指定）
        if request.skill_ids:
            for skill_id in request.skill_ids:
                # 确保技能已加载
                await self._skill_svc.activate_skill(skill_id)

        # 3. 发送消息
        async for chunk in self._dialog_svc.send_message(
            dialog_id=dialog_id,
            content=request.user_input,
            stream=request.stream
        ):
            yield chunk

        # 4. 生成总结（对话结束后异步进行）
        if request.use_memory:
            # 异步生成总结，不阻塞响应
            asyncio.create_task(
                self._generate_summary(dialog_id)
            )

    async def _generate_summary(self, dialog_id: str) -> None:
        """异步生成对话总结"""
        try:
            dialog = await self._dialog_svc.get_dialog(dialog_id)
            if dialog:
                await self._memory_svc.summarize_dialog(dialog)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
```

## 3. Repository 接口设计

```python
# core/domain/repositories/dialog_repository.py
from abc import ABC, abstractmethod
from typing import Optional

from core.domain.entities.dialog import Dialog


class IDialogRepository(ABC):
    """对话仓库接口"""

    @abstractmethod
    async def save(self, dialog: Dialog) -> None:
        """保存对话"""
        pass

    @abstractmethod
    async def get(self, dialog_id: str) -> Optional[Dialog]:
        """获取对话"""
        pass

    @abstractmethod
    async def list_all(self) -> list[Dialog]:
        """列出所有对话"""
        pass

    @abstractmethod
    async def delete(self, dialog_id: str) -> None:
        """删除对话"""
        pass


# core/infrastructure/persistence/memory/dialog_repo.py
class InMemoryDialogRepository(IDialogRepository):
    """内存对话仓库实现"""

    def __init__(self):
        self._dialogs: dict[str, Dialog] = {}

    async def save(self, dialog: Dialog) -> None:
        self._dialogs[dialog.id] = dialog

    async def get(self, dialog_id: str) -> Optional[Dialog]:
        return self._dialogs.get(dialog_id)

    async def list_all(self) -> list[Dialog]:
        return list(self._dialogs.values())

    async def delete(self, dialog_id: str) -> None:
        self._dialogs.pop(dialog_id, None)
```

## 4. 依赖注入配置

```python
# core/container.py
from core.container import Container

# 注册 Repository
container.register(
    IDialogRepository,
    InMemoryDialogRepository(),
    scope="singleton"
)

# 注册 Service
container.register(
    DialogService,
    lambda: DialogService(
        dialog_repo=container.resolve(IDialogRepository),
        event_bus=container.resolve(IEventBus),
        runtime=container.resolve(IAgentRuntime)
    ),
    scope="singleton"
)

# 注册 Facade (兼容层)
container.register(
    AgentEngine,
    lambda: AgentEngine(
        dialog_service=container.resolve(DialogService),
        skill_service=container.resolve(SkillService)
    ),
    scope="singleton"
)
```

## 5. 与现有 Manager 的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface 层                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ AgentEngine (Facade - 保持兼容)                      │   │
│  │  - 内部委托给 Service                                │   │
│  └─────────────────────┬───────────────────────────────┘   │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application Service 层                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │DialogService │  │SkillService  │  │AgentOrchestration│  │
│  │  - 对话用例   │  │  - 技能用例   │  │  - 复杂场景编排   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Manager 层 (保留)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │DialogManager │  │SkillManager  │  │ToolManager       │  │
│  │  - 状态管理   │  │  - 工具注册   │  │  - 工具执行       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Repository 层 (新增)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ IDialogRepository / ISkillRepository                │   │
│  └─────────────────────┬───────────────────────────────┘   │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain 层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │Dialog        │  │Message       │  │Skill             │  │
│  │  - 领域实体   │  │  - 领域实体   │  │  - 领域实体       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 6. 迁移策略

### 阶段 1: 创建 Repository 层
1. 定义 `IDialogRepository` 接口
2. 实现 `InMemoryDialogRepository`
3. 让 `DialogManager` 使用 Repository

### 阶段 2: 创建 Service 层
1. 实现 `DialogService`
2. 初始版本内部调用 `DialogManager`
3. 保持 `AgentEngine` 行为不变

### 阶段 3: 重构 AgentEngine
1. 让 `AgentEngine` 委托给 `DialogService`
2. 逐步将业务逻辑移到 Service
3. 添加测试验证

### 阶段 4: 清理
1. 将 `DialogManager` 标记为内部使用
2. 删除 `AgentEngine` 中的重复逻辑
3. 更新文档
