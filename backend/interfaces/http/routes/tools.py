"""
Tools Routes - 工具管理

提供工具查询、执行等端点。
"""

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.domain.models.agent.tool import ToolExecutionResult

router = APIRouter(tags=["tools"])


class ToolResponse(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ExecuteToolRequest(BaseModel):
    name: str
    arguments: dict[str, Any]


@router.get("/list", response_model=list[ToolResponse])
async def list_tools(request: Request):
    """列出所有工具"""
    engine = request.app.state.engine

    tools = engine.list_tools()
    return [
        ToolResponse(
            name=t.name,
            description=t.description,
            parameters=t.parameters,
        )
        for t in tools
    ]


@router.post("/execute")
async def execute_tool(request: Request, body: ExecuteToolRequest):
    """执行工具"""
    engine = request.app.state.engine

    # 创建 ToolCall 并执行
    from backend.domain.models import ToolCall

    tool_call = ToolCall.create(name=body.name, arguments=body.arguments)

    result = await engine.tool_manager.execute("manual", tool_call)

    return ToolExecutionResult(
        tool_call_id=tool_call.id,
        tool_name=body.name,
        result=str(result),
    )
