"""压缩策略实现

实现 Claude Code 的 4 层压缩机制：
1. Micro Compact - 缓存编辑删除旧工具结果
2. Auto Compact - Token 阈值自动触发压缩
3. Partial Compact - 智能保留关键内容
4. Session Memory - 跨会话持久化
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
from datetime import datetime, UTC
import json
import logging
from pathlib import Path

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
    SystemMessage,
    AnyMessage,
)
from langchain_core.messages.utils import count_tokens_approximately

from .types import (
    CompressionEvent,
    MicroCompactConfig,
    AutoCompactConfig,
    PartialCompactConfig,
    SessionMemoryConfig,
)

logger = logging.getLogger(__name__)


class CompressionStrategy(ABC):
    """压缩策略基类"""

    def __init__(self, config: Any):
        self.config = config
        self.token_counter: Callable[[list[AnyMessage]], int] = count_tokens_approximately

    @abstractmethod
    def should_compact(self, messages: list[AnyMessage], **kwargs) -> bool:
        """判断是否应该执行压缩"""
        pass

    @abstractmethod
    def compact(
        self, messages: list[AnyMessage], **kwargs
    ) -> tuple[list[AnyMessage], CompressionEvent]:
        """执行压缩，返回压缩后的消息和事件记录"""
        pass

    def _count_tokens(self, messages: list[AnyMessage]) -> int:
        """计算消息列表的 token 数"""
        try:
            return self.token_counter(messages)
        except Exception:
            # 降级：粗略估算
            return sum(len(str(m.content)) // 4 for m in messages)


class MicroCompactStrategy(CompressionStrategy):
    """微压缩策略

    Claude Code 的 Micro Compact 实现：
    - 使用 cache_edits 删除旧的工具结果
    - 或直接将旧工具结果替换为占位符
    - 保留最近 N 轮的工具结果

    对应 Claude Code: src/services/compact/microCompact.ts
    """

    def __init__(self, config: MicroCompactConfig):
        super().__init__(config)
        self.config: MicroCompactConfig = config

    def should_compact(self, messages: list[AnyMessage], **kwargs) -> bool:
        """检查是否有旧工具结果需要清理"""
        tool_results = self._get_tool_results(messages)
        # 如果工具结果数量超过保留数量，需要压缩
        return len(tool_results) > self.config.keep_recent_rounds

    def compact(
        self, messages: list[AnyMessage], **kwargs
    ) -> tuple[list[AnyMessage], CompressionEvent]:
        """执行微压缩

        策略：
        1. 识别所有 ToolMessage
        2. 保留最近 N 个
        3. 将旧的 ToolMessage 内容替换为占位符或标记为 cache_delete
        """
        original_count = len(messages)
        original_tokens = self._count_tokens(messages)

        # 找到所有 ToolMessage 的索引
        tool_indices = []
        for idx, msg in enumerate(messages):
            if isinstance(msg, ToolMessage):
                tool_indices.append(idx)

        # 确定需要保留的索引（最近 N 个）
        keep_count = self.config.keep_recent_rounds
        indices_to_clear = tool_indices[:-keep_count] if len(tool_indices) > keep_count else []

        # 创建新消息列表
        compressed_messages = []
        preserved_indices = []

        for idx, msg in enumerate(messages):
            if idx in indices_to_clear:
                # 替换为占位符
                placeholder_msg = self._create_placeholder(msg)
                compressed_messages.append(placeholder_msg)
            else:
                compressed_messages.append(msg)
                preserved_indices.append(idx)

        # 创建事件记录
        event: CompressionEvent = {
            "level": "micro",
            "timestamp": datetime.now(UTC).isoformat(),
            "original_message_count": original_count,
            "compressed_message_count": len(compressed_messages),
            "original_token_count": original_tokens,
            "compressed_token_count": self._count_tokens(compressed_messages),
            "preserved_indices": preserved_indices,
            "summary": f"Replaced {len(indices_to_clear)} old tool results with placeholders",
            "file_path": None,
        }

        return compressed_messages, event

    def _get_tool_results(self, messages: list[AnyMessage]) -> list[ToolMessage]:
        """获取所有工具结果消息"""
        return [m for m in messages if isinstance(m, ToolMessage)]

    def _create_placeholder(self, original_msg: ToolMessage) -> ToolMessage:
        """创建工具结果的占位符"""
        tool_call_id = getattr(original_msg, "tool_call_id", "unknown")
        tool_name = getattr(original_msg, "name", "unknown")

        # 创建简短的占位符内容
        placeholder_content = f"[Previous: used {tool_name}]"

        # 复制原消息但替换内容
        return ToolMessage(
            content=placeholder_content,
            tool_call_id=tool_call_id,
            name=tool_name,
            # 保留其他元数据
            additional_kwargs={
                **getattr(original_msg, "additional_kwargs", {}),
                "_compacted": True,
                "_original_length": len(str(original_msg.content)),
            },
        )

    def create_cache_edits_block(
        self, messages: list[AnyMessage]
    ) -> Optional[list[dict]]:
        """创建 Anthropic cache_edits 块（如果使用 Anthropic API）

        这是 Claude Code 的原生实现方式，通过 cache_edits 删除缓存中的旧工具结果。
        注意：这需要模型支持 cache_edits 功能。
        """
        if not self.config.use_cache_edits:
            return None

        tool_results = self._get_tool_results(messages)
        if len(tool_results) <= self.config.keep_recent_rounds:
            return None

        # 生成 cache_edits 指令
        # 注意：实际使用需要与 Anthropic API 集成
        cache_edits = []
        for msg in tool_results[: -self.config.keep_recent_rounds]:
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id:
                cache_edits.append(
                    {
                        "type": "cache_delete",
                        "hash": tool_call_id,  # 使用 tool_call_id 作为标识
                    }
                )

        return cache_edits if cache_edits else None


class AutoCompactStrategy(CompressionStrategy):
    """自动压缩策略

    Claude Code 的 Auto Compact 实现：
    - 基于 token 阈值自动触发
    - 支持多种压缩策略（claude/gpt 不同处理）
    - 图像剥离、附件去重

    对应 Claude Code: src/services/compact/autoCompact.ts
    """

    def __init__(self, config: AutoCompactConfig):
        super().__init__(config)
        self.config: AutoCompactConfig = config

    def should_compact(self, messages: list[AnyMessage], **kwargs) -> bool:
        """检查是否达到压缩阈值"""
        total_tokens = self._count_tokens(messages)
        threshold = self._get_threshold(**kwargs)
        return total_tokens >= threshold

    def compact(
        self, messages: list[AnyMessage], **kwargs
    ) -> tuple[list[AnyMessage], CompressionEvent]:
        """执行自动压缩

        策略：
        1. 预处理：剥离图像、去重附件
        2. 确定 cutoff 点
        3. 生成摘要
        4. 替换旧消息
        """
        original_count = len(messages)
        original_tokens = self._count_tokens(messages)

        # 步骤 1: 预处理
        processed_messages = self._preprocess(messages)

        # 步骤 2: 确定 cutoff
        cutoff_index = self._determine_cutoff(processed_messages)

        if cutoff_index <= 0:
            # 不需要压缩
            return messages, self._create_noop_event(messages)

        # 步骤 3: 分区消息
        to_summarize = processed_messages[:cutoff_index]
        to_preserve = processed_messages[cutoff_index:]

        # 步骤 4: 生成摘要
        summary = self._create_summary(to_summarize)

        # 步骤 5: 构建新消息列表
        summary_message = HumanMessage(
            content=f"Previous conversation summary:\n{summary}",
            additional_kwargs={"_compacted_summary": True},
        )

        compressed_messages = [summary_message] + to_preserve

        # 创建事件
        event: CompressionEvent = {
            "level": "auto",
            "timestamp": datetime.now(UTC).isoformat(),
            "original_message_count": original_count,
            "compressed_message_count": len(compressed_messages),
            "original_token_count": original_tokens,
            "compressed_token_count": self._count_tokens(compressed_messages),
            "preserved_indices": list(range(cutoff_index, original_count)),
            "summary": summary,
            "file_path": None,
        }

        return compressed_messages, event

    def _get_threshold(self, **kwargs) -> int:
        """获取压缩阈值"""
        threshold_type, threshold_value = self.config.threshold

        if threshold_type == "fraction":
            # 从 kwargs 获取模型上下文窗口
            context_window = kwargs.get("context_window", 200000)  # 默认值
            return int(context_window * threshold_value)
        else:  # tokens
            return int(threshold_value)

    def _preprocess(self, messages: list[AnyMessage]) -> list[AnyMessage]:
        """预处理：剥离图像、去重"""
        processed = []
        seen_attachments = set()

        for msg in messages:
            # 剥离图像（简化实现）
            if self.config.strip_images and self._contains_image(msg):
                msg = self._strip_image(msg)

            # 去重附件
            if self.config.deduplicate_attachments:
                msg = self._deduplicate_attachments(msg, seen_attachments)

            processed.append(msg)

        return processed

    def _contains_image(self, msg: AnyMessage) -> bool:
        """检查消息是否包含图像"""
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            return any(
                isinstance(block, dict) and block.get("type") == "image" for block in content
            )
        return False

    def _strip_image(self, msg: AnyMessage) -> AnyMessage:
        """剥离图像内容"""
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            new_content = [
                block for block in content if not (isinstance(block, dict) and block.get("type") == "image")
            ]
            # 如果没有文本内容，添加占位符
            if not new_content:
                new_content = [{"type": "text", "text": "[Image removed]"}]
            return msg.__class__(content=new_content)
        return msg

    def _deduplicate_attachments(
        self, msg: AnyMessage, seen: set[str]
    ) -> AnyMessage:
        """去重附件"""
        # 简化实现：基于内容哈希去重
        return msg

    def _determine_cutoff(self, messages: list[AnyMessage]) -> int:
        """确定压缩 cutoff 点"""
        keep_type, keep_value = self.config.keep

        if keep_type == "messages":
            # 保留最近 N 条消息
            return max(0, len(messages) - int(keep_value))

        elif keep_type == "fraction":
            # 保留比例
            return max(0, int(len(messages) * (1 - keep_value)))

        else:  # tokens
            # 从后向前计算，保留指定 token 数
            target_tokens = keep_value
            tokens_kept = 0
            for i in range(len(messages) - 1, -1, -1):
                msg_tokens = self._count_tokens([messages[i]])
                if tokens_kept + msg_tokens > target_tokens:
                    return i + 1
                tokens_kept += msg_tokens
            return 0

    def _create_summary(self, messages: list[AnyMessage]) -> str:
        """生成对话摘要

        注意：这是一个简化实现。完整的实现应该：
        1. 使用 LLM 生成摘要
        2. 保留关键决策点和文件操作
        """
        # 收集关键信息
        file_operations = []
        tool_calls = []

        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(tc.get("name", "unknown"))
                    if tc.get("name") in ["write_file", "edit_file", "read_file"]:
                        args = tc.get("args", {})
                        if "path" in args or "file_path" in args:
                            file_operations.append(args.get("path") or args.get("file_path"))

        # 构建摘要
        summary_parts = []

        if file_operations:
            summary_parts.append(f"File operations: {', '.join(set(file_operations))}")

        if tool_calls:
            unique_tools = list(dict.fromkeys(tool_calls))  # 保持顺序去重
            summary_parts.append(f"Tools used: {', '.join(unique_tools[:5])}")  # 最多5个

        summary_parts.append(f"Messages: {len(messages)}")

        return "; ".join(summary_parts) if summary_parts else f"Conversation with {len(messages)} messages"

    def _create_noop_event(self, messages: list[AnyMessage]) -> CompressionEvent:
        """创建无操作事件"""
        return {
            "level": "auto",
            "timestamp": datetime.now(UTC).isoformat(),
            "original_message_count": len(messages),
            "compressed_message_count": len(messages),
            "original_token_count": self._count_tokens(messages),
            "compressed_token_count": self._count_tokens(messages),
            "preserved_indices": list(range(len(messages))),
            "summary": "No compression needed",
            "file_path": None,
        }


class PartialCompactStrategy(CompressionStrategy):
    """部分压缩策略

    Claude Code 的 Partial Compact 实现：
    - 预压缩分析，预测需要保留的内容
    - 保留关键文件内容和工具调用结果

    对应 Claude Code: src/services/compact/partialCompact.ts
    """

    def __init__(self, config: PartialCompactConfig):
        super().__init__(config)
        self.config: PartialCompactConfig = config

    def should_compact(self, messages: list[AnyMessage], **kwargs) -> bool:
        """部分压缩总是可用，但通常在 auto compact 后使用"""
        return kwargs.get("force_partial", False)

    def compact(
        self, messages: list[AnyMessage], **kwargs
    ) -> tuple[list[AnyMessage], CompressionEvent]:
        """执行部分压缩

        策略：
        1. 分析哪些内容被引用
        2. 保留关键决策点
        3. 保留文件操作上下文
        """
        original_count = len(messages)
        original_tokens = self._count_tokens(messages)

        # 分析引用关系
        referenced_indices = self._analyze_references(messages)

        # 识别关键决策点
        decision_indices = self._identify_decisions(messages)

        # 合并需要保留的索引
        preserve_indices = sorted(set(referenced_indices) | set(decision_indices))

        # 将消息分区
        preserved = [messages[i] for i in preserve_indices]
        other = [messages[i] for i in range(len(messages)) if i not in preserve_indices]

        # 对 "other" 部分生成摘要
        if other:
            summary = self._create_detailed_summary(other)
            summary_msg = HumanMessage(
                content=f"Summary of omitted context:\n{summary}",
                additional_kwargs={"_partial_summary": True},
            )
            compressed = [summary_msg] + preserved
        else:
            compressed = messages

        event: CompressionEvent = {
            "level": "partial",
            "timestamp": datetime.now(UTC).isoformat(),
            "original_message_count": original_count,
            "compressed_message_count": len(compressed),
            "original_token_count": original_tokens,
            "compressed_token_count": self._count_tokens(compressed),
            "preserved_indices": preserve_indices,
            "summary": f"Preserved {len(preserve_indices)} critical messages",
            "file_path": None,
        }

        return compressed, event

    def _analyze_references(self, messages: list[AnyMessage]) -> list[int]:
        """分析哪些消息被引用"""
        if not self.config.preserve_referenced_content:
            return []

        # 简化实现：查找引用模式
        referenced = []
        content_text = " ".join(str(m.content) for m in messages)

        for idx, msg in enumerate(messages):
            # 检查是否包含文件路径（被引用的标志）
            if isinstance(msg, (AIMessage, ToolMessage)):
                content = str(msg.content)
                # 检查后续消息是否引用此内容
                if idx < len(messages) - 1:
                    # 简化检查：看是否有唯一标识符被引用
                    pass

        return referenced

    def _identify_decisions(self, messages: list[AnyMessage]) -> list[int]:
        """识别关键决策点"""
        if not self.config.preserve_decision_points:
            return []

        decision_indices = []

        for idx, msg in enumerate(messages):
            if isinstance(msg, AIMessage):
                content = str(msg.content).lower()
                # 启发式：包含决策关键词
                decision_keywords = ["decided", "choose", "will use", "approach:", "plan:"]
                if any(kw in content for kw in decision_keywords):
                    decision_indices.append(idx)

                # 保留文件操作
                if self.config.preserve_file_operations and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get("name") in ["write_file", "edit_file"]:
                            decision_indices.append(idx)
                            break

        return decision_indices

    def _create_detailed_summary(self, messages: list[AnyMessage]) -> str:
        """创建详细摘要"""
        topics = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                topics.append(f"User asked: {str(msg.content)[:50]}...")
            elif isinstance(msg, AIMessage) and msg.tool_calls:
                tools = [tc.get("name", "unknown") for tc in msg.tool_calls]
                topics.append(f"Executed: {', '.join(tools)}")

        return "\n".join(topics[:10])  # 最多10条


class SessionMemoryStrategy(CompressionStrategy):
    """会话记忆策略

    Claude Code 的 Session Memory Compact 实现：
    - 保存完整会话状态到记忆系统
    - 支持跨会话恢复

    对应 Claude Code: src/services/compact/sessionMemoryCompact.ts
    """

    def __init__(self, config: SessionMemoryConfig):
        super().__init__(config)
        self.config: SessionMemoryConfig = config

    def should_compact(self, messages: list[AnyMessage], **kwargs) -> bool:
        """在会话结束时压缩"""
        return kwargs.get("session_ending", False)

    def compact(
        self, messages: list[AnyMessage], **kwargs
    ) -> tuple[list[AnyMessage], CompressionEvent]:
        """执行会话记忆压缩

        策略：
        1. 生成完整会话摘要
        2. 保存到记忆系统
        3. 返回简化版本用于下次会话
        """
        original_count = len(messages)
        original_tokens = self._count_tokens(messages)

        session_id = kwargs.get("session_id", "default")

        # 生成会话摘要
        session_summary = self._create_session_summary(messages)

        # 保存到记忆系统
        file_path = None
        if self.config.save_to_memory_system:
            file_path = self._save_to_backend(backend, session_id, messages, session_summary)

        # 为下次会话创建启动消息
        context_message = HumanMessage(
            content=f"Previous session context:\n{session_summary}",
            additional_kwargs={
                "_session_memory": True,
                "_session_id": session_id,
            },
        )

        # 保留最近的几条消息作为上下文
        keep_recent = 3
        recent_messages = messages[-keep_recent:] if len(messages) > keep_recent else messages

        compressed = [context_message] + recent_messages

        event: CompressionEvent = {
            "level": "session",
            "timestamp": datetime.now(UTC).isoformat(),
            "original_message_count": original_count,
            "compressed_message_count": len(compressed),
            "original_token_count": original_tokens,
            "compressed_token_count": self._count_tokens(compressed),
            "preserved_indices": list(range(max(0, original_count - keep_recent), original_count)),
            "summary": session_summary,
            "file_path": file_path,
        }

        return compressed, event

    def _create_session_summary(self, messages: list[AnyMessage]) -> str:
        """创建会话摘要"""
        # 收集关键信息
        files_accessed = []
        tasks_completed = []
        decisions_made = []

        for msg in messages:
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        name = tc.get("name", "")
                        args = tc.get("args", {})

                        if name in ["read_file", "write_file", "edit_file"]:
                            path = args.get("path") or args.get("file_path", "unknown")
                            files_accessed.append(path)

                        if name == "write_todos":
                            tasks_completed.append(str(args))

                content = str(msg.content)
                if "decided" in content.lower() or "choose" in content.lower():
                    decisions_made.append(content[:100])

        summary_parts = []

        if files_accessed:
            summary_parts.append(f"Files: {', '.join(set(files_accessed))}")
        if tasks_completed:
            summary_parts.append(f"Tasks: {len(tasks_completed)} items")
        if decisions_made:
            summary_parts.append(f"Decisions: {decisions_made[0]}")

        summary_parts.append(f"Total messages: {len(messages)}")

        return "; ".join(summary_parts)

    def _save_to_backend(
        self,
        backend,
        session_id: str,
        messages: list[AnyMessage],
        summary: str
    ) -> Optional[str]:
        """保存到 deep-agent Backend 存储系统

        使用 BackendProtocol 统一接口，支持：
        - FilesystemBackend: 本地文件系统
        - StateBackend: LangGraph 状态存储
        - DaytonaSandbox: 远程沙箱
        - 其他自定义 Backend
        """
        if not self.config.save_to_backend or backend is None:
            return None

        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"session_{session_id}_{timestamp}.json"
            file_path = f"{self.config.storage_path_prefix}/{filename}"

            # 准备会话数据
            session_data = {
                "session_id": session_id,
                "timestamp": timestamp,
                "summary": summary,
                "message_count": len(messages),
                "messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": str(msg.content)[:500],  # 截断内容
                    }
                    for msg in messages
                ],
            }

            content = json.dumps(session_data, ensure_ascii=False, indent=2)

            # 使用 Backend 写入文件
            result = backend.write(file_path, content)

            if result.error:
                logger.warning(f"Failed to save session to backend: {result.error}")
                return None

            return file_path
        except Exception as e:
            logger.warning(f"Failed to save session to backend: {e}")
            return None

    async def _asave_to_backend(
        self,
        backend,
        session_id: str,
        messages: list[AnyMessage],
        summary: str
    ) -> Optional[str]:
        """异步保存到 deep-agent Backend 存储系统"""
        if not self.config.save_to_backend or backend is None:
            return None

        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"session_{session_id}_{timestamp}.json"
            file_path = f"{self.config.storage_path_prefix}/{filename}"

            session_data = {
                "session_id": session_id,
                "timestamp": timestamp,
                "summary": summary,
                "message_count": len(messages),
                "messages": [
                    {
                        "type": msg.__class__.__name__,
                        "content": str(msg.content)[:500],
                    }
                    for msg in messages
                ],
            }

            content = json.dumps(session_data, ensure_ascii=False, indent=2)

            # 使用异步 Backend 写入
            result = await backend.awrite(file_path, content)

            if result.error:
                logger.warning(f"Failed to save session to backend: {result.error}")
                return None

            return file_path
        except Exception as e:
            logger.warning(f"Failed to save session to backend: {e}")
            return None
