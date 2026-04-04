"""
Message - 消息实体

对话中单条消息的领域模型。
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from .tool_call import ToolCall


class Message:
    """
    消息 - 对话中的单条消息

    使用普通类而非 Pydantic/dataclass，保持灵活性。
    """

    def __init__(
        self,
        id: str,
        role: str,
        content: str,
        tool_calls: Optional[List["ToolCall"]] = None,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []
        self.tool_call_id = tool_call_id
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now()

    @classmethod
    def user(cls, content: str, **metadata) -> "Message":
        """创建用户消息"""
        return cls(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            role="user",
            content=content,
            metadata=metadata
        )

    @classmethod
    def assistant(
        cls,
        content: str,
        tool_calls: Optional[List["ToolCall"]] = None,
        message_id: Optional[str] = None,
        **metadata
    ) -> "Message":
        """创建助手消息"""
        return cls(
            id=message_id or f"msg_{uuid.uuid4().hex[:12]}",
            role="assistant",
            content=content,
            tool_calls=tool_calls or [],
            metadata=metadata
        )

    @classmethod
    def system(cls, content: str) -> "Message":
        """创建系统消息"""
        return cls(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            role="system",
            content=content
        )

    @classmethod
    def tool(cls, tool_call_id: str, content: str) -> "Message":
        """创建工具结果消息"""
        return cls(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            role="tool",
            content=content,
            tool_call_id=tool_call_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 (OpenAI 格式)"""
        result: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": str(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result
