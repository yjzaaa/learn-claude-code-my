"""
FastAPI 主应用 - 使用类化响应模型

展示如何使用 agents.models.response 中的响应类
"""

from loguru import logger
import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 导入响应模型
from ..models import (
    ApiResponse,
    DialogListResponse,
    DialogDetailResponse,
    SkillListResponse,
    SkillInfoResponse,
    AgentStatusResponse,
    MessageSendResponse,
    ConfigUpdateResponse,
    success_response,
    error_response,
    PaginatedData,
)
from ..models.message import MessageType, MessageStatus

# 导入其他组件
from ..websocket.event_manager import event_manager
from ..websocket.server import connection_manager, MessageHandler
from ..base import WorkspaceOps
from ..client import get_client, get_model
from ..s05_skill_loading import SKILL_LOADER

WORKDIR = Path.cwd()
OPS = WorkspaceOps(WORKDIR)

# 全局状态
agent_state = {
    "current_dialog_id": None,
    "is_running": False,
    "stop_requested": False,
    "pending_messages": {},
    "client": get_client(),
    "model": get_model(),
}


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Agent API (With Class Responses)",
        version="2.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ========== REST API 端点（使用类化响应）==========

    @app.get("/api/dialogs")
    async def get_dialogs() -> Dict[str, Any]:
        """获取所有对话框 - 使用 DialogListResponse"""
        dialogs = event_manager.get_all_dialogs()
        dialog_dicts = [event_manager.to_client_dialog_dict(d) for d in dialogs]

        # 使用响应类
        response_data = DialogListResponse(
            dialogs=dialog_dicts,
            total=len(dialog_dicts),
        )
        return ApiResponse.success(data=response_data.to_dict()).to_dict()

    @app.get("/api/dialogs/{dialog_id}")
    async def get_dialog(dialog_id: str) -> Dict[str, Any]:
        """获取特定对话框 - 使用 DialogDetailResponse"""
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            # 使用错误响应
            return ApiResponse.failure(
                error="DIALOG_NOT_FOUND",
                message=f"Dialog {dialog_id} not found"
            ).to_dict()

        response_data = DialogDetailResponse(
            id=dialog.id,
            title=dialog.title,
            messages=[m.to_dict() for m in dialog.messages],
            status=dialog.status.value,
            created_at=dialog.created_at,
            updated_at=dialog.updated_at,
        )
        return ApiResponse.success(data=response_data.to_dict()).to_dict()

    @app.post("/api/dialogs")
    async def create_dialog(request: Dict[str, Any]) -> Dict[str, Any]:
        """创建新对话框"""
        try:
            title = request.get("title", "New Dialog")
            dialog_id = str(uuid.uuid4())
            dialog = event_manager.create_dialog(dialog_id, title)

            await connection_manager.broadcast({
                "type": "dialog_created",
                "dialog": dialog.to_dict()
            })

            response_data = DialogDetailResponse(
                id=dialog.id,
                title=dialog.title,
                messages=[],
                status=dialog.status.value,
                created_at=dialog.created_at,
                updated_at=dialog.updated_at,
            )
            return ApiResponse.success(
                data=response_data.to_dict(),
                message="Dialog created successfully"
            ).to_dict()
        except Exception as e:
            return ApiResponse.failure(
                error="CREATE_DIALOG_FAILED",
                message=str(e)
            ).to_dict()

    @app.get("/api/skills")
    async def get_skills() -> Dict[str, Any]:
        """获取所有可用技能 - 使用 SkillListResponse"""
        skills = SKILL_LOADER.list_skills()

        skill_infos = [
            SkillInfoResponse(
                name=skill.get("name", ""),
                description=skill.get("description", ""),
                version=skill.get("version", "1.0.0"),
                author=skill.get("author"),
                tags=skill.get("tags", []),
            )
            for skill in skills
        ]

        response_data = SkillListResponse(
            skills=skill_infos,
            total=len(skill_infos),
        )
        return ApiResponse.success(data=response_data.to_dict()).to_dict()

    @app.get("/api/skills/{name}")
    async def get_skill(name: str) -> Dict[str, Any]:
        """获取技能详情"""
        content = SKILL_LOADER.get_content(name)
        if content is None:
            return ApiResponse.failure(
                error="SKILL_NOT_FOUND",
                message=f"Skill '{name}' not found"
            ).to_dict()

        # 使用字典作为 data，因为技能内容比较灵活
        return ApiResponse.success(data={
            "name": name,
            "content": content,
        }).to_dict()

    @app.get("/api/agent/status")
    async def get_agent_status() -> Dict[str, Any]:
        """获取Agent状态 - 使用 AgentStatusResponse"""
        response_data = AgentStatusResponse(
            is_running=agent_state["is_running"],
            current_dialog_id=agent_state["current_dialog_id"],
            model=agent_state["model"],
            agent_type="master" if agent_state["is_running"] else None,
        )
        return ApiResponse.success(data=response_data.to_dict()).to_dict()

    @app.post("/api/agent/stop")
    async def stop_agent() -> Dict[str, Any]:
        """停止当前Agent运行"""
        if not agent_state["is_running"]:
            return ApiResponse.failure(
                error="AGENT_NOT_RUNNING",
                message="No agent is currently running"
            ).to_dict()

        agent_state["stop_requested"] = True
        return ApiResponse.success(
            data=None,
            message="Stop requested, Agent will stop at next check point"
        ).to_dict()

    @app.post("/api/dialogs/{dialog_id}/messages")
    async def send_message(dialog_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息到对话框 - 使用 MessageSendResponse"""
        content = request.get("content", "").strip()
        if not content:
            return ApiResponse.failure(
                error="INVALID_REQUEST",
                message="Content is required"
            ).to_dict()

        # 检查Agent是否正在运行
        queued = False
        if agent_state["is_running"]:
            agent_state["stop_requested"] = True
            if dialog_id not in agent_state["pending_messages"]:
                agent_state["pending_messages"][dialog_id] = []
            agent_state["pending_messages"][dialog_id].append(content)
            queued = True
            message_id = str(uuid.uuid4())
        else:
            # 创建消息
            from ..websocket.event_manager import RealTimeMessage
            user_message = RealTimeMessage(
                id=str(uuid.uuid4()),
                type=MessageType.USER_MESSAGE,
                content=content,
                status=MessageStatus.COMPLETED,
            )
            event_manager.add_message_to_dialog(dialog_id, user_message)
            message_id = user_message.id

            # 启动Agent处理
            asyncio.create_task(process_agent_request(dialog_id))

        response_data = MessageSendResponse(
            message_id=message_id,
            dialog_id=dialog_id,
            queued=queued,
        )

        if queued:
            return ApiResponse.success(
                data=response_data.to_dict(),
                message="Message queued, Agent will process after current task"
            ).to_dict()
        else:
            return ApiResponse.success(
                data=response_data.to_dict(),
                message="Message sent successfully"
            ).to_dict()

    @app.get("/api/config/push-type-map")
    async def get_push_type_map() -> Dict[str, Any]:
        """获取后端消息类型推送控制 map"""
        try:
            config = event_manager.get_push_type_map()
            response_data = ConfigUpdateResponse(
                updated_keys=[],
                config=config,
            )
            return ApiResponse.success(data=response_data.to_dict()).to_dict()
        except Exception as e:
            return ApiResponse.failure(
                error="CONFIG_FETCH_FAILED",
                message=str(e)
            ).to_dict()

    @app.post("/api/config/push-type-map")
    async def update_push_type_map(request: Dict[str, Any]) -> Dict[str, Any]:
        """更新后端消息类型推送控制 map"""
        updates = request.get("map", {})
        if not isinstance(updates, dict):
            return ApiResponse.failure(
                error="INVALID_REQUEST",
                message="'map' must be a JSON object"
            ).to_dict()

        try:
            merged = event_manager.update_push_type_map(updates)
            response_data = ConfigUpdateResponse(
                updated_keys=list(updates.keys()),
                config=merged,
            )
            return ApiResponse.success(
                data=response_data.to_dict(),
                message="Configuration updated successfully"
            ).to_dict()
        except ValueError as e:
            return ApiResponse.failure(
                error="INVALID_CONFIG",
                message=str(e)
            ).to_dict()

    # ========== WebSocket 端点 ==========

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """WebSocket连接端点"""
        await connection_manager.connect(websocket, client_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    import json
                    message = json.loads(data)
                    await MessageHandler.handle_message(websocket, client_id, message)
                except json.JSONDecodeError:
                    error_response = ApiResponse.failure(
                        error="INVALID_JSON",
                        message="Invalid JSON format"
                    )
                    await websocket.send_text(error_response.to_json())
        except WebSocketDisconnect:
            connection_manager.disconnect(client_id)

    return app


async def process_agent_request(dialog_id: str):
    """处理Agent请求"""
    logger.info(f"[process_agent_request] Starting for dialog_id={dialog_id}")
    # ... 处理逻辑


# 创建应用
app = create_app()


# 快捷使用示例
if __name__ == "__main__":
    # 示例：直接创建响应
    from ..models import RealtimeMessage

    # 成功响应
    msg = RealtimeMessage.create(
        msg_type=MessageType.ASSISTANT_TEXT,
        content="Hello",
    )
    response = ApiResponse.success(data=msg.to_dict())
    print(response.to_json())

    # 错误响应
    error = ApiResponse.failure(
        error="NOT_FOUND",
        message="Resource not found"
    )
    print(error.to_json())

    # 分页响应
    items = [{"id": i, "name": f"Item {i}"} for i in range(10)]
    paginated = PaginatedData(items=items, total=100, page=1, page_size=10)
    page_response = ApiResponse.success(data=paginated.to_dict())
    print(page_response.to_json())
