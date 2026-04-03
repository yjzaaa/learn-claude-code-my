"""
对话管理相关功能的 Mixin
"""

from typing import Any, AsyncIterator
import logging
import os

from core.models.entities import Dialog
from core.models.events import AgentRoundsLimitReached, ErrorOccurred
from core.models.entities import ToolCall
from core.models.types import StreamToolCallDict, MessageDict, ToolCallDict, ToolCallFunctionDict
from .base import EngineMixinBase

logger = logging.getLogger(__name__)


class DialogMixin(EngineMixinBase):
    """对话管理功能"""

    async def create_dialog(self, user_input: str, title: str | None = None) -> str:
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
        message_id: str | None = None,
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
            # ToolCall 已在顶部导入
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

    def get_dialog(self, dialog_id: str) -> Dialog | None:
        """
        获取对话状态

        Args:
            dialog_id: 对话 ID

        Returns:
            对话实例或 None
        """
        return self._dialog_mgr.get(dialog_id)

    def list_dialogs(self) -> list[Dialog]:
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

    @property
    def dialog_manager(self) -> "Any":
        """对话管理器 (高级用例)"""
        return self._dialog_mgr
