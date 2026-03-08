"""
FastAPI 主应用 (OpenAI 风格)

提供 REST API + WebSocket 的统一服务
使用 ChatMessage 和 ChatEvent 进行前后端通信
"""

from loguru import logger
import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 导入 OpenAI 风格类型
from ..models import ChatMessage, ChatEvent

# 导入WebSocket组件
from ..websocket.event_manager import event_manager
from ..websocket.server import connection_manager, MessageHandler
try:
    from .agent_bridge import AgentWebSocketBridge
except ImportError:
    from agents.api.agent_bridge import AgentWebSocketBridge

# 导入Agent组件
try:
    from ..providers import create_provider_from_env
    from ..s05_skill_loading import SKILL_LOADER
    from ..s03_todo_write import TodoAgent
    from ..utils.agent_helpers import get_last_user_message
except ImportError:
    from agents.providers import create_provider_from_env
    from agents.s05_skill_loading import SKILL_LOADER
    from agents.s03_todo_write import TodoAgent
    from agents.utils.agent_helpers import get_last_user_message

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"

# 初始化 provider
provider = create_provider_from_env()

# 全局Agent状态
agent_state = {
    "current_dialog_id": None,
    "is_running": False,
    "stop_requested": False,
    "pending_messages": {},
    "provider": provider,
    "model": provider.default_model if provider else "deepseek-chat",
    "current_agent": None,
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
        description="Claude Code Agent REST API with WebSocket support (OpenAI style)",
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
            "message": "Agent API Server (OpenAI style)",
            "version": "2.0.0",
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
        发送消息到对话框 (OpenAI 风格)

        请求体:
            {
                "content": "用户消息内容",
                "role": "user"  // 可选，默认为 "user"
            }
        """
        content = request.get("content", "")
        role = request.get("role", "user")

        if not content:
            raise HTTPException(status_code=400, detail="Content is required")

        # 检查对话框是否存在
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        # 创建用户消息 (OpenAI 风格)
        user_message = ChatMessage.user(content)

        # 添加到对话框
        event_manager.add_chat_message(dialog_id, user_message)

        # 检查Agent是否正在运行
        if agent_state["is_running"]:
            logger.info(f"[send_message] Agent is running, requesting stop and queuing message for dialog {dialog_id}")
            agent_state["stop_requested"] = True

            # 将消息加入等待队列
            if dialog_id not in agent_state["pending_messages"]:
                agent_state["pending_messages"][dialog_id] = []
            agent_state["pending_messages"][dialog_id].append(content)

            return {
                "success": True,
                "data": {
                    "message": user_message.to_dict(),
                    "status": "queued",
                    "message": "Agent is busy, your message has been queued"
                }
            }
        else:
            # 异步触发Agent处理（不阻塞响应）
            await asyncio.sleep(0.1)
            asyncio.create_task(process_agent_request(dialog_id))

            return {
                "success": True,
                "data": {
                    "message": user_message.to_dict(),
                    "status": "processing",
                }
            }

    @app.get("/api/dialogs/{dialog_id}/messages")
    async def get_messages(dialog_id: str):
        """获取对话框的所有消息 (OpenAI 风格)"""
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        # 直接返回 OpenAI 风格消息
        messages = [msg.to_dict() for msg in dialog.messages]

        return {
            "success": True,
            "data": messages
        }

    @app.delete("/api/dialogs/{dialog_id}")
    async def delete_dialog(dialog_id: str):
        """删除对话框"""
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
        import threading
        logger.info(f"[stop_agent] Stop requested! Current is_running={agent_state.get('is_running')}, dialog_id={agent_state.get('current_dialog_id')}, thread={threading.current_thread().name}")

        # 1. 设置全局停止标志
        agent_state["stop_requested"] = True
        logger.info(f"[stop_agent] Setting stop_requested=True")

        # 2. 调用当前Agent的request_stop()方法（如果存在）
        current_agent = agent_state.get("current_agent")
        if current_agent:
            logger.info(f"[stop_agent] Calling request_stop() on {type(current_agent).__name__}")
            try:
                current_agent.request_stop()
                logger.info("[stop_agent] request_stop() called successfully")
            except Exception as e:
                logger.error(f"[stop_agent] Error calling request_stop(): {e}")
        else:
            logger.info("[stop_agent] No current_agent found")

        return {
            "success": True,
            "message": "Stop requested, Agent will stop at next check point"
        }

    # ========== WebSocket 端点 ==========

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """WebSocket连接端点 (OpenAI 风格)"""
        await connection_manager.connect(websocket, client_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    import json
                    message = json.loads(data)
                    await handle_websocket_message(websocket, client_id, message)
                except json.JSONDecodeError:
                    await websocket.send_text('{"type": "error", "message": "Invalid JSON"}')
        except WebSocketDisconnect:
            connection_manager.disconnect(client_id)

    return app


async def handle_websocket_message(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """处理 WebSocket 消息 (OpenAI 风格)"""
    msg_type = message.get("type")

    if msg_type == "chat.message":
        # 用户发送消息
        dialog_id = message.get("dialog_id")
        chat_message = message.get("message", {})

        if dialog_id and chat_message.get("content"):
            # 创建 ChatEvent
            event = ChatEvent(
                type="message",
                dialog_id=dialog_id,
                message=ChatMessage.from_dict(chat_message),
            )

            # 广播事件
            await connection_manager.broadcast({
                "type": "chat:event",
                "event": event.to_dict(),
            })

    elif msg_type == "chat.subscribe":
        # 订阅对话框
        dialog_id = message.get("dialog_id")
        if dialog_id:
            dialog = event_manager.get_dialog(dialog_id)
            if dialog:
                await websocket.send_json({
                    "type": "dialog:subscribed",
                    "dialog_id": dialog_id,
                    "dialog": event_manager.to_client_dialog_dict(dialog),
                })

    else:
        # 委托给旧的消息处理器
        await MessageHandler.handle_message(websocket, client_id, message)


async def process_agent_request(dialog_id: str):
    """
    异步处理Agent请求 (OpenAI 风格)

    处理流程：
    1. 发送系统事件（开始处理）
    2. 创建Agent循环（带WebSocket钩子）
    3. 流式处理响应
    4. 检查是否有待处理的消息，如有则继续处理
    5. 发送完成事件
    """
    logger.info(f"[process_agent_request] Starting for dialog_id={dialog_id}, is_running={agent_state['is_running']}")

    if agent_state["is_running"] and agent_state["current_dialog_id"] != dialog_id:
        logger.info(f"[process_agent_request] Agent is busy with other dialog, skipping")
        await _send_system_event(dialog_id, "Agent正在处理其他对话，请稍候...")
        return

    agent_state["is_running"] = True
    agent_state["current_dialog_id"] = dialog_id
    agent_state["stop_requested"] = False

    try:
        # 发送开始事件
        await _send_system_event(dialog_id, "开始处理请求")

        # 从对话框获取最后一条用户消息
        dialog = event_manager.get_dialog(dialog_id)
        if not dialog:
            raise ValueError(f"Dialog {dialog_id} not found")

        # 调试：打印所有消息
        logger.info(f"[process_agent_request] Dialog has {len(dialog.messages)} messages")

        # 获取最后一条用户消息
        last_user_message = get_last_user_message(dialog.messages)
        content_preview = last_user_message[:100] if last_user_message else 'NOT FOUND'
        logger.info(f"[process_agent_request] Last user message: {content_preview}")

        if not last_user_message:
            raise ValueError("No user message found in dialog")

        # 从 Agent 类动态获取名称（避免创建两次实例）
        agent_name = TodoAgent.__name__

        # 创建 WebSocket Bridge，传入 agent_name
        bridge = AgentWebSocketBridge(dialog_id=dialog_id, agent_name=agent_name)

        # 创建 TodoAgent，传入 bridge 的钩子函数
        agent = TodoAgent(
            **bridge.get_hook_kwargs()
        )
        agent_state["current_agent"] = agent
        logger.info(f"[process_agent_request] Agent instance saved to agent_state")

        # 在线程中运行Agent
        try:
            logger.info(f"[process_agent_request] Starting TodoAgent...")
            messages = _build_messages_from_dialog(dialog)
            logger.info(f"[process_agent_request] Built messages from dialog history: {len(messages)} messages")
            await asyncio.to_thread(agent.run_with_inbox, messages)
            logger.info(f"[process_agent_request] TodoAgent completed")
        except Exception as e:
            logger.info(f"[process_agent_request] Agent error: {e}")
            import traceback
            traceback.print_exc()
            bridge.on_error(e)
            await _send_system_event(dialog_id, f"Agent error: {str(e)}")

        # 发送完成事件
        await _send_system_event(dialog_id, "处理完成")

    except Exception as e:
        logger.info(f"[process_agent_request] Outer error: {e}")
        import traceback
        traceback.print_exc()
        await _send_system_event(dialog_id, f"错误: {str(e)}")

    finally:
        logger.info(f"[process_agent_request] Cleaning up, setting is_running=False")
        agent_state["is_running"] = False
        agent_state["current_dialog_id"] = None
        agent_state["current_agent"] = None

        # 检查是否有待处理的消息
        pending = agent_state.get("pending_messages", {}).get(dialog_id, [])
        if pending:
            logger.info(f"[process_agent_request] Processing {len(pending)} pending messages")
            agent_state["pending_messages"][dialog_id] = []
            agent_state["stop_requested"] = False

            if pending:
                await _send_system_event(dialog_id, "处理新的用户消息")
                asyncio.create_task(process_agent_request(dialog_id))


def _build_messages_from_dialog(dialog) -> list:
    """从对话框历史构建消息列表，供Agent使用（OpenAI格式）"""
    messages = []
    for msg in dialog.messages:
        if msg.role == "user":
            messages.append({"role": "user", "content": msg.content or ""})
        elif msg.role == "assistant":
            assistant_msg = {"role": "assistant", "content": msg.content or ""}
            # 添加工具调用（如果有）
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.get("name", "unknown"),
                            "arguments": tc.function.get("arguments", "{}"),
                        }
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_msg)
        elif msg.role == "tool":
            messages.append({
                "role": "tool",
                "tool_call_id": msg.tool_call_id,
                "content": msg.content or ""
            })
    return messages


async def _send_system_event(dialog_id: str, content: str, metadata: Optional[Dict] = None):
    """发送系统事件 (OpenAI 风格)"""
    # 创建系统消息
    system_message = ChatMessage.system(content)
    event_manager.add_chat_message(dialog_id, system_message)

    # 同时发送 OpenAI 风格事件
    event = ChatEvent(
        type="system",
        dialog_id=dialog_id,
        message=system_message,
    )
    await connection_manager.broadcast({
        "type": "chat:event",
        "event": event.to_dict(),
    })


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
