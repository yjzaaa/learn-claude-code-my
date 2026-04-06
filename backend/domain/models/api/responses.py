"""
API Response Models - API 响应模型

所有继承 Response 基类的 API 响应模型。
"""

from typing import Any

from pydantic import BaseModel, Field

from backend.domain.models.events.websocket import WSDialogSnapshot
from backend.domain.models.shared.base import Response
from backend.domain.models.shared.mixins import DialogRefMixin

from .containers import ItemData, ProposalData, ResultData, ToolItem


class ResultModel(Response):
    """通用操作结果模型"""

    data: Any | None = None

    @classmethod
    def ok(cls, message: str = "Success", data: Any | None = None, **kwargs) -> "ResultModel":
        """创建成功结果"""
        return cls(success=True, message=message, data=data, **kwargs)

    @classmethod
    def error(cls, message: str = "Error", data: Any | None = None, **kwargs) -> "ResultModel":
        """创建错误结果"""
        return cls(success=False, message=message, data=data, **kwargs)


class SendMessageData(BaseModel):
    """发送消息响应数据"""

    message_id: str
    status: str


class SendMessageResponse(Response, DialogRefMixin):
    """发送消息响应模型"""

    data: SendMessageData


class ResumeData(BaseModel):
    """恢复对话响应数据"""

    dialog_id: str
    status: str


class ResumeDialogResponse(Response):
    """恢复对话响应模型"""

    data: ResumeData


class AgentStatusItem(BaseModel):
    """Agent 状态项"""

    dialog_id: str
    status: str


class AgentStatusData(BaseModel):
    """Agent 状态数据"""

    active_dialogs: list[AgentStatusItem]
    total_dialogs: int


class AgentStatusResponse(Response):
    """Agent 状态响应模型"""

    data: AgentStatusData


class StopAgentData(BaseModel):
    """停止 Agent 响应数据"""

    stopped_dialogs: list[str]
    count: int


class StopAgentResponse(Response):
    """停止 Agent 响应模型"""

    data: StopAgentData


class SkillItem(BaseModel):
    """技能项模型"""

    name: str
    description: str
    tags: str
    path: str


class SkillListResponse(Response):
    """技能列表响应模型"""

    data: list[SkillItem]


class PendingSkillEditsResponse(Response):
    """待处理 Skill Edit 响应模型"""

    data: ProposalData


class DecideSkillEditResponse(Response):
    """Skill Edit 决策响应模型"""

    data: Any | None = None


class HealthResponse(Response):
    """健康检查响应模型"""

    status: str
    dialogs: int


class GetMessagesResponse(Response):
    """获取消息响应模型"""

    data: ResultData


# 对话相关响应


class ListDialogsResponse(Response):
    """对话列表响应模型"""

    data: list[WSDialogSnapshot]


class CreateDialogResponse(Response):
    """创建对话响应模型"""

    data: WSDialogSnapshot | None


class GetDialogResponse(Response):
    """获取对话响应模型"""

    data: WSDialogSnapshot


class DeleteDialogResponse(Response):
    """删除对话响应模型"""

    pass


# Todo 相关响应


class TodoStateDTO(BaseModel):
    """Todo 状态响应"""

    dialog_id: str
    items: list[Any] = Field(default_factory=list)
    rounds_since_todo: int = 0
    updated_at: float = Field(default_factory=__import__("time").time)


class TodoListResponse(Response):
    """Todo 列表响应"""

    dialog_id: str
    items: list[ItemData] = Field(default_factory=list)
    enabled: bool = True


# Skill 相关响应


class SkillDetailResponse(BaseModel):
    """技能详情响应"""

    id: str
    name: str
    description: str
    version: str
    path: str | None = None
    tools: list[ToolItem] = Field(default_factory=list)


class SkillEditProposalDTO(BaseModel):
    """Skill Edit 提案 DTO"""

    approval_id: str
    dialog_id: str
    path: str
    unified_diff: str
    reason: str
    status: str


class PendingProposalsResponse(Response):
    """待处理提案列表响应"""

    proposals: list[ItemData] = Field(default_factory=list)


# 其他


class ProviderSummary(BaseModel):
    """Provider 摘要信息"""

    name: str
    model: str
    status: str = "active"
