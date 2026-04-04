"""Claude Code 压缩中间件

将 Claude Code 的 4 层压缩系统移植到 deep-agent 框架的中间件实现。

对应 Claude Code: src/services/compact/
- microCompact.ts -> MicroCompactStrategy
- autoCompact.ts -> AutoCompactStrategy
- partialCompact.ts -> PartialCompactStrategy
- sessionMemoryCompact.ts -> SessionMemoryStrategy
"""

from typing import Any, Callable, Awaitable, Optional
from datetime import datetime, UTC
import logging

from langchain.agents.middleware.types import AgentMiddleware, AgentState, ModelRequest, ModelResponse, ExtendedModelResponse
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.types import Command

from .types import (
    CompressionConfig,
    CompressionEvent,
    MicroCompactConfig,
    AutoCompactConfig,
    PartialCompactConfig,
    SessionMemoryConfig,
    DEFAULT_COMPRESSION_CONFIG,
    MICRO_ONLY_CONFIG,
    AGGRESSIVE_CONFIG,
    CONSERVATIVE_CONFIG,
)
from .compression_strategies import (
    MicroCompactStrategy,
    AutoCompactStrategy,
    PartialCompactStrategy,
    SessionMemoryStrategy,
)

logger = logging.getLogger(__name__)


class CompressionState(AgentState):
    """压缩中间件状态"""
    _compression_events: list[CompressionEvent]
    _last_compaction_time: Optional[str]
    _original_message_count: int


class ClaudeCompressionMiddleware(AgentMiddleware):
    """Claude Code 风格的压缩中间件

    实现 4 层渐进式压缩：
    1. Micro: 每轮静默清理旧工具结果
    2. Auto: Token 阈值触发自动压缩
    3. Partial: 智能保留关键内容
    4. Session: 跨会话持久化

    使用示例:
        # 默认配置（启用 micro + auto）
        middleware = ClaudeCompressionMiddleware()

        # 仅微压缩
        middleware = ClaudeCompressionMiddleware.preset_micro_only()

        # 激进压缩（启用所有层级）
        middleware = ClaudeCompressionMiddleware.preset_aggressive()

        # 自定义配置
        middleware = ClaudeCompressionMiddleware(
            config=CompressionConfig(
                enable_micro_compact=True,
                enable_auto_compact=True,
                enable_partial_compact=False,
                enable_session_memory=False,
                auto=AutoCompactConfig(
                    threshold=("fraction", 0.75),
                    keep=("fraction", 0.25),
                ),
            )
        )

        # 添加到 Agent
        agent = (
            AgentBuilder()
            .with_model("claude-sonnet-4-6")
            .add_middleware(middleware)
            .build()
        )
    """

    state_schema = CompressionState

    def __init__(
        self,
        config: Optional[CompressionConfig] = None,
        auto_compact_threshold: float = 0.7,
        enable_micro_compact: bool = True,
        enable_auto_compact: bool = True,
        enable_partial_compact: bool = False,
        enable_session_memory: bool = False,
    ):
        """初始化压缩中间件

        Args:
            config: 完整配置对象（优先级最高）
            auto_compact_threshold: 自动压缩阈值（上下文窗口比例）
            enable_micro_compact: 启用微压缩
            enable_auto_compact: 启用自动压缩
            enable_partial_compact: 启用部分压缩
            enable_session_memory: 启用会话记忆
        """
        super().__init__()

        # 使用提供的配置或构建配置
        if config is not None:
            self.config = config
        else:
            self.config = CompressionConfig(
                enable_micro_compact=enable_micro_compact,
                enable_auto_compact=enable_auto_compact,
                enable_partial_compact=enable_partial_compact,
                enable_session_memory=enable_session_memory,
            )
            # 更新 auto 阈值
            if enable_auto_compact:
                self.config.auto.threshold = ("fraction", auto_compact_threshold)

        # 初始化策略
        self._init_strategies()

        logger.debug(
            f"ClaudeCompressionMiddleware initialized: "
            f"micro={self.config.enable_micro_compact}, "
            f"auto={self.config.enable_auto_compact}, "
            f"partial={self.config.enable_partial_compact}, "
            f"session={self.config.enable_session_memory}"
        )

    def _init_strategies(self) -> None:
        """初始化压缩策略"""
        self.micro_strategy = MicroCompactStrategy(self.config.micro)
        self.auto_strategy = AutoCompactStrategy(self.config.auto)
        self.partial_strategy = PartialCompactStrategy(self.config.partial)
        self.session_strategy = SessionMemoryStrategy(self.config.session)

    # ==================== 预设配置工厂方法 ====================

    @classmethod
    def preset_micro_only(cls) -> "ClaudeCompressionMiddleware":
        """仅微压缩预设（最低开销）"""
        return cls(config=MICRO_ONLY_CONFIG)

    @classmethod
    def preset_aggressive(cls) -> "ClaudeCompressionMiddleware":
        """激进压缩预设（最大节省）"""
        return cls(config=AGGRESSIVE_CONFIG)

    @classmethod
    def preset_conservative(cls) -> "ClaudeCompressionMiddleware":
        """保守压缩预设（安全优先）"""
        return cls(config=CONSERVATIVE_CONFIG)

    @classmethod
    def preset_no_compression(cls) -> "ClaudeCompressionMiddleware":
        """无压缩（用于调试或特殊场景）"""
        return cls(
            enable_micro_compact=False,
            enable_auto_compact=False,
            enable_partial_compact=False,
            enable_session_memory=False,
        )

    # ==================== 核心中间件方法 ====================

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse | ExtendedModelResponse:
        """包装模型调用，执行压缩逻辑

        这是中间件的核心入口，在每次模型调用前执行。
        """
        messages = list(request.messages)
        original_count = len(messages)

        # 获取状态
        compression_events = request.state.get("_compression_events", [])

        # 步骤 1: 微压缩（每轮执行，开销最小）
        if self.config.enable_micro_compact:
            messages = self._apply_micro_compact(messages, compression_events)

        # 步骤 2: 自动压缩（基于 token 阈值）
        if self.config.enable_auto_compact:
            messages = self._apply_auto_compact(messages, compression_events, request)

        # 步骤 3: 部分压缩（可选，更智能的保留）
        if self.config.enable_partial_compact:
            messages = self._apply_partial_compact(messages, compression_events)

        # 步骤 4: 会话压缩（在会话结束时）
        if self.config.enable_session_memory:
            messages = self._apply_session_compact(messages, compression_events, request)

        # 检查是否有压缩事件发生
        new_events = [
            e for e in compression_events
            if e["timestamp"] > (compression_events[-1]["timestamp"] if compression_events else "")
        ] if compression_events else []

        # 如果有新事件，返回 ExtendedModelResponse 更新状态
        if new_events and len(messages) < original_count:
            # 构建修改后的请求
            modified_request = request.override(messages=messages)

            # 调用 handler
            response = handler(modified_request)

            # 返回带状态更新的响应
            return ExtendedModelResponse(
                model_response=response,
                command=Command(update={
                    "_compression_events": compression_events + new_events,
                    "_last_compaction_time": datetime.now(UTC).isoformat(),
                }),
            )

        # 无压缩或无需更新状态
        modified_request = request.override(messages=messages)
        return handler(modified_request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | ExtendedModelResponse:
        """异步版本的 wrap_model_call"""
        # 复用同步逻辑
        result = self.wrap_model_call(
            request,
            lambda req: handler(req),  # type: ignore
        )
        # 如果结果是协程，等待它
        if hasattr(result, '__await__'):
            return await result
        return result

    # ==================== 压缩策略应用 ====================

    def _apply_micro_compact(
        self,
        messages: list[AnyMessage],
        events: list[CompressionEvent],
    ) -> list[AnyMessage]:
        """应用微压缩"""
        if not self.micro_strategy.should_compact(messages):
            return messages

        try:
            compressed, event = self.micro_strategy.compact(messages)
            events.append(event)

            logger.debug(
                f"Micro compact: {event['original_message_count']} -> "
                f"{event['compressed_message_count']} messages, "
                f"saved {event['original_token_count'] - event['compressed_token_count']} tokens"
            )

            return compressed
        except Exception as e:
            logger.warning(f"Micro compact failed: {e}")
            return messages

    def _apply_auto_compact(
        self,
        messages: list[AnyMessage],
        events: list[CompressionEvent],
        request: ModelRequest,
    ) -> list[AnyMessage]:
        """应用自动压缩"""
        # 获取上下文窗口大小（从模型信息或配置）
        context_window = self._get_context_window(request)

        if not self.auto_strategy.should_compact(messages, context_window=context_window):
            return messages

        try:
            compressed, event = self.auto_strategy.compact(messages, context_window=context_window)
            events.append(event)

            logger.info(
                f"Auto compact triggered at {event['original_token_count']} tokens: "
                f"{event['original_message_count']} -> {event['compressed_message_count']} messages"
            )

            return compressed
        except Exception as e:
            logger.warning(f"Auto compact failed: {e}")
            return messages

    def _apply_partial_compact(
        self,
        messages: list[AnyMessage],
        events: list[CompressionEvent],
    ) -> list[AnyMessage]:
        """应用部分压缩"""
        if not self.partial_strategy.should_compact(messages):
            return messages

        try:
            compressed, event = self.partial_strategy.compact(messages)
            events.append(event)

            logger.debug(
                f"Partial compact: preserved {len(event['preserved_indices'])} critical messages"
            )

            return compressed
        except Exception as e:
            logger.warning(f"Partial compact failed: {e}")
            return messages

    def _get_backend(self, request: ModelRequest):
        """从 request 获取 backend

        Backend 来源优先级：
        1. request.runtime.backend (如果存在)
        2. request.state.get("_backend")
        3. None (不使用 Backend 存储)
        """
        # 尝试从 runtime 获取
        runtime = getattr(request, "runtime", None)
        if runtime and hasattr(runtime, "backend"):
            return runtime.backend

        # 尝试从 state 获取
        backend = request.state.get("_backend")
        if backend:
            return backend

        return None

    def _apply_session_compact(
        self,
        messages: list[AnyMessage],
        events: list[CompressionEvent],
        request: ModelRequest,
    ) -> list[AnyMessage]:
        """应用会话压缩

        使用 deep-agent Backend 统一存储会话历史：
        - FilesystemBackend: 存储到本地文件系统
        - StateBackend: 存储到 LangGraph 状态
        - DaytonaSandbox: 存储到远程沙箱
        - 其他自定义 Backend
        """
        # 检查是否是会话结束（可以通过特定标志或配置判断）
        session_ending = request.state.get("_session_ending", False)

        if not self.session_strategy.should_compact(messages, session_ending=session_ending):
            return messages

        try:
            session_id = request.state.get("session_id", "default")

            # 获取 Backend（deep-agent 统一存储）
            backend = self._get_backend(request)

            compressed, event = self.session_strategy.compact(
                messages,
                session_id=session_id,
                backend=backend,  # 传入 Backend 用于存储
            )
            events.append(event)

            if event.get("file_path"):
                logger.info(
                    f"Session compact saved to backend: {event['file_path']}"
                )
            else:
                logger.info("Session compact completed (no backend storage)")

            return compressed
        except Exception as e:
            logger.warning(f"Session compact failed: {e}")
            return messages

    def _get_context_window(self, request: ModelRequest) -> int:
        """获取模型上下文窗口大小"""
        # 尝试从模型信息获取
        model = getattr(request, 'model', None)
        if model and hasattr(model, 'profile'):
            profile = model.profile
            if isinstance(profile, dict) and 'max_input_tokens' in profile:
                return profile['max_input_tokens']

        # 默认值（Claude 3.5 Sonnet）
        return 200000

    # ==================== 工具方法 ====================

    def get_compression_stats(self, state: AgentState) -> dict[str, Any]:
        """获取压缩统计信息"""
        events = state.get("_compression_events", [])

        if not events:
            return {"total_compactions": 0}

        stats = {
            "total_compactions": len(events),
            "by_level": {},
            "total_tokens_saved": 0,
            "last_compaction": events[-1]["timestamp"] if events else None,
        }

        for event in events:
            level = event["level"]
            if level not in stats["by_level"]:
                stats["by_level"][level] = {
                    "count": 0,
                    "tokens_saved": 0,
                }

            stats["by_level"][level]["count"] += 1
            tokens_saved = event["original_token_count"] - event["compressed_token_count"]
            stats["by_level"][level]["tokens_saved"] += tokens_saved
            stats["total_tokens_saved"] += tokens_saved

        return stats

    def reset_stats(self, state: AgentState) -> Command:
        """重置压缩统计"""
        return Command(update={
            "_compression_events": [],
            "_last_compaction_time": None,
        })

    def save_compression_history(
        self,
        backend,
        session_id: str,
        state: AgentState,
    ) -> Optional[str]:
        """将压缩历史保存到 Backend 存储

        使用 deep-agent Backend 统一存储压缩事件历史，
        支持跨会话统计和分析。

        Args:
            backend: deep-agent Backend 实例
            session_id: 会话 ID
            state: Agent 状态

        Returns:
            保存的文件路径，失败返回 None
        """
        if backend is None:
            return None

        try:
            import json

            events = state.get("_compression_events", [])
            stats = self.get_compression_stats(state)

            history_data = {
                "session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "stats": stats,
                "events": events,
            }

            file_path = f"/compression_history/{session_id}_history.json"
            content = json.dumps(history_data, ensure_ascii=False, indent=2)

            result = backend.write(file_path, content)

            if result.error:
                logger.warning(f"Failed to save compression history: {result.error}")
                return None

            logger.debug(f"Compression history saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.warning(f"Failed to save compression history: {e}")
            return None

    async def asave_compression_history(
        self,
        backend,
        session_id: str,
        state: AgentState,
    ) -> Optional[str]:
        """异步保存压缩历史到 Backend"""
        if backend is None:
            return None

        try:
            import json

            events = state.get("_compression_events", [])
            stats = self.get_compression_stats(state)

            history_data = {
                "session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "stats": stats,
                "events": events,
            }

            file_path = f"/compression_history/{session_id}_history.json"
            content = json.dumps(history_data, ensure_ascii=False, indent=2)

            result = await backend.awrite(file_path, content)

            if result.error:
                logger.warning(f"Failed to save compression history: {result.error}")
                return None

            logger.debug(f"Compression history saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.warning(f"Failed to save compression history: {e}")
            return None


# ==================== 便捷函数 ====================

def create_compression_middleware(
    level: str = "standard",
    **kwargs
) -> ClaudeCompressionMiddleware:
    """创建压缩中间件的便捷函数

    Args:
        level: 压缩级别
            - "none": 无压缩
            - "micro": 仅微压缩
            - "standard": 微压缩 + 自动压缩（默认）
            - "aggressive": 所有层级
        **kwargs: 额外的配置参数

    Returns:
        配置好的压缩中间件
    """
    presets = {
        "none": ClaudeCompressionMiddleware.preset_no_compression,
        "micro": ClaudeCompressionMiddleware.preset_micro_only,
        "standard": lambda: ClaudeCompressionMiddleware(),
        "aggressive": ClaudeCompressionMiddleware.preset_aggressive,
        "conservative": ClaudeCompressionMiddleware.preset_conservative,
    }

    if level not in presets:
        raise ValueError(f"Unknown compression level: {level}. Choose from {list(presets.keys())}")

    return presets[level]()
