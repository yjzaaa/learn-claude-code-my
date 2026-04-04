"""
Request DTOs - 请求数据传输对象

使用 dataclass 定义请求参数，便于类型检查和文档生成。
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ChatRequest:
    """聊天请求 DTO

    用于 AgentOrchestrationService.chat() 方法，
    封装用户聊天请求的所有参数。

    Attributes:
        dialog_id: 可选的对话 ID，为 None 时创建新对话
        user_input: 用户输入内容
        stream: 是否流式返回响应
        use_memory: 是否使用记忆功能
        skill_ids: 要激活的技能 ID 列表
    """
    dialog_id: Optional[str] = None
    user_input: str = ""
    stream: bool = True
    use_memory: bool = True
    skill_ids: Optional[List[str]] = None
