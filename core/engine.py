"""
AgentEngine - Agent 核心引擎 (Facade)

基于 Hanako 架构设计思想的门面模式实现。
所有外部交互都通过此类，内部委托给各 Manager。
"""

from typing import Optional, AsyncIterator, Callable, Coroutine, Dict, Any, List
import logging
import os

from runtime.event_bus import EventBus
from core.managers.dialog_manager import DialogManager
from core.managers.tool_manager import ToolManager
from core.managers.state_manager import StateManager
from core.managers.provider_manager import ProviderManager
from core.managers.memory_manager import MemoryManager
from core.managers.skill_manager import SkillManager
from core.models.dialog import Dialog, Message
from core.models.domain import Skill
from core.models.events import SystemStarted, SystemStopped, ErrorOccurred, AgentRoundsLimitReached
from core.models.config import EngineConfig
from core.models.dto import DecisionResult, TodoStateDTO
from core.models.tool import ToolInfo
from core.models.types import StreamToolCallDict, MessageDict, ToolCallDict, ToolCallFunctionDict, JSONSchema
from core.tools import WorkspaceOps
from core.hitl import (
    skill_edit_hitl_store,
    todo_store,
    is_skill_edit_hitl_enabled,
    is_todo_hook_enabled,
)
from core.plugins import PluginManager, CompactPlugin

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    Agent 核心引擎 - Facade 模式
    
    职责:
    - 统一入口，封装内部复杂性
    - 协调各 Manager 工作
    - 提供高级 API 供 Interface 层调用
    
    使用示例:
        engine = AgentEngine(config)
        await engine.startup()
        
        # 创建对话
        dialog_id = await engine.create_dialog("Hello")
        
        # 发送消息
        async for chunk in engine.send_message(dialog_id, "How are you?"):
            print(chunk)
        
        await engine.shutdown()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化引擎

        Args:
            config: 配置字典或 EngineConfig
        """
        if isinstance(config, EngineConfig):
            self._config_obj = config
        else:
            self._config_obj = EngineConfig.from_dict(config)
        self._config = config or {}  # 保持向后兼容

        # ═══════════════════════════════════════════════════
        # 初始化基础设施
        # ═══════════════════════════════════════════════════

        # 事件总线 (核心解耦机制)
        self._event_bus = EventBus()

        # ═══════════════════════════════════════════════════
        # 初始化 Managers (依赖注入)
        # ═══════════════════════════════════════════════════

        # 状态管理器
        self._state_mgr = StateManager(
            config=self._config_obj.state
        )

        # Provider 管理器
        self._provider_mgr = ProviderManager(
            config=self._config_obj.provider
        )

        # 对话管理器
        self._dialog_mgr = DialogManager(
            event_bus=self._event_bus,
            state_manager=self._state_mgr,
            config=self._config_obj.dialog
        )

        # 工具管理器
        self._tool_mgr = ToolManager(
            event_bus=self._event_bus,
            config=self._config_obj.tools
        )

        # 记忆管理器
        self._memory_mgr = MemoryManager(
            event_bus=self._event_bus,
            config=self._config_obj.memory
        )
        
        # 技能管理器
        self._skill_mgr = SkillManager(
            event_bus=self._event_bus,
            tool_manager=self._tool_mgr,
            config=self._config_obj.skills
        )
        
        # 插件管理器
        self._plugin_mgr = PluginManager(self._event_bus)
        
        # 注册默认插件
        self._plugin_mgr.register(CompactPlugin)
        
        # 注册插件工具
        for tool in self._plugin_mgr.get_all_tools():
            spec = getattr(tool, "__tool_spec__", {})
            self._tool_mgr.register(
                name=spec.get("name", getattr(tool, "__name__", "")),
                handler=tool,
                description=spec.get("description", ""),
                parameters=spec.get("parameters", {})
            )
        
        logger.info("[AgentEngine] Initialized with all managers and plugins")
    
    # ═══════════════════════════════════════════════════════════
    # 对话管理 API (代理给 DialogManager)
    # ═══════════════════════════════════════════════════════════
    
    async def create_dialog(self, user_input: str, title: Optional[str] = None) -> str:
        """
        创建新对话
        
        Args:
            user_input: 用户初始输入
            title: 对话标题 (可选)
            
        Returns:
            对话 ID
        """
        dialog_id = await self._dialog_mgr.create(user_input, title)
        return dialog_id
    
    async def send_message(
        self,
        dialog_id: str,
        message: str,
        stream: bool = True,
        message_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        发送消息，返回流式响应
        
        Args:
            dialog_id: 对话 ID
            message: 消息内容
            stream: 是否流式返回
            
        Yields:
            响应文本片段
        """
        # 添加用户消息
        await self._dialog_mgr.add_user_message(dialog_id, message)
        
        # 获取 Provider
        provider = self._provider_mgr.default
        if not provider:
            yield "Error: No provider available"
            return
        
        # 获取消息历史
        messages = self._dialog_mgr.get_messages_for_llm(dialog_id)

        # 先构建系统提示词 (触发 skill 懒加载，注册工具)
        system_prompt = self._build_system_prompt()
        if system_prompt:
            messages.insert(0, MessageDict(role="system", content=system_prompt))

        # 懒加载完成后再获取工具列表 (包含 skill 注册的工具)
        tools = self._tool_mgr.get_schemas()
        
        try:
            from core.models.dialog import ToolCall
            import json

            _max_rounds_env = os.getenv("MAX_AGENT_ROUNDS", "").strip()
            max_rounds = int(_max_rounds_env) if _max_rounds_env.isdigit() else None

            _round = 0
            while max_rounds is None or _round < max_rounds:
                _round += 1
                full_response: list[str] = []
                tool_calls_in_round: list[StreamToolCallDict] = []

                async for chunk in provider.chat_stream(
                    messages=messages,
                    tools=tools if tools else None
                ):
                    if chunk.is_content:
                        full_response.append(chunk.content)
                        if stream:
                            yield chunk.content

                    elif chunk.is_tool_call and chunk.tool_call is not None:
                        tool_calls_in_round.append(chunk.tool_call)

                assistant_text = "".join(full_response)

                if not tool_calls_in_round:
                    # 没有工具调用，对话自然结束
                    break

                # 检查是否已到达轮次上限（本轮还有工具调用但不再继续）
                if max_rounds is not None and _round >= max_rounds:
                    logger.warning(
                        "[AgentEngine] dialog=%s reached MAX_AGENT_ROUNDS=%d, stopping",
                        dialog_id, max_rounds,
                    )
                    self._event_bus.emit(AgentRoundsLimitReached(
                        dialog_id=dialog_id,
                        rounds=_round,
                    ))
                    notice = f"\n\n⚠️ Agent 已达到最大轮次限制（{max_rounds} 轮），任务中止。"
                    if stream:
                        yield notice
                    assistant_text += notice
                    break

                # 将 assistant 的工具调用决策追加到 messages
                messages.append(MessageDict(
                    role="assistant",
                    content=assistant_text or "",
                    tool_calls=[
                        ToolCallDict(
                            id=tc.get("id", f"call_{i}"),
                            type="function",
                            function=ToolCallFunctionDict(
                                name=tc["name"],
                                arguments=json.dumps(tc["arguments"])
                                    if isinstance(tc["arguments"], dict)
                                    else tc["arguments"],
                            ),
                        )
                        for i, tc in enumerate(tool_calls_in_round)
                    ],
                ))

                # 执行所有工具调用，把结果作为 tool 消息追加
                for tc in tool_calls_in_round:
                    tool_call = ToolCall.create(
                        name=tc["name"],
                        arguments=tc["arguments"],
                    )
                    result = await self._tool_mgr.execute(dialog_id, tool_call)
                    messages.append(MessageDict(
                        role="tool",
                        tool_call_id=tc.get("id", "call_0"),
                        content=str(result),
                    ))
                    logger.info("[AgentEngine] Tool %s → %s", tc["name"], str(result)[:200])

            # 保存最终助手响应
            await self._dialog_mgr.add_assistant_message(
                dialog_id, assistant_text, message_id=message_id
            )

            if not stream:
                yield assistant_text

        except Exception as e:
            logger.exception(f"[AgentEngine] Error in send_message: {e}")
            self._event_bus.emit(ErrorOccurred(
                error_type=type(e).__name__,
                error_message=str(e),
                dialog_id=dialog_id
            ))
            yield f"Error: {e}"
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        parts = []

        # 基础提示词
        parts.append("You are a helpful AI assistant.")

        # 注入长期记忆
        memory = self._memory_mgr.load_memory()
        if memory and memory.strip() != "# Agent Memory":
            parts.append("\n# Long-term Memory\n" + memory)

        # 添加技能提示词
        skill_prompts = []
        for skill in self._skill_mgr.list_skills():
            prompt = self._skill_mgr.get_skill_prompt(skill.id)
            if prompt:
                skill_prompts.append(f"[{skill.name}]\n{prompt}")
        
        if skill_prompts:
            parts.append("\nActive skills:")
            parts.append("\n\n".join(skill_prompts))
        
        return "\n".join(parts)
    
    def get_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """
        获取对话状态
        
        Args:
            dialog_id: 对话 ID
            
        Returns:
            对话实例或 None
        """
        return self._dialog_mgr.get(dialog_id)
    
    def list_dialogs(self) -> List[Dialog]:
        """
        列出所有对话
        
        Returns:
            对话列表
        """
        return self._dialog_mgr.list_dialogs()
    
    async def close_dialog(self, dialog_id: str, reason: str = "completed"):
        """
        关闭对话
        
        Args:
            dialog_id: 对话 ID
            reason: 关闭原因
        """
        # 总结并写入 memory.md
        messages = self._dialog_mgr.get_messages_for_llm(dialog_id)
        provider = self._provider_mgr.default
        await self._memory_mgr.summarize_and_store(dialog_id, messages, provider)

        # 关闭对话
        await self._dialog_mgr.close(dialog_id, reason)
    
    # ═══════════════════════════════════════════════════════════
    # 工具管理 API (代理给 ToolManager)
    # ═══════════════════════════════════════════════════════════
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Optional[JSONSchema] = None
    ):
        """
        注册工具

        Args:
            name: 工具名称
            handler: 处理函数
            description: 描述
            parameters: 参数定义
        """
        self._tool_mgr.register(name, handler, description, parameters)
    
    def list_tools(self) -> List[ToolInfo]:
        """
        列出可用工具
        
        Returns:
            工具信息列表
        """
        return self._tool_mgr.list_available()
    
    # ═══════════════════════════════════════════════════════════
    # 技能管理 API (代理给 SkillManager)
    # ═══════════════════════════════════════════════════════════
    
    def load_skill(self, skill_path: str) -> Optional[Skill]:
        """
        加载技能
        
        Args:
            skill_path: 技能目录路径
            
        Returns:
            技能实例或 None
        """
        return self._skill_mgr.load_skill_from_directory(skill_path)
    
    def list_skills(self) -> List[Skill]:
        """
        列出所有技能
        
        Returns:
            技能列表
        """
        return self._skill_mgr.list_skills()
    
    # ═══════════════════════════════════════════════════════════
    # 记忆管理 API (代理给 MemoryManager)
    # ═══════════════════════════════════════════════════════════
    
    def get_memory(self) -> str:
        """读取 memory.md 内容"""
        return self._memory_mgr.load_memory()
    
    # ═══════════════════════════════════════════════════════════
    # 事件订阅 API (代理给 EventBus)
    # ═══════════════════════════════════════════════════════════
    
    def subscribe(
        self,
        callback: Callable,
        event_types: Optional[List[str]] = None,
        dialog_id: Optional[str] = None
    ) -> Callable:
        """
        订阅事件
        
        Args:
            callback: 回调函数
            event_types: 事件类型列表
            dialog_id: 特定对话 ID
            
        Returns:
            取消订阅函数
        """
        return self._event_bus.subscribe(callback, event_types, dialog_id)
    
    def emit(self, event: Any):
        """
        发射事件
        
        Args:
            event: 事件对象
        """
        self._event_bus.emit(event)
    
    # ═══════════════════════════════════════════════════════════
    # 生命周期管理
    # ═══════════════════════════════════════════════════════════
    
    async def startup(self):
        """启动引擎"""
        await self._state_mgr.load()
        self._skill_mgr.load_builtin_skills()
        self._event_bus.emit(SystemStarted())
        logger.info("[AgentEngine] Startup complete")
    
    async def shutdown(self):
        """关闭引擎"""
        await self._state_mgr.save()
        self._event_bus.emit(SystemStopped())
        self._event_bus.shutdown()
        logger.info("[AgentEngine] Shutdown complete")
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._event_bus.is_running
    
    # ═══════════════════════════════════════════════════════════
    # 快速设置
    # ═══════════════════════════════════════════════════════════
    
    def setup_workspace_tools(self, workdir: Any):
        """
        快速设置工作区工具
        
        Args:
            workdir: 工作目录路径
        """
        from pathlib import Path

        workspace = WorkspaceOps(Path(workdir))
        
        for tool_fn in workspace.get_tools():
            spec = getattr(tool_fn, "__tool_spec__", {})
            self.register_tool(
                name=spec.get("name", getattr(tool_fn, "__name__", "")),
                handler=tool_fn,
                description=spec.get("description", ""),
                parameters=spec.get("parameters", {})
            )
        
        logger.info(f"[AgentEngine] Setup workspace tools from {workdir}")
    
    # ═══════════════════════════════════════════════════════════
    # 内部访问 (供高级用例使用)
    # ═══════════════════════════════════════════════════════════
    
    @property
    def event_bus(self) -> EventBus:
        """事件总线 (高级用例)"""
        return self._event_bus
    
    @property
    def dialog_manager(self) -> DialogManager:
        """对话管理器 (高级用例)"""
        return self._dialog_mgr
    
    @property
    def tool_manager(self) -> ToolManager:
        """工具管理器 (高级用例)"""
        return self._tool_mgr
    
    @property
    def memory_manager(self) -> MemoryManager:
        """记忆管理器 (高级用例)"""
        return self._memory_mgr
    
    @property
    def skill_manager(self) -> SkillManager:
        """技能管理器 (高级用例)"""
        return self._skill_mgr
    
    @property
    def plugin_manager(self) -> PluginManager:
        """插件管理器 (高级用例)"""
        return self._plugin_mgr
    
    # ═══════════════════════════════════════════════════════════
    # HITL API
    # ═══════════════════════════════════════════════════════════
    
    # Skill Edit HITL
    def get_skill_edit_proposals(self, dialog_id: Optional[str] = None) -> list[dict]:
        """获取待处理的 Skill 编辑提案"""
        if not is_skill_edit_hitl_enabled():
            return []
        return skill_edit_hitl_store.list_pending(dialog_id)
    
    def decide_skill_edit(self, approval_id: str, decision: str, edited_content: Optional[str] = None) -> DecisionResult:
        """处理 Skill 编辑审核决定"""
        if not is_skill_edit_hitl_enabled():
            return DecisionResult(success=False, message="HITL disabled")
        return skill_edit_hitl_store.decide(approval_id, decision, edited_content)
    
    # Todo HITL
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
    
    def register_hitl_broadcaster(self, broadcaster: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]):
        """注册 HITL 广播器"""
        if is_skill_edit_hitl_enabled():
            skill_edit_hitl_store.register_broadcaster(broadcaster)
        if is_todo_hook_enabled():
            todo_store.register_broadcaster(broadcaster)