"""
Dialog Models - 对话模型

定义对话、消息和工具调用的领域模型。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from .types import MessageDict, ToolCallDict, ToolCallFunctionDict

try:
    from dataclasses_json import dataclass_json  # type: ignore[import-not-found]
except ImportError:
    def dataclass_json(cls):  # type: ignore[no-redef]
        return cls





@dataclass_json
@dataclass
class ToolCallFunction:
    """OpenAI 格式的工具调用函数定义"""
    name: str
    arguments: str  # JSON 字符串




@dataclass_json
@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @classmethod
    def create(cls, name: str, arguments: Dict[str, Any]) -> "ToolCall":
        return cls(
            id=f"tc_{uuid.uuid4().hex[:12]}",
            name=name,
            arguments=arguments,
            started_at=datetime.now()
        )
    
    def complete(self, result: str):
        self.result = result
        self.completed_at = datetime.now()
    
    def fail(self, error: str):
        self.error = error
        self.completed_at = datetime.now()
    
    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None
    
    @property
    def duration_ms(self) -> Optional[int]:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None


@dataclass_json
@dataclass
class Message:
    """消息"""
    id: str
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None  # for tool role messages
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
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
    def assistant(cls, content: str, tool_calls: Optional[List[ToolCall]] = None, message_id: Optional[str] = None, **metadata) -> "Message":
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
    
    def to_dict(self) -> MessageDict:
        """转换为字典 (OpenAI 格式)"""
        result: MessageDict = {"role": self.role, "content": self.content}
        if self.tool_calls:
            result["tool_calls"] = [
                ToolCallDict(
                    id=tc.id,
                    type="function",
                    function=ToolCallFunctionDict(
                        name=tc.name,
                        arguments=str(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
                    ),
                )
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass_json
@dataclass
class Dialog:
    """对话"""
    id: str
    title: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, title: Optional[str] = None) -> "Dialog":
        """创建新对话"""
        return cls(
            id=f"dlg_{uuid.uuid4().hex[:16]}",
            title=title
        )
    
    @classmethod
    def from_user_input(cls, user_input: str) -> "Dialog":
        """从用户输入创建对话"""
        dialog = cls.create(title=user_input[:50])
        dialog.add_message(Message.user(user_input))
        return dialog
    
    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_messages_for_llm(self) -> List[MessageDict]:
        """获取 LLM 格式的消息列表"""
        return [msg.to_dict() for msg in self.messages]
    
    @property
    def last_message(self) -> Optional[Message]:
        """最后一条消息"""
        return self.messages[-1] if self.messages else None
    
    @property
    def message_count(self) -> int:
        """消息数量"""
        return len(self.messages)
    
    def estimate_tokens(self) -> int:
        """估算 token 数 (简单估算)"""
        total = 0
        for msg in self.messages:
            # 简单估算: 1 token ≈ 4 字符
            total += len(msg.content) // 4 + 10  # +10 for overhead
        return total
