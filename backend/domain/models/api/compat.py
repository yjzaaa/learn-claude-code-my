"""
Compatibility Aliases - 向后兼容别名

为旧代码提供的导入别名。
"""

from .responses import (
    AgentStatusData,
    AgentStatusItem,
    AgentStatusResponse,
    CreateDialogResponse,
    DecideSkillEditResponse,
    DeleteDialogResponse,
    GetDialogResponse,
    GetMessagesResponse,
    HealthResponse,
    ListDialogsResponse,
    PendingSkillEditsResponse,
    Response,
    ResultModel,
    ResumeData,
    ResumeDialogResponse,
    SendMessageData,
    SendMessageResponse,
    SkillItem,
    SkillListResponse,
    StopAgentData,
    StopAgentResponse,
)
from .sse_events import (
    SkillEditPendingEvent,
    SkillEditResolvedEvent,
    TodoReminderEvent,
    TodoUpdatedEvent,
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
