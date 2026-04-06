"""
AgentOrchestrationService - Agent 编排服务

职责:
- 协调多个 Service 完成复杂用例
- 处理对话、技能、记忆的整合
- 提供简化的统一入口

这是最高层的 Service，面向具体业务场景。
"""

import asyncio
from collections.abc import AsyncIterator

from backend.application.dto.requests import ChatRequest
from backend.application.dto.responses import ChatResponse
from backend.application.services.dialog import DialogService
from backend.application.services.memory import MemoryService
from backend.application.services.skill import SkillService


class AgentOrchestrationService:
    """Agent 编排服务 - 高层业务用例

    协调 DialogService、SkillService、MemoryService
    完成复杂的业务用例，提供简化的统一入口。

    Attributes:
        _dialog_svc: 对话服务
        _skill_svc: 技能服务
        _memory_svc: 记忆服务
        _runtime: Agent 运行时
    """

    def __init__(
        self,
        dialog_service: DialogService,
        skill_service: SkillService,
        memory_service: MemoryService,
        runtime,
    ):
        """初始化 AgentOrchestrationService

        Args:
            dialog_service: DialogService 实例
            skill_service: SkillService 实例
            memory_service: MemoryService 实例
            runtime: 实现 IAgentRuntime 接口的对象
        """
        self._dialog_svc = dialog_service
        self._skill_svc = skill_service
        self._memory_svc = memory_service
        self._runtime = runtime

    async def chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """统一聊天用例

        流程:
        1. 创建或获取对话
        2. 加载相关技能
        3. 注入相关记忆
        4. 发送消息并流式返回
        5. 保存总结（如对话结束）

        Args:
            request: 聊天请求 DTO

        Yields:
            str: 流式响应内容
        """
        # 1. 创建或获取对话
        if not request.dialog_id:
            result = await self._dialog_svc.create_dialog(user_input=request.user_input)
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
            dialog_id=dialog_id, content=request.user_input, stream=request.stream
        ):
            yield chunk

        # 4. 生成总结（对话结束后异步进行）
        if request.use_memory:
            # 异步生成总结，不阻塞响应
            asyncio.create_task(self._generate_summary(dialog_id))

    async def chat_complete(self, request: ChatRequest) -> ChatResponse:
        """非流式聊天用例

        与 chat() 类似，但返回完整响应而非流式输出。

        Args:
            request: 聊天请求 DTO

        Returns:
            ChatResponse: 完整响应
        """
        # 1. 创建或获取对话
        if not request.dialog_id:
            result = await self._dialog_svc.create_dialog(user_input=request.user_input)
            dialog_id = result.dialog_id
        else:
            dialog_id = request.dialog_id

        # 2. 加载技能（如果指定）
        if request.skill_ids:
            for skill_id in request.skill_ids:
                await self._skill_svc.activate_skill(skill_id)

        # 3. 收集完整响应
        full_content = []
        async for chunk in self._dialog_svc.send_message(
            dialog_id=dialog_id,
            content=request.user_input,
            stream=False,  # 非流式
        ):
            full_content.append(chunk)

        content = "".join(full_content)

        # 4. 异步生成总结
        if request.use_memory:
            asyncio.create_task(self._generate_summary(dialog_id))

        # 5. 构建响应
        return ChatResponse(
            dialog_id=dialog_id,
            message_id="",  # 由 dialog service 生成
            content=content,
            tool_calls=[],  # 可从运行时获取
            tokens_used=0,  # 可从运行时获取
        )

    async def _generate_summary(self, dialog_id: str) -> None:
        """异步生成对话总结

        Args:
            dialog_id: 对话 ID
        """
        try:
            dialog = await self._dialog_svc.get_dialog(dialog_id)
            if dialog:
                await self._memory_svc.summarize_dialog(dialog)
        except Exception:
            # 总结生成失败不应影响主流程
            pass

    async def create_dialog_with_skills(
        self,
        user_input: str,
        skill_ids: list[str] | None = None,
        title: str | None = None,
    ) -> str:
        """创建对话并加载技能

        Args:
            user_input: 用户初始输入
            skill_ids: 要加载的技能 ID 列表
            title: 对话标题

        Returns:
            str: 新创建对话的 ID
        """
        # 1. 创建对话
        result = await self._dialog_svc.create_dialog(user_input=user_input, title=title)

        # 2. 加载技能
        if skill_ids:
            for skill_id in skill_ids:
                await self._skill_svc.activate_skill(skill_id)

        return result.dialog_id

    async def get_context_with_memories(
        self, dialog_id: str, query: str, memory_limit: int = 3
    ) -> dict:
        """获取带记忆的对话上下文

        Args:
            dialog_id: 对话 ID
            query: 查询文本（用于检索相关记忆）
            memory_limit: 记忆数量上限

        Returns:
            dict: 包含对话历史和记忆的上下文
        """
        # 1. 获取对话历史
        messages = await self._dialog_svc.get_dialog_history(dialog_id)

        # 2. 获取相关记忆
        memories = await self._memory_svc.get_relevant_memories(query=query, limit=memory_limit)

        return {
            "dialog_id": dialog_id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                }
                for m in messages
            ],
            "memories": memories,
        }
