"""
FastAPI 主应用 (OpenAI 风格)

提供 REST API + WebSocket 的统一服务
使用 ChatMessage 和 ChatEvent 进行前后端通信
"""

from loguru import logger
import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 导入 OpenAI 风格类型
from ..models import ChatMessage, ChatEvent

# 导入WebSocket组件
from ..websocket.event_manager import event_manager
from ..websocket.server import connection_manager, MessageHandler
try:
    from ..hooks.agent_websocket_bridge import AgentWebSocketBridge
    from ..session.session_manager import SessionManager
    from ..hooks.composite.composite_hooks import CompositeHooks
    from ..hooks.session_history_hook import SessionHistoryHook
except ImportError:
    from agents.hooks.agent_websocket_bridge import AgentWebSocketBridge
    from agents.session.session_manager import SessionManager
    from agents.hooks.composite.composite_hooks import CompositeHooks
    from agents.hooks.session_history_hook import SessionHistoryHook

# 导入Agent组件
try:
    from ..providers import create_provider_from_env
    from ..s05_skill_loading import SKILL_LOADER
    from ..agent.s02_with_skill_loader import S02WithSkillLoaderAgent
    from ..utils.agent_helpers import get_last_user_message
except ImportError:
    from agents.providers import create_provider_from_env
    from agents.s05_skill_loading import SKILL_LOADER
    from agents.agent.s02_with_skill_loader import S02WithSkillLoaderAgent
    from agents.utils.agent_helpers import get_last_user_message

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"

# 初始化 provider
provider = create_provider_from_env()

def _build_session_manager() -> SessionManager:
    """构建默认 SessionManager。"""
    window_rounds_raw = os.getenv("SESSION_WINDOW_ROUNDS", "10")
    try:
        window_rounds = max(1, int(window_rounds_raw))
    except ValueError:
        window_rounds = 10

    return SessionManager(
        provider=provider,
        model=(provider.default_model if provider and provider.default_model else "deepseek-chat"),
        window_rounds=window_rounds,
    )


# 模块级默认实例，app.state 初始化前可用
_default_session_manager = _build_session_manager()


def _get_session_manager() -> SessionManager:
    """统一获取 SessionManager，优先 app.state。"""
    app_obj = globals().get("app")
    if app_obj is not None and hasattr(app_obj, "state") and hasattr(app_obj.state, "session_manager"):
        return app_obj.state.session_manager
    return _default_session_manager


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

    # 挂载到应用状态，便于后续替换/注入
    app.state.session_manager = _default_session_manager

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
        session_manager = _get_session_manager()

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

        # 会话对象（缓存历史与队列）
        session_manager.get_or_create(dialog_id)

        # 检查 Agent 是否正在运行（全局串行）
        if session_manager.is_globally_running():
            current_dialog_id = session_manager.active_dialog_id()
            logger.info(
                f"[send_message] Agent is running, requesting stop and queuing message for dialog {dialog_id}"
            )

            # 请求停止当前运行中的会话
            session_manager.request_stop(current_dialog_id)

            # 将消息加入目标会话等待队列
            session_manager.queue_message(dialog_id, content)

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
        """获取Agent状态"""
        session_manager = _get_session_manager()
        return {
            "success": True,
            "data": session_manager.status(),
        }

    @app.post("/api/agent/stop")
    async def stop_agent():
        """停止当前Agent运行"""
        session_manager = _get_session_manager()
        import threading
        status = session_manager.status()
        active_dialog_id = status.get("current_dialog_id")
        logger.info(
            f"[stop_agent] Stop requested! Current is_running={status.get('is_running')}, "
            f"dialog_id={active_dialog_id}, thread={threading.current_thread().name}"
        )

        # 请求停止（session_manager 会处理任务取消和 agent 停止）
        session_manager.request_stop(active_dialog_id)
        logger.info(f"[stop_agent] Stop signal sent (task cancelled if running)")

        # 保存完整的 messages 到 JSONL 文件以便分析
        if active_dialog_id:
            import json
            from pathlib import Path
            from datetime import datetime

            dialog = event_manager.get_dialog(active_dialog_id)
            if dialog:
                messages_dict = [msg.to_dict() for msg in dialog.messages]

                # 创建 .logs 目录
                logs_dir = Path(".logs")
                logs_dir.mkdir(exist_ok=True)

                # 生成文件名: {dialog_id}_stop_{timestamp}.jsonl
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = logs_dir / f"{active_dialog_id}_stop_{timestamp}.jsonl"

                # 以 JSONL 格式保存
                with open(log_file, "w", encoding="utf-8") as f:
                    for msg in messages_dict:
                        f.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")

                logger.info(f"[stop_agent] Messages saved to: {log_file}")
                logger.info(f"[stop_agent] Total messages: {len(messages_dict)}")

                # 同时在日志中打印摘要
                for i, msg in enumerate(messages_dict):
                    logger.info(f"  [{i}] role={msg.get('role')}, id={msg.get('id')}, tool_call_id={msg.get('tool_call_id')}, tool_calls={len(msg.get('tool_calls', []))}")
                    content_preview = str(msg.get('content', ''))[:100] if msg.get('content') else '(empty)'
                    logger.info(f"      content_preview={content_preview}")

        return {
            "success": True,
            "message": "Stop requested, Agent will stop immediately"
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
    session_manager = _get_session_manager()

    logger.info(
        f"[process_agent_request] Starting for dialog_id={dialog_id}, "
        f"is_running={session_manager.is_globally_running()}"
    )

    if session_manager.is_globally_running() and session_manager.active_dialog_id() != dialog_id:
        logger.info(f"[process_agent_request] Agent is busy with other dialog, skipping")
        await _send_system_event(dialog_id, "Agent正在处理其他对话，请稍候...")
        return

    # 确保会话存在
    session_manager.get_or_create(dialog_id)

    run_error: str | None = None

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
        agent_name = S02WithSkillLoaderAgent.__name__

        # 创建 WebSocket Bridge，传入 agent_name
        bridge = AgentWebSocketBridge(dialog_id=dialog_id, agent_name=agent_name)
        history_hook = SessionHistoryHook(
            dialog_id=dialog_id,
            session_manager=session_manager,
        )
        composite_hooks = CompositeHooks([history_hook, bridge])

        # 创建 Agent，并通过统一 hook delegate 绑定 WebSocket bridge
        agent = S02WithSkillLoaderAgent()
        agent.set_hook_delegate(composite_hooks)

        # 异步运行Agent（支持真正的停止）
        run_task = None
        try:
            logger.info(f"[process_agent_request] Starting {agent_name}...")
            messages = [{"role": "user", "content": last_user_message}]
            logger.info("[process_agent_request] Built base messages for hook-based history injection")

            # 创建异步任务
            run_task = asyncio.create_task(agent.arun(messages))

            # 将任务保存到 session，以便可以取消
            session_manager.begin_run(dialog_id, agent, run_task)
            logger.info(f"[process_agent_request] Agent instance and task saved to session")

            await run_task
            logger.info(f"[process_agent_request] {agent_name} completed")
        except asyncio.CancelledError:
            logger.info("[process_agent_request] Agent was cancelled (stop requested)")
            await _send_system_event(dialog_id, "Agent已停止")
            # 发送停止事件到前端
            bridge.on_stop()
        except Exception as e:
            logger.info(f"[process_agent_request] Agent error: {e}")
            import traceback
            traceback.print_exc()
            bridge.on_error(e)
            await _send_system_event(dialog_id, f"Agent error: {str(e)}")
            run_error = str(e)

        # 发送完成事件
        await _send_system_event(dialog_id, "处理完成")

    except Exception as e:
        logger.info(f"[process_agent_request] Outer error: {e}")
        import traceback
        traceback.print_exc()
        await _send_system_event(dialog_id, f"错误: {str(e)}")

    finally:
        logger.info(f"[process_agent_request] Cleaning up, setting is_running=False")
        session_manager.end_run(dialog_id, error=run_error)

        # 检查是否有待处理的消息
        pending = session_manager.pop_pending_messages(dialog_id)
        if pending:
            logger.info(f"[process_agent_request] Processing {len(pending)} pending messages")

            if pending:
                await _send_system_event(dialog_id, "处理新的用户消息")
                asyncio.create_task(process_agent_request(dialog_id))
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
