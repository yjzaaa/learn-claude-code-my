"""
Memory Manager - 记忆管理器

每次对话结束时，将对话上下文用 LLM 总结为一条带时间戳的重要信息，
追加写入 memory.md，供后续对话注入 system prompt。
"""

from typing import Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

from runtime.event_bus import EventBus
from core.models.config import MemoryConfig
from core.models.api import MemoryStats
from core.models.types import MessageDict

logger = logging.getLogger(__name__)

_SUMMARIZE_PROMPT = """\
请将以下对话历史总结为一条简短的重要信息（不超过200字），
只保留对未来对话有参考价值的事实、用户偏好或决策结论。
用中文输出，不要使用列表，直接描述。

对话历史：
{history}
"""


class MemoryManager:
    """
    记忆管理器

    职责：
    - 对话结束时，调用 LLM 总结对话，追加写入 memory.md
    - 启动时读取 memory.md，注入 system prompt 作为长期记忆背景
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        config: MemoryConfig | None = None,
        memory_file: str = "memory.md",
    ):
        self._config = config or MemoryConfig()
        self._memory_file = Path(memory_file)

        # 确保文件存在
        if not self._memory_file.exists():
            self._memory_file.write_text("# Agent Memory\n\n", encoding="utf-8")

    # ─────────────────────────────────────────────
    # 写入：对话结束后总结并追加
    # ─────────────────────────────────────────────

    async def summarize_and_store(
        self,
        dialog_id: str,
        messages: list[MessageDict],
        provider: Any = None,
    ) -> str | None:
        """
        总结一次对话并追加到 memory.md。

        Args:
            dialog_id: 对话 ID（仅用于日志）
            messages:  对话消息列表（OpenAI 格式）
            provider:  LLM provider 实例；为 None 时做简单文本摘取

        Returns:
            写入的摘要文本，或 None（无内容可总结时）
        """
        # 过滤出用户/助手消息，跳过 system / tool
        turns = [
            m for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        if not turns:
            return None

        if provider:
            summary = await self._llm_summarize(turns, provider)
        else:
            summary = self._simple_summarize(turns)

        if not summary:
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## [{timestamp}]\n{summary}\n"
        self._memory_file.open("a", encoding="utf-8").write(entry)

        logger.info("[MemoryManager] Stored summary for dialog %s", dialog_id)
        return summary

    # ─────────────────────────────────────────────
    # 读取：注入 system prompt
    # ─────────────────────────────────────────────

    def load_memory(self) -> str:
        """读取 memory.md 内容，供 system prompt 使用。"""
        try:
            return self._memory_file.read_text(encoding="utf-8")
        except OSError:
            return ""

    # ─────────────────────────────────────────────
    # 内部实现
    # ─────────────────────────────────────────────

    async def _llm_summarize(self, turns: list[MessageDict], provider: Any) -> str:
        """调用 LLM 总结对话。"""
        history_lines = []
        for m in turns[-20:]:  # 最多取最近 20 条
            role = "用户" if m["role"] == "user" else "助手"
            content = (m.get("content") or "")[:300]
            history_lines.append(f"{role}：{content}")

        prompt = _SUMMARIZE_PROMPT.format(history="\n".join(history_lines))

        result: list[str] = []
        async for chunk in provider.chat_stream(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
        ):
            if chunk.is_content and chunk.content:
                result.append(chunk.content)

        return "".join(result).strip()

    def _simple_summarize(self, turns: list[MessageDict]) -> str:
        """无 LLM 时的简单摘取：取最后一条用户消息。"""
        for m in reversed(turns):
            if m.get("role") == "user" and m.get("content"):
                content = (m["content"] or "")[:200]
                return f"用户提问：{content}"
        return ""

    def get_stats(self) -> MemoryStats:
        """获取统计信息。"""
        lines = self.load_memory().splitlines()
        entries = sum(1 for l in lines if l.startswith("## ["))
        return MemoryStats(
            short_term_dialogs=0,
            short_term_entries=0,
            long_term_entries=entries,
            summaries=entries,
        )
