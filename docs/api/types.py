"""
API 契约 - Python 类型定义

前后端共享的类型定义，与 OpenAPI 规范保持一致
使用 Pydantic BaseModel 实现运行时类型验证

@version 1.0.0
"""

from typing import Any, Dict, List, Literal, Optional, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ═════════════════════════════════════════════════════════════════════════════
# 枚举类型
# ═════════════════════════════════════════════════════════════════════════════


class DialogStatus(str, Enum):
    """对话状态"""
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    COMPLETED = "completed"
    ERROR = "error"


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


class ToolCallStatus(str, Enum):
    """工具调用状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class TruncatedReason(str, Enum):
    """流截断原因"""
    INTERRUPTED = "interrupted"
    TIMEOUT = "timeout"
    ERROR = "error"
    NOT_SUPPORTED = "not_supported"


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 验证错误 (400)
    VALIDATION_001 = "VALIDATION_001"
    VALIDATION_002 = "VALIDATION_002"
    # 未找到 (404)
    NOT_FOUND_100 = "NOT_FOUND_100"
    NOT_FOUND_101 = "NOT_FOUND_101"
    # 冲突 (409)
    CONFLICT_100 = "CONFLICT_100"
    # 内部错误 (500)
    INTERNAL_001 = "INTERNAL_001"
    # Agent 错误 (600)
    AGENT_300 = "AGENT_300"
    AGENT_301 = "AGENT_301"
    AGENT_302 = "AGENT_302"
    # 工具错误 (700)
    TOOL_400 = "TOOL_400"
    TOOL_401 = "TOOL_401"
    TOOL_402 = "TOOL_402"
    # Skill 错误 (800)
    SKILL_500 = "SKILL_500"
    SKILL_501 = "SKILL_501"


# 错误码消息映射
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_001: "请求参数无效",
    ErrorCode.VALIDATION_002: "缺少必需参数",
    ErrorCode.NOT_FOUND_100: "对话不存在",
    ErrorCode.NOT_FOUND_101: "消息不存在",
    ErrorCode.CONFLICT_100: "对话正在处理中",
    ErrorCode.INTERNAL_001: "内部服务器错误",
    ErrorCode.AGENT_300: "Agent 执行错误",
    ErrorCode.AGENT_301: "Agent 超时",
    ErrorCode.AGENT_302: "Agent 轮次限制达到",
    ErrorCode.TOOL_400: "工具执行错误",
    ErrorCode.TOOL_401: "工具未找到",
    ErrorCode.TOOL_402: "工具参数无效",
    ErrorCode.SKILL_500: "Skill 加载错误",
    ErrorCode.SKILL_501: "Skill 未找到",
}


# ═════════════════════════════════════════════════════════════════════════════
# 实体模型
# ═════════════════════════════════════════════════════════════════════════════


class ToolCall(BaseModel):
    """工具调用"""
    id: str = Field(..., description="工具调用 ID")
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(..., description="工具参数")
    status: ToolCallStatus = Field(..., description="执行状态")
    result: Optional[str] = Field(None, description="执行结果")
    started_at: Optional[str] = Field(None, description="开始时间")
    completed_at: Optional[str] = Field(None, description="完成时间")


class Message(BaseModel):
    """消息"""
    id: str = Field(..., description="消息 ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    content_type: ContentType = Field(..., description="内容类型")
    status: MessageStatus = Field(..., description="消息状态")
    timestamp: str = Field(..., description="时间戳")

    # Assistant only
    tool_calls: Optional[List[ToolCall]] = Field(None, description="工具调用列表")
    reasoning_content: Optional[str] = Field(None, description="推理内容")
    agent_name: Optional[str] = Field(None, description="Agent 名称")

    # Tool only
    tool_call_id: Optional[str] = Field(None, description="关联工具调用 ID")
    tool_name: Optional[str] = Field(None, description="工具名称")


class StreamingMessage(BaseModel):
    """流式消息"""
    id: str = Field(..., description="消息 ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="当前累积内容")
    content_type: ContentType = Field(..., description="内容类型")
    status: Literal["streaming"] = Field("streaming", description="消息状态")
    timestamp: str = Field(..., description="时间戳")
    agent_name: str = Field(..., description="Agent 名称")
    reasoning_content: Optional[str] = Field(None, description="推理内容")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="工具调用列表")


class DialogMetadata(BaseModel):
    """对话元数据"""
    model: str = Field(..., description="模型标识符")
    agent_name: str = Field(..., description="Agent 名称")
    tool_calls_count: int = Field(0, description="工具调用次数")
    total_tokens: int = Field(0, description="总 Token 数")


class DialogSession(BaseModel):
    """对话会话"""
    id: str = Field(..., description="对话 ID")
    title: str = Field(..., description="对话标题")
    status: DialogStatus = Field(..., description="对话状态")
    messages: List[Message] = Field(..., description="消息列表")
    streaming_message: Optional[StreamingMessage] = Field(None, description="流式消息")
    metadata: DialogMetadata = Field(..., description="元数据")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class DialogSummary(BaseModel):
    """对话摘要"""
    id: str = Field(..., description="对话 ID")
    title: str = Field(..., description="对话标题")
    message_count: int = Field(..., description="消息数量")
    updated_at: str = Field(..., description="更新时间")


class TodoItem(BaseModel):
    """Todo 项目"""
    id: str = Field(..., description="Todo ID")
    text: str = Field(..., description="Todo 文本")
    status: Literal["pending", "in_progress", "completed"] = Field("pending", description="状态")


class SkillItem(BaseModel):
    """技能项"""
    name: str = Field(..., description="技能名称")
    description: str = Field(..., description="技能描述")
    tags: str = Field(..., description="技能标签")
    path: str = Field(..., description="技能路径")


# ═════════════════════════════════════════════════════════════════════════════
# REST API 请求模型
# ═════════════════════════════════════════════════════════════════════════════


class CreateDialogRequest(BaseModel):
    """创建对话请求"""
    title: Optional[str] = Field("New Dialog", description="对话标题")


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., description="消息内容", min_length=1)


# ═════════════════════════════════════════════════════════════════════════════
# REST API 响应模型
# ═════════════════════════════════════════════════════════════════════════════


class BaseResponse(BaseModel):
    """基础响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")


class HealthResponse(BaseResponse):
    """健康检查响应"""
    status: Literal["ok"] = Field("ok", description="状态")
    dialogs: int = Field(..., description="对话总数")


class ListDialogsResponse(BaseResponse):
    """对话列表响应"""
    data: List[DialogSession] = Field(..., description="对话列表")


class CreateDialogResponse(BaseResponse):
    """创建对话响应"""
    data: DialogSession = Field(..., description="创建的对话")


class GetDialogResponse(BaseResponse):
    """获取对话响应"""
    data: DialogSession = Field(..., description="对话详情")


class DeleteDialogResponse(BaseResponse):
    """删除对话响应"""
    pass


class GetMessagesData(BaseModel):
    """获取消息数据"""
    items: List[Message] = Field(..., description="消息列表")


class GetMessagesResponse(BaseResponse):
    """获取消息响应"""
    data: GetMessagesData = Field(..., description="消息数据")


class SendMessageData(BaseModel):
    """发送消息数据"""
    message_id: str = Field(..., description="生成的消息 ID")
    status: Literal["queued"] = Field("queued", description="队列状态")


class SendMessageResponse(BaseResponse):
    """发送消息响应"""
    data: SendMessageData = Field(..., description="发送消息数据")


class ResumeData(BaseModel):
    """恢复对话数据"""
    dialog_id: str = Field(..., description="对话 ID")
    status: Literal["idle"] = Field("idle", description="恢复后的状态")


class ResumeDialogResponse(BaseResponse):
    """恢复对话响应"""
    data: ResumeData = Field(..., description="恢复对话数据")


class AgentStatusItem(BaseModel):
    """Agent 状态项"""
    dialog_id: str = Field(..., description="对话 ID")
    status: str = Field(..., description="当前状态")


class AgentStatusData(BaseModel):
    """Agent 状态数据"""
    active_dialogs: List[AgentStatusItem] = Field(..., description="活跃对话列表")
    total_dialogs: int = Field(..., description="对话总数")


class AgentStatusResponse(BaseResponse):
    """Agent 状态响应"""
    data: AgentStatusData = Field(..., description="Agent 状态数据")


class StopAgentData(BaseModel):
    """停止 Agent 数据"""
    stopped_dialogs: List[str] = Field(..., description="停止的对话 ID 列表")
    count: int = Field(..., description="停止的对话数量")


class StopAgentResponse(BaseResponse):
    """停止 Agent 响应"""
    data: StopAgentData = Field(..., description="停止 Agent 数据")


class SkillListResponse(BaseResponse):
    """技能列表响应"""
    data: List[SkillItem] = Field(..., description="技能列表")


class PendingSkillEditsData(BaseModel):
    """待处理技能编辑数据"""
    proposals: List[Dict[str, Any]] = Field(default_factory=list, description="提案列表")


class PendingSkillEditsResponse(BaseResponse):
    """待处理技能编辑响应"""
    data: PendingSkillEditsData = Field(..., description="待处理编辑数据")


# ═════════════════════════════════════════════════════════════════════════════
# WebSocket 消息模型
# ═════════════════════════════════════════════════════════════════════════════


class ClientMessage(BaseModel):
    """基础客户端消息"""
    type: str = Field(..., description="消息类型")
    timestamp: Optional[int] = Field(None, description="客户端时间戳")

    class Config:
        # 允许子类覆盖字段类型
        arbitrary_types_allowed = True


class SubscribeRequest(ClientMessage):
    """订阅请求"""
    type: Literal["subscribe"] = "subscribe"
    dialog_id: str = Field(..., description="对话 ID")
    last_known_message_id: Optional[str] = Field(None, description="最后已知消息 ID")


class UnsubscribeRequest(ClientMessage):
    """取消订阅请求"""
    type: Literal["unsubscribe"] = "unsubscribe"
    dialog_id: str = Field(..., description="对话 ID")


class PingRequest(ClientMessage):
    """心跳请求"""
    type: Literal["ping"] = "ping"


class StreamResumeRequest(ClientMessage):
    """流恢复请求"""
    type: Literal["stream:resume"] = "stream:resume"
    dialog_id: str = Field(..., description="对话 ID")
    message_id: str = Field(..., description="消息 ID")
    from_chunk: int = Field(..., description="从哪个块开始恢复")


class SyncRequest(ClientMessage):
    """同步请求"""
    type: Literal["sync:request"] = "sync:request"
    dialog_id: str = Field(..., description="对话 ID")
    last_sync_at: Optional[int] = Field(None, description="最后同步时间戳")


# 客户端请求联合类型
ClientRequest = Union[
    SubscribeRequest,
    UnsubscribeRequest,
    PingRequest,
    StreamResumeRequest,
    SyncRequest,
]


class ServerMessage(BaseModel):
    """基础服务端消息"""
    type: str = Field(..., description="事件类型")
    timestamp: int = Field(..., description="Unix 毫秒时间戳")

    class Config:
        # 允许子类覆盖字段类型
        arbitrary_types_allowed = True


class DialogSnapshotEvent(ServerMessage):
    """对话快照事件"""
    type: Literal["dialog:snapshot"] = "dialog:snapshot"
    dialog_id: str = Field(..., description="对话 ID")
    data: DialogSession = Field(..., description="对话数据")


class StreamStartEvent(ServerMessage):
    """流开始事件"""
    type: Literal["stream:start"] = "stream:start"
    dialog_id: str = Field(..., description="对话 ID")
    message_id: str = Field(..., description="消息 ID")
    role: MessageRole = Field(..., description="消息角色")
    metadata: Optional[Dict[str, str]] = Field(None, description="元数据")


class StreamDeltaData(BaseModel):
    """流增量数据"""
    content: str = Field(..., description="内容增量")
    reasoning: Optional[str] = Field(None, description="推理内容增量")


class StreamDeltaEvent(ServerMessage):
    """流增量事件"""
    type: Literal["stream:delta"] = "stream:delta"
    dialog_id: str = Field(..., description="对话 ID")
    message_id: str = Field(..., description="消息 ID")
    chunk_index: int = Field(..., description="块序号")
    delta: str = Field(..., description="内容增量")
    is_reasoning: bool = Field(False, description="是否为推理内容")


class TokenUsage(BaseModel):
    """Token 使用量"""
    prompt_tokens: int = Field(..., description="提示 Token 数")
    completion_tokens: int = Field(..., description="完成 Token 数")
    total_tokens: int = Field(..., description="总 Token 数")


class StreamEndEvent(ServerMessage):
    """流结束事件"""
    type: Literal["stream:end"] = "stream:end"
    dialog_id: str = Field(..., description="对话 ID")
    message_id: str = Field(..., description="消息 ID")
    final_content: str = Field(..., description="最终内容")
    usage: Optional[TokenUsage] = Field(None, description="Token 使用量")


class StreamResumedEvent(ServerMessage):
    """流恢复确认事件"""
    type: Literal["stream:resumed"] = "stream:resumed"
    dialog_id: str = Field(..., description="对话 ID")
    message_id: str = Field(..., description="消息 ID")
    from_chunk: int = Field(..., description="请求恢复的块")
    current_chunk: int = Field(..., description="当前块")


class StreamTruncatedEvent(ServerMessage):
    """流截断事件"""
    type: Literal["stream:truncated"] = "stream:truncated"
    dialog_id: str = Field(..., description="对话 ID")
    message_id: str = Field(..., description="消息 ID")
    reason: TruncatedReason = Field(..., description="截断原因")
    last_chunk_index: int = Field(..., description="最后块序号")


class StatusChangeEvent(ServerMessage):
    """状态变更事件"""
    type: Literal["status:change"] = "status:change"
    dialog_id: str = Field(..., description="对话 ID")
    from_status: DialogStatus = Field(..., alias="from", description="原状态")
    to_status: DialogStatus = Field(..., alias="to", description="新状态")

    class Config:
        populate_by_name = True


class ToolCallUpdateEvent(ServerMessage):
    """工具调用更新事件"""
    type: Literal["tool_call:update"] = "tool_call:update"
    dialog_id: str = Field(..., description="对话 ID")
    tool_call: ToolCall = Field(..., description="工具调用信息")


class TodoUpdatedEvent(ServerMessage):
    """Todo 更新事件"""
    type: Literal["todo:updated"] = "todo:updated"
    dialog_id: str = Field(..., description="对话 ID")
    todos: List[TodoItem] = Field(..., description="Todo 列表")
    rounds_since_todo: int = Field(0, description="距离上次更新 todo 的轮次")


class TodoReminderEvent(ServerMessage):
    """Todo 提醒事件"""
    type: Literal["todo:reminder"] = "todo:reminder"
    dialog_id: str = Field(..., description="对话 ID")
    message: str = Field(..., description="提醒消息")
    rounds_since_todo: int = Field(0, description="距离上次更新 todo 的轮次")


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[Any] = Field(None, description="额外详情")


class ErrorEvent(ServerMessage):
    """错误事件"""
    type: Literal["error"] = "error"
    dialog_id: Optional[str] = Field(None, description="对话 ID")
    message_id: Optional[str] = Field(None, description="消息 ID")
    error: ErrorDetail = Field(..., description="错误详情")


class AckEvent(ServerMessage):
    """确认事件"""
    type: Literal["ack"] = "ack"
    dialog_id: str = Field(..., description="对话 ID")
    client_id: str = Field(..., description="客户端 ID")
    server_id: Optional[str] = Field(None, description="服务端消息 ID")
    message: Optional[Any] = Field(None, description="消息数据")


class PongEvent(ServerMessage):
    """心跳响应"""
    type: Literal["pong"] = "pong"


# 服务端事件联合类型
ServerEvent = Union[
    DialogSnapshotEvent,
    StreamStartEvent,
    StreamDeltaEvent,
    StreamEndEvent,
    StreamResumedEvent,
    StreamTruncatedEvent,
    StatusChangeEvent,
    ToolCallUpdateEvent,
    TodoUpdatedEvent,
    TodoReminderEvent,
    ErrorEvent,
    AckEvent,
    PongEvent,
]


# ═════════════════════════════════════════════════════════════════════════════
# 错误处理辅助函数
# ═════════════════════════════════════════════════════════════════════════════


def get_error_message(code: ErrorCode) -> str:
    """获取错误码对应的消息"""
    return ERROR_MESSAGES.get(code, "未知错误")


def create_error_response(code: ErrorCode, details: Optional[Any] = None) -> ErrorEvent:
    """创建错误事件"""
    return ErrorEvent(
        type="error",
        timestamp=int(datetime.now().timestamp() * 1000),
        error=ErrorDetail(
            code=code.value,
            message=get_error_message(code),
            details=details,
        ),
    )
