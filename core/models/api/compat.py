"""
Compatibility Aliases - 向后兼容别名

为旧代码提供的导入别名。
"""
from .responses import (
    SendMessageData,
    SendMessageResponse,
    ResumeData,
    ResumeDialogResponse,
    AgentStatusItem,
    AgentStatusData,
    AgentStatusResponse,
    StopAgentData,
    StopAgentResponse,
    HealthResponse,
    SkillListResponse,
    PendingSkillEditsResponse,
    DecideSkillEditResponse,
    ListDialogsResponse,
    CreateDialogResponse,
    GetDialogResponse,
    DeleteDialogResponse,
    GetMessagesResponse,
    SkillItem,
    ResultModel,
    Response,
)
from .sse_events import (
    SkillEditPendingEvent,
    SkillEditResolvedEvent,
    TodoUpdatedEvent,
    TodoReminderEvent,
)

# 来自 response_models.py 的别名
APISendMessageData = SendMessageData
APISendMessageResponse = SendMessageResponse
APIResumeData = ResumeData
APIResumeDialogResponse = ResumeDialogResponse
APIAgentStatusItem = AgentStatusItem
APIAgentStatusData = AgentStatusData
APIAgentStatusResponse = AgentStatusResponse
APIStopAgentData = StopAgentData
APIStopAgentResponse = StopAgentResponse
APIHealthResponse = HealthResponse
APISkillListResponse = SkillListResponse
APIPendingSkillEditsResponse = PendingSkillEditsResponse
APIDecideSkillEditResponse = DecideSkillEditResponse
APIListDialogsResponse = ListDialogsResponse
APICreateDialogResponse = CreateDialogResponse
APIGetDialogResponse = GetDialogResponse
APIDeleteDialogResponse = DeleteDialogResponse
APIGetMessagesResponse = GetMessagesResponse
SkillItemModel = SkillItem
HITLResultModel = Response  # 简化兼容

# 来自 dto.py 的别名
TodoResult = Response
DecisionResult = ResultModel
HITLResult = Response
BaseResult = Response
SkillEditPendingEventDTO = SkillEditPendingEvent
SkillEditResolvedEventDTO = SkillEditResolvedEvent
TodoUpdatedEventDTO = TodoUpdatedEvent
TodoReminderEventDTO = TodoReminderEvent
