"""类型定义和配置"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Literal, TypedDict
from enum import Enum, auto


class CompressionLevel(Enum):
    """压缩层级"""
    MICRO = auto()      # 微压缩：缓存编辑
    AUTO = auto()       # 自动压缩：Token阈值
    PARTIAL = auto()    # 部分压缩：智能保留
    SESSION = auto()    # 会话压缩：跨会话持久化


@dataclass
class MicroCompactConfig:
    """微压缩配置"""
    # 保留最近 N 轮的工具结果
    keep_recent_rounds: int = 3
    # 使用 cache_edits（Anthropic API 特性）还是直接删除
    use_cache_edits: bool = True
    # 时间触发：超过 N 分钟的旧结果删除
    time_based_threshold_minutes: Optional[int] = None


@dataclass
class AutoCompactConfig:
    """自动压缩配置"""
    # 触发阈值：上下文窗口的比例或具体token数
    threshold: tuple[Literal["fraction", "tokens"], float] = ("fraction", 0.7)
    # 压缩后保留的比例或token数
    keep: tuple[Literal["fraction", "tokens", "messages"], float] = ("fraction", 0.3)
    # 是否剥离图像
    strip_images: bool = True
    # 是否去重附件
    deduplicate_attachments: bool = True


@dataclass
class PartialCompactConfig:
    """部分压缩配置"""
    # 预压缩分析：保留被引用的内容
    preserve_referenced_content: bool = True
    # 保留关键决策点
    preserve_decision_points: bool = True
    # 保留文件操作结果
    preserve_file_operations: bool = True


@dataclass
class SessionMemoryConfig:
    """会话记忆配置"""
    # Backend 存储路径前缀（统一使用 deep-agent Backend）
    storage_path_prefix: str = "/compression_history"
    # 启用跨会话恢复
    enable_cross_session_recovery: bool = True
    # 压缩后保存到 Backend
    save_to_backend: bool = True


@dataclass
class CompressionConfig:
    """压缩中间件完整配置"""
    # 启用哪些压缩层级
    enable_micro_compact: bool = True
    enable_auto_compact: bool = True
    enable_partial_compact: bool = False  # 默认关闭，需要更复杂的分析
    enable_session_memory: bool = False   # 默认关闭，需要配置存储

    # 各层级配置
    micro: MicroCompactConfig = field(default_factory=MicroCompactConfig)
    auto: AutoCompactConfig = field(default_factory=AutoCompactConfig)
    partial: PartialCompactConfig = field(default_factory=PartialCompactConfig)
    session: SessionMemoryConfig = field(default_factory=SessionMemoryConfig)

    # Token 计数器（可选，用于非 Anthropic 模型）
    token_counter: Optional[Callable[[list], int]] = None


class CompressionEvent(TypedDict):
    """压缩事件记录"""
    level: str                    # 压缩层级 "micro" | "auto" | "partial" | "session"
    timestamp: str                # ISO 格式时间戳
    original_message_count: int   # 原始消息数
    compressed_message_count: int # 压缩后消息数
    original_token_count: int     # 原始token数
    compressed_token_count: int   # 压缩后token数
    preserved_indices: list[int]  # 保留的消息索引
    summary: Optional[str]        # 生成的摘要（如果有）
    file_path: Optional[str]      # 卸载历史的文件路径（如果有）


# 默认配置
DEFAULT_COMPRESSION_CONFIG = CompressionConfig()

# 仅微压缩配置（最低开销）
MICRO_ONLY_CONFIG = CompressionConfig(
    enable_micro_compact=True,
    enable_auto_compact=False,
    enable_partial_compact=False,
    enable_session_memory=False,
)

# 激进压缩配置（最大节省）
AGGRESSIVE_CONFIG = CompressionConfig(
    enable_micro_compact=True,
    enable_auto_compact=True,
    enable_partial_compact=True,
    enable_session_memory=True,
    auto=AutoCompactConfig(threshold=("fraction", 0.6), keep=("fraction", 0.2)),
)

# 保守压缩配置（安全优先）
CONSERVATIVE_CONFIG = CompressionConfig(
    enable_micro_compact=True,
    enable_auto_compact=True,
    enable_partial_compact=False,
    enable_session_memory=False,
    auto=AutoCompactConfig(threshold=("fraction", 0.8), keep=("fraction", 0.4)),
)
