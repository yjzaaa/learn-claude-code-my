"""
FastAPI 主应用

提供 REST API + WebSocket 的统一服务
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
from ..websocket.event_manager import (
    event_manager,
    RealTimeMessage,
    MessageType,
    MessageStatus,
)
from ..websocket.server import connection_manager, MessageHandler

# 导入Agent组件
try:
    from ..base import WorkspaceOps, tool
    from ..client import get_client, get_model
    from ..sql_agent_loop import SQLAgentLoop, SYSTEM, TOOLS
    from ..websocket.bridge import WebSocketBridge
except ImportError:
    from agents.base import WorkspaceOps, tool
    from agents.client import get_client, get_model
    from agents.sql_agent_loop import SQLAgentLoop, SYSTEM, TOOLS
    from agents.websocket.bridge import WebSocketBridge

from ..s05_skill_loading import SKILL_LOADER
from ..utils import (
    append_messages_jsonl,
    build_model_messages_from_dialog,
    get_last_user_message,
    is_stop_requested,
)

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"
OPS = WorkspaceOps(WORKDIR)
LOG_DIR = WORKDIR / ".logs"
LOG_FILE = LOG_DIR / "api_messages.jsonl"

# 全局Agent状态
agent_state = {
    "current_dialog_id": None,
    "is_running": False,
    "stop_requested": False,  # 新增：请求停止标志
    "pending_messages": {},   # 新增：等待处理的消息 {dialog_id: [messages]}
    "client": get_client(),
    "model": get_model(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 FastAPI Server starting...")
    yield
    # 关闭时
    logger.info("🛑 FastAPI Server shutting down...")
def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Agent API",
        description="Claude Code Agent REST API with WebSocket support",
        version="1.0.0",
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
            "message": "Agent API Server",
            "version": "1.0.0",
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

        # 广播新对话框创建
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

    @app.post("/api/dialogs/{dialog_id}/messages")
    async def send_message(dialog_id: str, request: Dict[str, Any]):
        """
        发送消息到对话框

        如果Agent未运行，会触发Agent处理
        如果Agent正在运行，会请求停止当前循环并排队新消息
        """
        content = request.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")

        # 检查对话框是否存在
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        # 创建用户消息
        user_message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.USER_MESSAGE,
            content=content,
            status=MessageStatus.COMPLETED,
        )
        event_manager.add_message_to_dialog(dialog_id, user_message)

        # 检查Agent是否正在运行
        if agent_state["is_running"]:
            # 如果正在运行，请求停止并排队消息
            logger.info(f"[send_message] Agent is running, requesting stop and queuing message for dialog {dialog_id}")
            agent_state["stop_requested"] = True

            # 将消息加入等待队列
            if dialog_id not in agent_state["pending_messages"]:
                agent_state["pending_messages"][dialog_id] = []
            agent_state["pending_messages"][dialog_id].append(content)

            return {
                "success": True,
                "data": {
                    "message_id": user_message.id,
                    "status": "queued",
                    "message": "Agent is busy, your message has been queued"
                }
            }
        else:
            # 异步触发Agent处理（不阻塞响应）
            # 注意：用户消息已添加到对话框，process_agent_request会从对话框读取历史
            await asyncio.sleep(0.1)  # 延迟100ms确保消息已写入
            asyncio.create_task(process_agent_request(dialog_id))

            return {
                "success": True,
                "data": {
                    "message_id": user_message.id,
                    "status": "processing",
                }
            }

    @app.get("/api/dialogs/{dialog_id}/messages")
    async def get_messages(dialog_id: str):
        """获取对话框的所有消息"""
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return {
            "success": True,
            "data": event_manager.filter_message_dicts([m.to_dict() for m in dialog.messages])
        }

    @app.delete("/api/dialogs/{dialog_id}")
    async def delete_dialog(dialog_id: str):
        """删除对话框"""
        # 这里可以实现删除逻辑
        await connection_manager.broadcast({
            "type": "dialog_deleted",
            "dialog_id": dialog_id
        })
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
        old_text = request.get("old_text")
        new_text = request.get("new_text")
        full_content = request.get("full_content")
        reason = request.get("reason", "")

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
    异步处理Agent请求

    处理流程：
    1. 发送系统事件（开始处理）
    2. 创建Agent循环（带WebSocket钩子）
    3. 流式处理响应
    4. 检查是否有待处理的消息，如有则继续处理
    5. 发送完成事件
    """
    logger.info(f"[process_agent_request] Starting for dialog_id={dialog_id}, is_running={agent_state['is_running']}")
    if agent_state["is_running"] and agent_state["current_dialog_id"] != dialog_id:
        # 如果Agent正在处理其他对话，发送提示
        logger.info(f"[process_agent_request] Agent is busy with other dialog, skipping")
        await _send_system_event(dialog_id, "Agent正在处理其他对话，请稍候...")
        return

    agent_state["is_running"] = True
    agent_state["current_dialog_id"] = dialog_id
    agent_state["stop_requested"] = False
    logger.info(f"[process_agent_request] Set is_running=True")
    # 创建WebSocket桥接器
    bridge = WebSocketBridge(dialog_id)
    await bridge.initialize(title="Skill Agent")

    def _on_after_round(messages: List[Dict[str, Any]], response: Any):
        bridge.on_after_round(messages, response)
        append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

    def _on_stop(messages: List[Dict[str, Any]], response: Any):
        bridge.on_stop(messages, response)
        append_messages_jsonl(messages, LOG_DIR, LOG_FILE)

    try:
        # 发送开始事件
        await _send_system_event(dialog_id, "开始处理请求", {"step": "start"})

        # 从对话框获取最后一条用户消息
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise ValueError(f"Dialog {dialog_id} not found")

        # 调试：打印所有消息
        logger.info(f"[process_agent_request] Dialog has {len(dialog.messages)} messages:")
        for i, msg in enumerate(dialog.messages):
            logger.info(f"  [{i}] type={msg.type}, content={msg.content[:50] if msg.content else '(empty)'}...")
        # 获取最后一条用户消息用于日志与基础校验
        last_user_message = get_last_user_message(dialog.messages)
        logger.info(f"[process_agent_request] Last user message: {last_user_message[:100] if last_user_message else 'NOT FOUND'}")
        if not last_user_message:
            raise ValueError("No user message found in dialog")

        # 构建多轮上下文，避免跨轮对话丢失。
        messages = build_model_messages_from_dialog(dialog.messages, max_messages=20)
        if not messages:
            messages = [{"role": "user", "content": last_user_message}]

        logger.info(
            "[process_agent_request] Processing with context messages: "
            f"count={len(messages)}, last_user={last_user_message[:100]}..."
        )
        # 创建带WebSocket钩子的Agent循环
        agent_loop = SQLAgentLoop(
            client=agent_state["client"],
            model=agent_state["model"],
            system=SYSTEM,
            tools=TOOLS,
            max_tokens=8000,
            max_rounds=30,  # finance 场景会多次读取技能/脚本，适当提高轮数避免提前中断
            # WebSocket钩子
            on_before_round=bridge.on_before_round,
            on_stream_token=None,  # 临时关闭按 token 流式推送，改为回合结束后统一落消息
            on_stream_text=bridge.on_stream_text,
            on_tool_call=bridge.on_tool_call,
            on_tool_result=bridge.on_tool_result,
            on_round_end=bridge.on_round_end,
            on_after_round=_on_after_round,
            on_stop=_on_stop,
            should_stop=lambda: is_stop_requested(agent_state),  # 新增：停止检查回调
        )

        # 在线程中运行Agent（避免阻塞事件循环）
        try:
            logger.info(f"[process_agent_request] Starting agent loop...")
            await asyncio.to_thread(agent_loop.run, messages)
            logger.info(f"[process_agent_request] Agent loop completed")
        except Exception as e:
            logger.info(f"[process_agent_request] Agent error: {e}")
            import traceback
            traceback.print_exc()
            await _send_system_event(dialog_id, f"Agent error: {str(e)}")

        # 发送完成事件
        await _send_system_event(dialog_id, "处理完成", {"step": "complete"})

    except Exception as e:
        logger.info(f"[process_agent_request] Outer error: {e}")
        import traceback
        traceback.print_exc()
        # 发送错误事件
        await _send_system_event(dialog_id, f"错误: {str(e)}", {"error": str(e)})

    finally:
        logger.info(f"[process_agent_request] Cleaning up, setting is_running=False")

        # 最终兜底：异常/中断路径也要收口 streaming 消息，避免前端一直显示生成中。
        try:
            if bridge.message_bridge and bridge._loop:
                asyncio.run_coroutine_threadsafe(
                    bridge.message_bridge.finalize_streaming_messages(),
                    bridge._loop,
                ).result(timeout=5)
        except Exception as e:
            logger.info(f"[process_agent_request] finalize_streaming_messages in finally failed: {e}")

        agent_state["is_running"] = False
        agent_state["current_dialog_id"] = None

        # 检查是否有待处理的消息
        pending = agent_state.get("pending_messages", {}).get(dialog_id, [])
        if pending:
            logger.info(f"[process_agent_request] Processing {len(pending)} pending messages")
            # 清空已处理的消息
            agent_state["pending_messages"][dialog_id] = []
            agent_state["stop_requested"] = False

            # 处理待处理的消息（用户消息已在send_message中添加）
            if pending:
                await _send_system_event(dialog_id, "处理新的用户消息", {"step": "new_message"})
                # 递归调用处理新消息
                asyncio.create_task(process_agent_request(dialog_id))


# ========== 辅助函数 ==========

async def _send_system_event(dialog_id: str, content: str, metadata: Optional[Dict] = None):
    """发送系统事件"""
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
        "agents.api.main:app",
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

