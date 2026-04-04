"""
MemoryService - 记忆应用服务

职责:
- 对话总结生成
- 长期记忆管理
- 记忆注入上下文
"""

from typing import Optional, List
from datetime import datetime
from pathlib import Path

from backend.domain.models import Dialog
from backend.application.dto.responses import MemorySummary


class MemoryService:
    """记忆应用服务

    提供对话总结和长期记忆管理功能。

    Attributes:
        _llm_provider: LLM 提供者接口
        _memory_file: 记忆文件路径
    """

    def __init__(
        self,
        llm_provider,
        memory_file: Path = Path("memory.md")
    ):
        """初始化 MemoryService

        Args:
            llm_provider: 实现 ILLMProvider 接口的对象
            memory_file: 记忆文件路径（默认 "memory.md"）
        """
        self._llm = llm_provider
        self._memory_file = memory_file

    async def summarize_dialog(self, dialog: Dialog) -> str:
        """总结单个对话

        流程:
        1. 提取关键消息
        2. 调用 LLM 生成总结
        3. 格式化输出
        4. 保存到记忆文件

        Args:
            dialog: 对话实体

        Returns:
            str: 生成的总结文本
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
        try:
            async for chunk in self._llm.chat_stream(
                messages=[{"role": "user", "content": prompt}]
            ):
                if hasattr(chunk, 'content') and chunk.content:
                    summary_parts.append(chunk.content)
                elif isinstance(chunk, str):
                    summary_parts.append(chunk)
        except Exception:
            # LLM 调用失败时返回简单总结
            return f"对话 {dialog.id} 总结生成失败"

        summary = "".join(summary_parts).strip()

        # 3. 保存到记忆文件
        await self._append_memory(dialog.id, summary)

        return summary

    async def get_relevant_memories(
        self,
        query: str,
        limit: int = 3
    ) -> List[str]:
        """获取与查询相关的记忆

        简化实现：返回最近的记忆
        未来可接入向量搜索

        Args:
            query: 查询文本
            limit: 返回记忆数量上限

        Returns:
            List[str]: 记忆内容列表
        """
        if not self._memory_file.exists():
            return []

        try:
            content = self._memory_file.read_text(encoding="utf-8")
            entries = content.split("\n## ")

            # 返回最近的条目
            if len(entries) > 1:
                return entries[-limit:]
            return [content] if content else []
        except Exception:
            return []

    async def get_memory_summary(self) -> Optional[MemorySummary]:
        """获取记忆摘要

        Returns:
            MemorySummary: 记忆摘要，无记忆时返回 None
        """
        if not self._memory_file.exists():
            return None

        try:
            content = self._memory_file.read_text(encoding="utf-8")
            entries = content.split("\n## ")

            return MemorySummary(
                content=content[:500] + "..." if len(content) > 500 else content,
                created_at=datetime.fromtimestamp(
                    self._memory_file.stat().st_mtime
                ),
                dialog_count=len(entries) - 1 if len(entries) > 1 else 1,
            )
        except Exception:
            return None

    async def clear_memories(self) -> bool:
        """清空所有记忆

        Returns:
            bool: 是否成功清空
        """
        try:
            if self._memory_file.exists():
                self._memory_file.unlink()
            return True
        except Exception:
            return False

    async def _append_memory(self, dialog_id: str, summary: str) -> None:
        """追加记忆到文件

        Args:
            dialog_id: 对话 ID
            summary: 总结内容
        """
        timestamp = datetime.now().isoformat()
        entry = f"""\n## {timestamp} - Dialog {dialog_id}\n\n{summary}\n"""

        with open(self._memory_file, "a", encoding="utf-8") as f:
            f.write(entry)

    def _format_history(self, messages: List[dict]) -> str:
        """格式化消息历史

        Args:
            messages: 消息字典列表

        Returns:
            str: 格式化后的历史文本
        """
        lines = []
        for m in messages[-20:]:  # 最近20条
            role = m.get("role", "unknown")
            content = m.get("content", "")[:300]
            role_cn = "用户" if role == "user" else "助手" if role == "assistant" else role
            lines.append(f"{role_cn}：{content}")
        return "\n".join(lines)
