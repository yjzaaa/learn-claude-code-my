"""
FastAPI 主应用 - 优化版

使用新架构 BaseInteractiveAgent，简化代码:
- 无需手动管理 WebSocket 桥接器
- 无需手动处理回调函数
- Agent 自动处理前端交互
"""

from loguru import logger
import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 导入WebSocket组件
from ..websocket.event_manager import event_manager
from ..websocket.server import connection_manager, MessageHandler

# 导入Agent组件（新架构）
try:
    from ..base import WorkspaceOps
    from ..client import get_client, get_model
    from ..sql_agent_interactive import InteractiveSQLAgent, MASTER_SYSTEM
except ImportError:
    from agents.base import WorkspaceOps
    from agents.client import get_client, get_model
    from agents.sql_agent_interactive import InteractiveSQLAgent, MASTER_SYSTEM

from ..s05_skill_loading import SKILL_LOADER
from ..utils import (
    append_messages_jsonl,
    build_model_messages_from_dialog,
    get_last_user_message,
)

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"
OPS = WorkspaceOps(WORKDIR)
LOG_DIR = WORKDIR / ".logs"
LOG_FILE = LOG_DIR / "api_messages.jsonl"

# 全局Agent状态（简化版）
agent_state = {
    "current_dialog_id": None,
    "is_running": False,
    "stop_requested": False,
    "pending_messages": {},
    "client": get_client(),
    "model": get_model(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 FastAPI Server starting...")
    yield
    logger.info("🛑 FastAPI Server shutting down...")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Agent API",
        description="Claude Code Agent REST API with WebSocket support",
        version="2.0.0",
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
            "message": "Agent API Server (Optimized)",
            "version": "2.0.0",
            "architecture": "BaseInteractiveAgent",
            "endpoints": {
                "dialogs": "/api/dialogs",
                "skills": "/api/skills",
                "websocket": "/ws/{client_id}",
            }
        }

    @app.get("/api/config/push-type-map")
    async def get_push_type_map():
        """获取后端消息类型推送控制 map。"""
        return {
            "success": True,
            "data": event_manager.get_push_type_map(),
        }

    @app.post("/api/config/push-type-map")
    async def update_push_type_map(request: Dict[str, Any]):
        """更新后端消息类型推送控制 map。"""
        updates = request.get("map", {})
        if not isinstance(updates, dict):
            raise HTTPException(status_code=400, detail="'map' must be a JSON object")

        try:
            merged = event_manager.update_push_type_map(updates)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return {
            "success": True,
            "data": merged,
        }

    # ---- 对话框 API ----

    @app.get("/api/dialogs")
    async def get_dialogs():
        """获取所有对话框"""
        dialogs = event_manager.get_all_dialogs()
        return {
            "success": True,
            "data": [event_manager.to_client_dialog_dict(d) for d in dialogs]
        }

    @app.post("/api/dialogs")
    async def create_dialog(request: Dict[str, Any]):
        """创建新对话框"""
        title = request.get("title", "New Dialog")
        dialog_id = str(uuid.uuid4())
        dialog = event_manager.create_dialog(dialog_id, title)

        await connection_manager.broadcast({
            "type": "dialog_created",
            "dialog": dialog.to_dict()
        })

        return {
            "success": True,
            "data": dialog.to_dict()
        }

    @app.get("/api/dialogs/{dialog_id}")
    async def get_dialog(dialog_id: str):
        """获取特定对话框"""
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")
        return {
            "success": True,
            "data": event_manager.to_client_dialog_dict(dialog)
        }

    @app.delete("/api/dialogs/{dialog_id}")
    async def delete_dialog(dialog_id: str):
        """删除对话框"""
        # 删除逻辑...
        await connection_manager.broadcast({
            "type": "dialog_deleted",
            "dialog_id": dialog_id
        })
        return {"success": True, "message": "Dialog deleted"}

    @app.post("/api/dialogs/{dialog_id}/messages")
    async def send_message(dialog_id: str, request: Dict[str, Any]):
        """发送消息到对话框"""
        content = request.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")

        # 检查Agent是否正在运行
        if agent_state["is_running"]:
            agent_state["stop_requested"] = True
            if dialog_id not in agent_state["pending_messages"]:
                agent_state["pending_messages"][dialog_id] = []
            agent_state["pending_messages"][dialog_id].append(content)
            return {
                "success": True,
                "message": "Stop requested, message queued",
                "data": {"queued": True}
            }

        # 添加到对话框
        from ..websocket.event_manager import RealTimeMessage, MessageType, MessageStatus
        user_message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.USER_MESSAGE,
            content=content,
            status=MessageStatus.COMPLETED,
        )
        event_manager.add_message_to_dialog(dialog_id, user_message)

        # 启动Agent处理
        asyncio.create_task(process_agent_request(dialog_id))

        return {
            "success": True,
            "data": {"message_id": user_message.id}
        }

    # ---- Skills API ----

    @app.get("/api/skills")
    async def get_skills():
        """获取所有可用技能"""
        return {
            "success": True,
            "data": SKILL_LOADER.list_skills()
        }

    @app.get("/api/skills/{name}")
    async def get_skill(name: str):
        """获取技能详情"""
        content = SKILL_LOADER.get_content(name)
        if content is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {
            "success": True,
            "data": {"name": name, "content": content}
        }

    @app.post("/api/skills/{name}/load")
    async def load_skill(name: str, request: Dict[str, Any]):
        """加载技能到对话"""
        dialog_id = request.get("dialog_id")
        if not dialog_id:
            raise HTTPException(status_code=400, detail="dialog_id is required")

        content = SKILL_LOADER.get_content(name)
        if content is None:
            raise HTTPException(status_code=404, detail="Skill not found")

        from ..websocket.event_manager import RealTimeMessage, MessageType, MessageStatus
        message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.SYSTEM_EVENT,
            content=f"Skill '{name}' loaded",
            status=MessageStatus.COMPLETED,
            metadata={"skill_name": name, "skill_content": content}
        )
        event_manager.add_message_to_dialog(dialog_id, message)

        return {
            "success": True,
            "data": {"message_id": message.id}
        }

    # ---- Agent Control API ----

    @app.get("/api/agent/status")
    async def get_agent_status():
        """获取Agent状态"""
        return {
            "success": True,
            "data": {
                "is_running": agent_state["is_running"],
                "current_dialog_id": agent_state["current_dialog_id"],
                "model": agent_state["model"],
            }
        }

    @app.post("/api/agent/stop")
    async def stop_agent():
        """停止当前Agent运行"""
        logger.info(f"[stop_agent] Stop requested! is_running={agent_state['is_running']}")
        agent_state["stop_requested"] = True
        return {
            "success": True,
            "message": "Stop requested, Agent will stop at next check point"
        }

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
                    await websocket.send_text('{"type": "error", "message": "Invalid JSON"}')
        except WebSocketDisconnect:
            connection_manager.disconnect(client_id)

    return app


async def process_agent_request(dialog_id: str):
    """
    异步处理Agent请求 - 优化版

    使用 InteractiveSQLAgent，自动处理前端交互
    代码大幅简化，无需手动管理回调
    """
    logger.info(f"[process_agent_request] Starting for dialog_id={dialog_id}")

    # 检查是否已有其他对话在运行
    if agent_state["is_running"] and agent_state["current_dialog_id"] != dialog_id:
        await _send_system_event(dialog_id, "Agent正在处理其他对话，请稍候...")
        return

    # 设置状态
    agent_state["is_running"] = True
    agent_state["current_dialog_id"] = dialog_id
    agent_state["stop_requested"] = False

    try:
        # 获取对话框
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise ValueError(f"Dialog {dialog_id} not found")

        # 构建上下文消息
        messages = build_model_messages_from_dialog(dialog.messages, max_messages=20)
        if not messages:
            last_msg = get_last_user_message(dialog.messages)
            if last_msg:
                messages = [{"role": "user", "content": last_msg}]

        logger.info(f"[process_agent_request] Processing {len(messages)} context messages")

        # 创建 Agent（新架构，自动处理前端交互）
        agent = InteractiveSQLAgent(
            client=agent_state["client"],
            model=agent_state["model"],
            dialog_id=dialog_id,
            system=MASTER_SYSTEM,
            max_tokens=8000,
            max_rounds=30,
            enable_learning=True,
        )

        # 在线程中运行（避免阻塞事件循环）
        try:
            await asyncio.to_thread(agent.run_conversation, messages)
            logger.info("[process_agent_request] Agent completed successfully")
        except Exception as e:
            logger.error(f"[process_agent_request] Agent error: {e}")
            await _send_system_event(dialog_id, f"Agent错误: {str(e)}", {"error": str(e)})

        # 输出学习系统摘要
        learning_summary = agent.get_learning_summary()
        if learning_summary:
            logger.info(f"[process_agent_request] Learning summary: {learning_summary}")

    except Exception as e:
        logger.error(f"[process_agent_request] Outer error: {e}")
        await _send_system_event(dialog_id, f"系统错误: {str(e)}", {"error": str(e)})

    finally:
        logger.info("[process_agent_request] Cleaning up")
        agent_state["is_running"] = False
        agent_state["current_dialog_id"] = None

        # 处理待处理的消息
        await _process_pending_messages(dialog_id)


async def _process_pending_messages(dialog_id: str):
    """处理待处理的消息"""
    pending = agent_state.get("pending_messages", {}).get(dialog_id, [])
    if pending:
        logger.info(f"[process_agent_request] Processing {len(pending)} pending messages")
        agent_state["pending_messages"][dialog_id] = []
        agent_state["stop_requested"] = False

        # 添加新的用户消息
        from ..websocket.event_manager import RealTimeMessage, MessageType, MessageStatus
        for content in pending:
            msg = RealTimeMessage(
                id=str(uuid.uuid4()),
                type=MessageType.USER_MESSAGE,
                content=content,
                status=MessageStatus.COMPLETED,
            )
            event_manager.add_message_to_dialog(dialog_id, msg)

        # 递归处理
        await _send_system_event(dialog_id, "处理新的用户消息", {"step": "new_message"})
        asyncio.create_task(process_agent_request(dialog_id))


async def _send_system_event(dialog_id: str, content: str, metadata: Optional[Dict] = None):
    """发送系统事件"""
    from ..websocket.event_manager import RealTimeMessage, MessageType, MessageStatus
    message = RealTimeMessage(
        id=str(uuid.uuid4()),
        type=MessageType.SYSTEM_EVENT,
        content=content,
        status=MessageStatus.COMPLETED,
        metadata=metadata or {},
    )
    event_manager.add_message_to_dialog(dialog_id, message)


# 创建全局应用实例
app = create_app()


async def start_api_server(host: str = "0.0.0.0", port: int = 8001, reload: bool = False):
    """启动API服务器"""
    import uvicorn
    config = uvicorn.Config(
        "agents.api.main_optimized:app",
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
