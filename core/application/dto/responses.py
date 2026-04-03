"""
Response DTOs - 响应数据传输对象

使用 dataclass 定义服务层返回的结果类型，
便于类型检查和序列化。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class CreateDialogResult:
    """创建对话结果

    Attributes:
        dialog_id: 新创建对话的 ID
        title: 对话标题
        created_at: 创建时间（ISO 格式字符串）
    """
    dialog_id: str
    title: str
    created_at: str


@dataclass
class SendMessageResult:
    """发送消息结果

    Attributes:
        message_id: 消息 ID
        content: 消息内容
        token_count: 消耗的 token 数
    """
    message_id: str
    content: str
    token_count: int


@dataclass
class LoadSkillResult:
    """加载技能结果

    Attributes:
        skill_id: 技能 ID
        name: 技能名称
        tool_count: 加载的工具数量
        loaded: 是否加载成功
    """
    skill_id: str
    name: str
    tool_count: int
    loaded: bool


@dataclass
class SkillInfoDTO:
    """技能信息 DTO

    Attributes:
        id: 技能 ID
        name: 技能名称
        description: 技能描述
        tools: 工具名称列表
        active: 是否已激活
    """
    id: str
    name: str
    description: str
    tools: List[str]
    active: bool


@dataclass
class MessageDTO:
    """消息 DTO

    Attributes:
        id: 消息 ID
        role: 角色 (user/assistant/system/tool)
        content: 消息内容
        created_at: 创建时间（ISO 格式字符串）
        metadata: 附加元数据
    """
    id: str
    role: str
    content: str
    created_at: str
    metadata: Dict[str, Any]

    @classmethod
    def from_entity(cls, message) -> "MessageDTO":
        """从消息实体创建 DTO

        Args:
            message: 消息实体（LangChain BaseMessage 或自定义消息类型）

        Returns:
            MessageDTO 实例
        """
        # 处理不同类型的消息对象
        if hasattr(message, 'id'):
            msg_id = message.id
        else:
            msg_id = ""

        if hasattr(message, 'role'):
            role = message.role
        elif hasattr(message, 'type'):
            role = message.type
        else:
            role = "unknown"

        if hasattr(message, 'content'):
            content = message.content
        else:
            content = ""

        if hasattr(message, 'created_at'):
            created_at = message.created_at
        else:
            created_at = datetime.now().isoformat()

        metadata = {}
        if hasattr(message, 'additional_kwargs'):
            metadata = message.additional_kwargs or {}
        elif hasattr(message, 'metadata'):
            metadata = message.metadata or {}

        return cls(
            id=msg_id,
            role=role,
            content=content,
            created_at=created_at,
            metadata=metadata
        )


@dataclass
class MemorySummary:
    """记忆摘要

    Attributes:
        content: 摘要内容
        created_at: 创建时间
        dialog_count: 关联的对话数量
    """
    content: str
    created_at: datetime
    dialog_count: int


@dataclass
class ChatResponse:
    """聊天响应 DTO

    Attributes:
        dialog_id: 对话 ID
        message_id: 消息 ID
        content: 完整响应内容
        tool_calls: 工具调用列表
        tokens_used: 使用的 token 数
    """
    dialog_id: str
    message_id: str
    content: str
    tool_calls: List[Dict[str, Any]]
    tokens_used: int
