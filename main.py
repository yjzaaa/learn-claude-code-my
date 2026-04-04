"""
main.py — 后端入口点

启动 FastAPI + WebSocket 服务器，对接前端 useAgentApi / useWebSocket。
端口: PORT env (默认 8001)
"""

import asyncio
import json
import uuid
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Set, Optional, Dict

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

# 明确加载项目根目录的 .env，并覆盖已有环境变量
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Runtime Factory (lazy import so load_dotenv runs first) ───────────────────
from backend.infrastructure.runtime.runtime_factory import AgentRuntimeFactory  # noqa: E402
from backend.domain.models.config import EngineConfig  # noqa: E402
from backend.domain.models.types import (  # noqa: E402
    WSMessageItem,
    WSDialogMetadata,
    WSStreamingMessage,
    WSDialogSnapshot,
    WSSnapshotEvent,
    WSStreamDeltaEvent,
    WSDeltaContent,
    WSErrorEvent,
    WSErrorDetail,
    WSRoundsLimitEvent,
    make_status_change,
    APISendMessageData,
    APIResumeData,
    APIAgentStatusItem,
    APIAgentStatusData,
    APIStopAgentData,
    APISkillItem,
)

_PROJECT_ROOT = Path(__file__).parent

# 从环境变量读取 Agent 类型，默认 simple
_AGENT_TYPE = os.getenv("AGENT_TYPE", "simple")

# 如果配置为 deep 但依赖不存在，优雅降级到 simple
if _AGENT_TYPE == "deep":
    try:
        import deepagents
    except ImportError:
        logger.warning("deepagents not installed, falling back to simple runtime")
        _AGENT_TYPE = "simple"

factory = AgentRuntimeFactory()
config = EngineConfig.from_dict({
    "skills": {"skills_dir": str(_PROJECT_ROOT / "skills")},
    "provider": {
        "model": os.getenv("MODEL_ID", "deepseek/deepseek-chat"),
        "api_key": os.getenv("ANTHROPIC_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("ANTHROPIC_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL"),
    },
    "system": "You are a helpful AI assistant with access to tools. CRITICAL INSTRUCTIONS: 1) When you need to get information, you MUST use the appropriate tool - never pretend to have a script or tell the user to run something themselves. 2) Actually execute the tool and wait for the result. 3) Based on the actual tool result, provide the answer. 4) Never invent file paths like '/tmp/query_xxx.py' or claim scripts are 'ready to run'. 5) If a tool fails, report the error truthfully. 6) After getting tool results, analyze them and provide a clear, concise answer."
})
runtime = factory.create(_AGENT_TYPE, "main-agent", config)

# ── Session Manager ───────────────────────────────────────────────────────────
from backend.domain.models.dialog import DialogSessionManager
session_manager = DialogSessionManager(max_sessions=100, session_ttl_seconds=1800)
if hasattr(runtime, 'set_session_manager'):
    runtime.set_session_manager(session_manager)

# ── WebSocket broadcast ───────────────────────────────────────────────────────
_ws_clients: Set[WebSocket] = set()


async def _broadcast(event: Any) -> None:
    if not _ws_clients:
        return
    text = json.dumps(event, default=str)
    dead: Set[WebSocket] = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(text)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


# ── Status & streaming tracker ────────────────────────────────────────────────
# dialog_id → "idle" | "thinking" | "completed" | "error"
_status: dict[str, str] = {}
# dialog_id → current streaming Message dict (or None)
_streaming_msg: dict[str, Optional[WSStreamingMessage]] = {}

# ── Dialog-level locks to prevent concurrent agent execution ───────────────────
_dialog_locks: dict[str, asyncio.Lock] = {}


def _get_dialog_lock(dialog_id: str) -> asyncio.Lock:
    """获取对话级别的锁，防止同一对话并发执行多个 agent 任务"""
    if dialog_id not in _dialog_locks:
        _dialog_locks[dialog_id] = asyncio.Lock()
    return _dialog_locks[dialog_id]


def _ts() -> int:
    return int(time.time() * 1000)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_message(m) -> WSMessageItem:
    # LangChain 消息使用 type 属性 (human/ai/system/tool)
    msg_type = getattr(m, 'type', 'unknown')
    # 映射为前端期望的角色名
    role_map = {'human': 'user', 'ai': 'assistant', 'system': 'system', 'tool': 'tool'}
    role = role_map.get(msg_type, msg_type)
    # 获取消息ID - CustomXMessage 使用 msg_id 属性，普通消息使用 id
    msg_id = getattr(m, 'msg_id', '') or getattr(m, 'id', '')
    return WSMessageItem(
        id=msg_id,
        role=role,
        content=m.content or "",
        content_type="markdown",
        status="completed",
        timestamp=_iso(),
    )


def _dialog_to_snapshot(dialog_id: str) -> Optional[WSDialogSnapshot]:
    """Convert SessionManager snapshot → WSDialogSnapshot (唯一来源路径)."""
    session_snap = session_manager.build_snapshot(dialog_id)
    if not session_snap:
        return None

    messages: list[WSMessageItem] = []
    for m in session_snap.get("messages", []):
        messages.append({
            "id": m.get("id", ""),
            "role": m.get("role", ""),
            "content": m.get("content", ""),
            "content_type": m.get("content_type", "text"),
            "status": m.get("status", "completed"),
            "timestamp": m.get("timestamp", ""),
        })
    metadata = session_snap.get("metadata", {})
    return {
        "id": session_snap["id"],
        "title": session_snap.get("title", "New Dialog"),
        "status": _status.get(dialog_id, "idle"),
        "messages": messages,
        "streaming_message": _streaming_msg.get(dialog_id),
        "metadata": {
            "model": metadata.get("model", ""),
            "agent_name": metadata.get("agent_name", "Agent"),
            "tool_calls_count": metadata.get("tool_calls_count", 0),
            "total_tokens": metadata.get("total_tokens", 0),
        },
        "created_at": session_snap["created_at"],
        "updated_at": session_snap.get("updated_at", session_snap["created_at"]),
    }


# ── Background agent runner ───────────────────────────────────────────────────

async def _run_agent(dialog_id: str, content: str, message_id: str) -> None:
    # 使用对话级别锁防止并发执行
    async with _get_dialog_lock(dialog_id):
        msg_id = message_id

        # Set up streaming message placeholder
        _status[dialog_id] = "thinking"
        _streaming_msg[dialog_id] = WSStreamingMessage(
            id=msg_id,
            role="assistant",
            content="",
            content_type="markdown",
            status="streaming",
            timestamp=_iso(),
            agent_name="Agent",
            reasoning_content=None,
            tool_calls=[],
        )

        await _broadcast(make_status_change(dialog_id, "idle", "thinking", _ts()))

        accumulated = ""
        first_chunk = True

        try:
            async for event in runtime.send_message(dialog_id, content, stream=True, message_id=msg_id):
                if event.type == "text_delta":
                    if first_chunk:
                        first_chunk = False
                        # runtime has now added user message to dialog — send snapshot before first delta
                        # streaming_message content is still empty so frontend doesn't double-count it
                        snap = _dialog_to_snapshot(dialog_id)
                        if snap:
                            await _broadcast(WSSnapshotEvent(
                                type="dialog:snapshot", data=snap, timestamp=_ts()
                            ))

                    chunk = event.data
                    if isinstance(chunk, list):
                        chunk = "".join(str(c) for c in chunk)
                    elif not isinstance(chunk, str):
                        chunk = str(chunk)
                    accumulated += chunk
                    sm = _streaming_msg.get(dialog_id)
                    if sm is not None:
                        sm["content"] = accumulated

                    await _broadcast(WSStreamDeltaEvent(
                        type="stream:delta",
                        dialog_id=dialog_id,
                        message_id=msg_id,
                        delta=WSDeltaContent(content=chunk, reasoning=""),
                        timestamp=_ts(),
                    ))
                # elif event.type in ("tool_call", "agent:tool_call"):
                #     await _broadcast({
                #         "type": "agent:tool_call",
                #         "dialog_id": dialog_id,
                #         "data": event.data,
                #         "timestamp": _ts(),
                #     })
                # elif event.type in ("tool_result", "agent:tool_result"):
                #     await _broadcast({
                #         "type": "agent:tool_result",
                #         "dialog_id": dialog_id,
                #         "data": event.data,
                #         "timestamp": _ts(),
                #     })
                elif event.type == "complete":
                    break
                elif event.type == "error":
                    raise Exception(str(event.data))

            # Send status:change while streaming_message is still set so frontend can fire
            # agent:message_complete using prevSnapshot.streaming_message
            _status[dialog_id] = "completed"
            await _broadcast(make_status_change(dialog_id, "thinking", "completed", _ts()))

            # Clean up — no second snapshot to avoid duplicate assistant message
            _streaming_msg[dialog_id] = None
            _status[dialog_id] = "idle"

        except Exception as exc:
            logger.exception("[agent] Error running dialog %s: %s", dialog_id, exc)
            _streaming_msg[dialog_id] = None
            _status[dialog_id] = "error"
            await _broadcast(WSErrorEvent(
                type="error",
                dialog_id=dialog_id,
                error=WSErrorDetail(code="agent_error", message=str(exc)),
                timestamp=_ts(),
            ))
            await _broadcast(make_status_change(dialog_id, "thinking", "error", _ts()))


# ── FastAPI app ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await runtime.initialize(config)
    # 检查 runtime 是否有 setup_workspace_tools 方法（SimpleRuntime 有）
    if hasattr(runtime, 'setup_workspace_tools'):
        runtime.setup_workspace_tools(_PROJECT_ROOT)

    async def _on_rounds_limit(event) -> None:
        await _broadcast(WSRoundsLimitEvent(
            type="agent:rounds_limit_reached",
            dialog_id=event.dialog_id,
            rounds=event.rounds,
            timestamp=_ts(),
        ))

    # 检查 runtime 是否有 _event_bus 属性（SimpleRuntime 有，DeepAgentRuntime 没有）
    if hasattr(runtime, '_event_bus'):
        runtime._event_bus.subscribe(_on_rounds_limit, event_types=["AgentRoundsLimitReached"])

    yield
    await runtime.shutdown()


app = FastAPI(title="Hana Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic request bodies ───────────────────────────────────────────────────

class CreateDialogBody(BaseModel):
    title: Optional[str] = "New Dialog"


class SendMessageBody(BaseModel):
    content: str


# ── REST routes ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    sessions = session_manager.list_sessions()
    return {"status": "ok", "dialogs": len(sessions)}


@app.get("/api/dialogs")
def list_dialogs():
    data: list[WSDialogSnapshot] = []
    for session in session_manager.list_sessions():
        d = _dialog_to_snapshot(session.dialog_id)
        if d:
            data.append(d)
    return {"success": True, "data": data}


@app.post("/api/dialogs")
async def create_dialog(body: CreateDialogBody):
    title = body.title or "New Dialog"
    dialog_id = await runtime.create_dialog("", title)
    _status[dialog_id] = "idle"
    _streaming_msg[dialog_id] = None
    d = _dialog_to_snapshot(dialog_id)
    return {"success": True, "data": d}


@app.get("/api/dialogs/{dialog_id}")
def get_dialog(dialog_id: str):
    d = _dialog_to_snapshot(dialog_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dialog not found")
    return {"success": True, "data": d}


@app.delete("/api/dialogs/{dialog_id}")
async def delete_dialog(dialog_id: str):
    session = session_manager.get_session_sync(dialog_id)
    if session is not None:
        await session_manager.close_session(dialog_id)
    _status.pop(dialog_id, None)
    _streaming_msg.pop(dialog_id, None)
    return {"success": True}


@app.get("/api/dialogs/{dialog_id}/messages")
def get_messages(dialog_id: str):
    d = _dialog_to_snapshot(dialog_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dialog not found")
    return {"success": True, "data": d["messages"]}


@app.post("/api/dialogs/{dialog_id}/messages")
async def send_message(dialog_id: str, body: SendMessageBody):
    d = _dialog_to_snapshot(dialog_id)
    if not d:
        raise HTTPException(status_code=404, detail="Dialog not found")

    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    asyncio.create_task(_run_agent(dialog_id, body.content, msg_id))
    return {"success": True, "data": APISendMessageData(message_id=msg_id, status="queued")}


@app.post("/api/dialogs/{dialog_id}/resume")
async def resume_dialog(dialog_id: str):
    return {"success": True, "data": APIResumeData(dialog_id=dialog_id, status="idle")}


@app.get("/api/agent/status")
def agent_status():
    active = [
        APIAgentStatusItem(dialog_id=k, status=v)
        for k, v in _status.items()
        if v not in ("idle", "completed")
    ]
    sessions = session_manager.list_sessions()
    return {"success": True, "data": APIAgentStatusData(
        active_dialogs=active,
        total_dialogs=len(sessions),
    )}


@app.post("/api/agent/stop")
async def stop_agent():
    stopped = [k for k, v in _status.items() if v == "thinking"]
    for k in stopped:
        _status[k] = "idle"
        _streaming_msg[k] = None
    return {"success": True, "data": APIStopAgentData(stopped_dialogs=stopped, count=len(stopped))}


@app.get("/api/skills")
def list_skills():
    try:
        # 检查 runtime 是否有 _skill_mgr 属性（SimpleRuntime 有，DeepAgentRuntime 没有）
        if hasattr(runtime, '_skill_mgr'):
            skills = runtime._skill_mgr.list_skills()
            data = [
                APISkillItem(name=s.id, description=getattr(s, "description", ""),
                             tags="", path="")
                for s in skills
            ]
        else:
            data = []
    except Exception:
        data = []
    return {"success": True, "data": data}


@app.get("/api/skill-edits/pending")
def pending_skill_edits():
    return {"success": True, "data": []}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/{client_id}")
async def ws_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info("[WS] Client connected: %s (total=%d)", client_id, len(_ws_clients))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            # subscribe — send snapshot immediately
            if msg_type == "subscribe":
                did = msg.get("dialog_id")
                if did:
                    snap = _dialog_to_snapshot(did)
                    if snap:
                        await websocket.send_text(
                            json.dumps(WSSnapshotEvent(
                                type="dialog:snapshot", data=snap, timestamp=_ts()
                            ), default=str)
                        )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("[WS] Client %s error: %s", client_id, exc)
    finally:
        _ws_clients.discard(websocket)
        logger.info("[WS] Client disconnected: %s", client_id)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    logger.info("Starting Hana Agent API on %s:%d", host, port)
    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
