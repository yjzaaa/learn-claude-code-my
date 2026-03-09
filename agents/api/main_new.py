"""
FastAPI 主应用 (重构版)

后端状态管理架构 - 前端纯渲染设计
"""

from loguru import logger
import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 导入新的状态管理类型
from ..models.dialog_types import (
    DialogSession,
    DialogStatus,
    Message,
    MessageStatus,
    Role,
    ContentType,
    ToolCall,
    ToolCallStatus,
)
from ..api.state_managed_bridge import (
    StateManagedAgentBridge,
    DialogStore,
    dialog_store,
)

# 导入 WebSocket 组件
from ..websocket.server import connection_manager

# 导入 Agent 组件
try:
    from ..agent.s02_with_skill_loader import S02WithSkillLoaderAgent
    from ..utils.agent_helpers import get_last_user_message
    from ..s05_skill_loading import SKILL_LOADER
except ImportError:
    from agents.agent.s02_with_skill_loader import S02WithSkillLoaderAgent
    from agents.utils.agent_helpers import get_last_user_message
    from agents.s05_skill_loading import SKILL_LOADER


def _get_agent_name() -> str:
    """获取 Agent 名称"""
    return S02WithSkillLoaderAgent.__name__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 FastAPI Server starting (重构版)...")
    yield
    logger.info("🛑 FastAPI Server shutting down...")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Agent API (重构版)",
        description="Claude Code Agent REST API with Backend State Management",
        version="3.0.0",
        lifespan=lifespan,
    )

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ========== REST API 端点 ==========

    @app.get("/")
    async def root():
        """根端点"""
        return {
            "message": "Agent API Server (重构版 - 后端状态管理)",
            "version": "3.0.0",
            "endpoints": {
                "dialogs": "/api/dialogs",
                "skills": "/api/skills",
                "agent": "/api/agent/status",
                "websocket": "/ws/{client_id}",
            }
        }

    # ---- 对话框 API ----

    @app.get("/api/dialogs")
    async def get_dialogs():
        """获取所有对话框列表"""
        summaries = dialog_store.list_dialogs()
        return {
            "success": True,
            "data": [s.to_dict() for s in summaries]
        }

    @app.post("/api/dialogs")
    async def create_dialog(request: Dict[str, Any]):
        """创建新对话框"""
        title = request.get("title", "新对话")
        dialog_id = str(uuid.uuid4())

        bridge = dialog_store.create_dialog(
            dialog_id=dialog_id,
            title=title,
            agent_name=_get_agent_name(),
        )

        # 立即推送初始快照
        bridge._push_snapshot()

        return {
            "success": True,
            "data": bridge.get_session().to_dict()
        }

    @app.get("/api/dialogs/{dialog_id}")
    async def get_dialog(dialog_id: str):
        """获取特定对话框完整状态"""
        session = dialog_store.get_session(dialog_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return {
            "success": True,
            "data": session.to_dict()
        }

    @app.post("/api/dialogs/{dialog_id}/messages")
    async def send_message(dialog_id: str, request: Dict[str, Any]):
        """
        发送消息到对话框

        请求体:
            {
                "content": "用户消息内容"
            }
        """
        content = request.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")

        # 获取或创建 Bridge
        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            # 如果对话框不存在，创建一个新的
            bridge = dialog_store.create_dialog(
                dialog_id=dialog_id,
                title="Agent 对话",
                agent_name=_get_agent_name(),
            )

        # 处理用户输入（这会推送 snapshot）
        bridge.on_user_input(content)

        # 异步启动 Agent 处理
        asyncio.create_task(process_agent_request(dialog_id, bridge))

        return {
            "success": True,
            "data": {
                "dialog_id": dialog_id,
                "status": bridge.get_session().status.value,
            }
        }

    @app.post("/api/dialogs/{dialog_id}/stop")
    async def stop_dialog(dialog_id: str):
        """停止当前对话框的 Agent 运行"""
        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            raise HTTPException(status_code=404, detail="Dialog not found")

        bridge.on_stop()

        return {
            "success": True,
            "data": bridge.get_session().to_dict()
        }

    @app.delete("/api/dialogs/{dialog_id}")
    async def delete_dialog(dialog_id: str):
        """删除对话框"""
        success = dialog_store.delete_dialog(dialog_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return {
            "success": True,
            "message": "Dialog deleted"
        }

    # ---- Skills API ----

    @app.get("/api/skills")
    async def get_skills():
        """获取所有可用的skills"""
        skills = []
        for name, skill in SKILL_LOADER.skills.items():
            skills.append({
                "name": name,
                "description": skill["meta"].get("description", "No description"),
                "tags": skill["meta"].get("tags", ""),
                "path": skill["path"],
            })

        return {
            "success": True,
            "data": skills
        }

    @app.get("/api/skills/{skill_name}")
    async def get_skill(skill_name: str):
        """获取特定skill的详情"""
        content = SKILL_LOADER.get_content(skill_name)
        if content.startswith("Error:"):
            raise HTTPException(status_code=404, detail="Skill not found")

        return {
            "success": True,
            "data": {
                "name": skill_name,
                "content": content,
            }
        }

    @app.post("/api/skills/{skill_name}/load")
    async def load_skill(skill_name: str):
        """加载skill（触发工具调用）"""
        content = SKILL_LOADER.get_content(skill_name)
        if content.startswith("Error:"):
            raise HTTPException(status_code=404, detail="Skill not found")

        return {
            "success": True,
            "data": {
                "name": skill_name,
                "content": content,
            }
        }

    @app.post("/api/skills/{skill_name}/update")
    async def update_skill(skill_name: str, request: Dict[str, Any]):
        """更新skill"""
        old_text = request.get("old_text") or ""
        new_text = request.get("new_text") or ""
        full_content = request.get("full_content") or ""
        reason = request.get("reason", "") or ""

        result = SKILL_LOADER.update_skill(
            skill_name,
            old_text=old_text,
            new_text=new_text,
            full_content=full_content,
            reason=reason
        )

        if result.startswith("Error:"):
            raise HTTPException(status_code=400, detail=result)

        return {
            "success": True,
            "data": {
                "message": result
            }
        }

    # ---- Agent控制 API ----

    @app.get("/api/agent/status")
    async def get_agent_status():
        """获取Agent状态 - 返回所有活跃对话框的状态"""
        dialogs = dialog_store.list_dialogs()
        active_dialogs = [
            {
                "dialog_id": d.id,
                "status": dialog_store.get_session(d.id).status.value if dialog_store.get_session(d.id) else "unknown"
            }
            for d in dialogs
        ]

        return {
            "success": True,
            "data": {
                "active_dialogs": active_dialogs,
                "total_dialogs": len(dialogs),
            }
        }

    @app.post("/api/agent/stop")
    async def stop_agent():
        """停止当前所有运行中的Agent"""
        stopped = []
        for summary in dialog_store.list_dialogs():
            bridge = dialog_store.get_bridge(summary.id)
            if bridge and bridge.get_session().status in [DialogStatus.THINKING, DialogStatus.TOOL_CALLING]:
                bridge.on_stop()
                stopped.append(summary.id)

        return {
            "success": True,
            "data": {
                "stopped_dialogs": stopped,
                "count": len(stopped)
            }
        }

    # ========== WebSocket 端点 ==========

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """
        WebSocket连接端点

        客户端事件:
        - subscribe: 订阅对话框
        - user:input: 用户输入
        - stop: 停止 Agent
        """
        await connection_manager.connect(websocket, client_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    import json
                    message = json.loads(data)
                    await handle_websocket_message(websocket, client_id, message)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": {"code": "INVALID_JSON", "message": "Invalid JSON"}
                    }))
        except WebSocketDisconnect:
            connection_manager.disconnect(client_id)

    return app


async def handle_websocket_message(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """处理 WebSocket 消息"""
    msg_type = message.get("type")
    dialog_id = message.get("dialog_id")

    if msg_type == "subscribe":
        # 订阅对话框 - 立即推送当前快照
        bridge = dialog_store.get_bridge(dialog_id)
        if bridge:
            await websocket.send_json(bridge.to_snapshot())
        else:
            await websocket.send_json({
                "type": "error",
                "dialog_id": dialog_id,
                "error": {"code": "DIALOG_NOT_FOUND", "message": "Dialog not found"}
            })

    elif msg_type == "user:input":
        # 用户输入
        content = message.get("content", "")
        if not content or not dialog_id:
            return

        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            bridge = dialog_store.create_dialog(
                dialog_id=dialog_id,
                title="Agent 对话",
                agent_name=_get_agent_name(),
            )

        # 处理用户输入
        bridge.on_user_input(content)

        # 启动 Agent 处理
        asyncio.create_task(process_agent_request(dialog_id, bridge))

    elif msg_type == "stop":
        # 停止 Agent
        bridge = dialog_store.get_bridge(dialog_id)
        if bridge:
            bridge.on_stop()

    else:
        # 未知消息类型
        await websocket.send_json({
            "type": "error",
            "error": {"code": "UNKNOWN_TYPE", "message": f"Unknown message type: {msg_type}"}
        })


async def process_agent_request(dialog_id: str, bridge: StateManagedAgentBridge):
    """
    异步处理 Agent 请求

    处理流程：
    1. 从 Bridge 获取用户输入
    2. 创建 Agent 并运行
    3. Hook 处理状态变更并广播
    4. 完成后更新状态
    """
    try:
        logger.info(f"[ProcessAgent] Starting for dialog {dialog_id}")

        # 获取最后一条用户消息
        session = bridge.get_session()
        user_messages = [m for m in session.messages if m.role == Role.USER]
        if not user_messages:
            logger.warning(f"[ProcessAgent] No user message found")
            return

        last_user_message = user_messages[-1].content

        # 创建 Agent，设置 Hook 委托
        agent = S02WithSkillLoaderAgent()
        agent.set_hook_delegate(bridge)

        # 运行 Agent
        try:
            logger.info(f"[ProcessAgent] Running agent...")
            messages = [{"role": "user", "content": last_user_message}]
            await agent.arun(messages)
            logger.info(f"[ProcessAgent] Agent completed")
        except asyncio.CancelledError:
            logger.info(f"[ProcessAgent] Agent was cancelled")
            bridge.on_stop()
        except Exception as e:
            logger.error(f"[ProcessAgent] Agent error: {e}")
            import traceback
            traceback.print_exc()
            bridge.on_error(e)

    except Exception as e:
        logger.error(f"[ProcessAgent] Outer error: {e}")
        import traceback
        traceback.print_exc()
        bridge.on_error(e)


# 创建全局应用实例
app = create_app()


async def start_api_server(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """启动API服务器"""
    import uvicorn
    config = uvicorn.Config(
        "agents.api.main_new:app",
        host=host,
        port=port,
        log_level="info",
        reload=reload,
        reload_dirs=["agents"] if reload else None,
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio
    asyncio.run(start_api_server())
