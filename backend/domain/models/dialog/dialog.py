"""
Dialog - 对话实体

对话管理和消息列表的领域模型。
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from backend.domain.models.message.adapter import LegacyMessageAdapter
from backend.domain.models.message.message import Message


class DialogOutput(BaseModel):
    """对话输出模型"""
    id: str
    title: Optional[str] = None
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    selected_model_id: Optional[str] = None  # 对话选择的模型


class Dialog:
    """
    对话 - 管理消息列表和元数据

    使用 LangChain BaseMessage 作为消息存储格式。
    支持 per-dialog 模型选择。
    """

    def __init__(
        self,
        id: Optional[str] = None,
        title: Optional[str] = None,
        messages: Optional[List[BaseMessage]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        selected_model_id: Optional[str] = None,
    ):
        self.id: str = id or f"dlg_{uuid.uuid4().hex[:16]}"
        self.title: Optional[str] = title
        self.messages: List[BaseMessage] = messages or []
        self.metadata: Dict[str, Any] = metadata or {}
        self.created_at: datetime = created_at or datetime.now()
        self.updated_at: datetime = updated_at or datetime.now()
        self.selected_model_id: Optional[str] = selected_model_id  # 对话选择的模型

    @classmethod
    def create(cls, title: Optional[str] = None) -> "Dialog":
        """创建新对话"""
        # 从配置获取默认模型
        from backend.infrastructure.config import config
        default_model = config.model.id
        return cls(title=title, selected_model_id=default_model or None)

    @classmethod
    def from_user_input(cls, user_input: str) -> "Dialog":
        """从用户输入创建对话"""
        from backend.infrastructure.config import config
        default_model = config.model.id
        dialog = cls.create(title=user_input[:50])
        dialog.selected_model_id = default_model or None
        dialog.add_human_message(user_input)
        return dialog

    def add_message(self, message: BaseMessage) -> None:
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def add_human_message(self, content: str, **kwargs) -> "BaseMessage":
        """添加用户消息"""
        from backend.domain.models.message.messages import create_human
        msg = create_human(content, **kwargs)
        self.add_message(msg)
        return msg

    def add_ai_message(self, content: str, **kwargs) -> "BaseMessage":
        """添加助手消息"""
        from backend.domain.models.message.messages import create_ai
        msg = create_ai(content, **kwargs)
        self.add_message(msg)
        return msg

    def add_system_message(self, content: str, **kwargs) -> "BaseMessage":
        """添加系统消息"""
        from backend.domain.models.message.messages import create_system
        msg = create_system(content, **kwargs)
        self.add_message(msg)
        return msg

    def add_tool_message(
        self, content: str, tool_call_id: str, **kwargs
    ) -> "BaseMessage":
        """添加工具消息"""
        from backend.domain.models.message.messages import create_tool
        msg = create_tool(content, tool_call_id, **kwargs)
        self.add_message(msg)
        return msg

    def get_messages_for_llm(self) -> List[Dict[str, Any]]:
        """获取 LLM 格式的消息列表"""
        return [message_to_dict(m) for m in self.messages]

    def to_dict(self) -> Dict[str, Any]:
        """将对话序列化为字典"""
        output = DialogOutput(
            id=self.id,
            title=self.title,
            messages=[message_to_dict(m) for m in self.messages],
            metadata=self.metadata,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            selected_model_id=self.selected_model_id,
        )
        return output.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dialog":
        """从字典恢复对话"""
        messages_data = data.get("messages", [])

        # 检测并转换旧格式
        if messages_data and LegacyMessageAdapter.is_legacy_format(messages_data[0]):
            messages_data = LegacyMessageAdapter.convert_list_legacy_to_langchain(
                messages_data
            )

        messages = messages_from_dict(messages_data)

        return cls(
            id=data.get("id"),
            title=data.get("title"),
            messages=messages,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", ""))
            if "created_at" in data
            else None,
            updated_at=datetime.fromisoformat(data.get("updated_at", ""))
            if "updated_at" in data
            else None,
            selected_model_id=data.get("selected_model_id"),
        )

    @property
    def last_message(self) -> Optional[BaseMessage]:
        """最后一条消息"""
        return self.messages[-1] if self.messages else None

    @property
    def message_count(self) -> int:
        """消息数量"""
        return len(self.messages)

    def estimate_tokens(self) -> int:
        """估算 token 数"""
        total = 0
        for msg in self.messages:
            total += len(msg.content) // 4 + 10  # +10 for overhead
        return total

    def clear_messages(self) -> None:
        """清空消息"""
        self.messages.clear()
        self.updated_at = datetime.now()

    def get_message_by_index(self, index: int) -> Optional[BaseMessage]:
        """通过索引获取消息"""
        if 0 <= index < len(self.messages):
            return self.messages[index]
        return None
