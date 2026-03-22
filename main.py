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
from typing import Any, Dict, Set, Optional

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Engine (lazy import so load_dotenv runs first) ────────────────────────────
from core.engine import AgentEngine  # noqa: E402
from core.models.types import (  # noqa: E402
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
engine = AgentEngine({"skills": {"skills_dir": str(_PROJECT_ROOT / "skills")}})

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
_status: Dict[str, str] = {}
# dialog_id → current streaming Message dict (or None)
_streaming_msg: Dict[str, Optional[WSStreamingMessage]] = {}


def _ts() -> int:
    return int(time.time() * 1000)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_message(m) -> WSMessageItem:
    return WSMessageItem(
        id=m.id,
        role=m.role,
        content=m.content or "",
        content_type="markdown",
        status="completed",
        timestamp=m.created_at.isoformat() if hasattr(m, "created_at") else _iso(),
    )


def _dialog_to_snapshot(dialog_id: str) -> Optional[WSDialogSnapshot]:
    """Convert engine Dialog → DialogSession JSON (matches frontend types/dialog.ts)."""
    dialog = engine._dialog_mgr.get(dialog_id)
    if not dialog:
        return None
    msgs = [_make_message(m) for m in dialog.messages]
    return WSDialogSnapshot(
        id=dialog.id,
        title=dialog.title or "New Dialog",
        status=_status.get(dialog_id, "idle"),
        messages=msgs,
        streaming_message=_streaming_msg.get(dialog_id),
        metadata=WSDialogMetadata(
            model="",
            agent_name="Agent",
            tool_calls_count=0,
            total_tokens=0,
        ),
        created_at=dialog.created_at.isoformat(),
        updated_at=dialog.updated_at.isoformat(),
    )


# ── Background agent runner ───────────────────────────────────────────────────

async def _run_agent(dialog_id: str, content: str) -> None:
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"

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
        async for chunk in engine.send_message(dialog_id, content, message_id=msg_id):
            if first_chunk:
                first_chunk = False
                # engine has now added user message to dialog — send snapshot before first delta
                # streaming_message content is still empty so frontend doesn't double-count it
                snap = _dialog_to_snapshot(dialog_id)
                if snap:
                    await _broadcast(WSSnapshotEvent(
                        type="dialog:snapshot", data=snap, timestamp=_ts()
                    ))

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
    await engine.startup()
    engine.setup_workspace_tools(_PROJECT_ROOT)

    async def _on_rounds_limit(event) -> None:
        await _broadcast(WSRoundsLimitEvent(
            type="agent:rounds_limit_reached",
            dialog_id=event.dialog_id,
            rounds=event.rounds,
            timestamp=_ts(),
        ))

    engine.subscribe(_on_rounds_limit, event_types=["AgentRoundsLimitReached"])

    yield
    await engine.shutdown()


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
    return {"status": "ok", "dialogs": len(engine._dialog_mgr._dialogs)}


@app.get("/api/dialogs")
def list_dialogs():
    data: list[WSDialogSnapshot] = []
    for did in engine._dialog_mgr._dialogs:
        d = _dialog_to_snapshot(did)
        if d:
            data.append(d)
    return {"success": True, "data": data}


@app.post("/api/dialogs")
async def create_dialog(body: CreateDialogBody):
    title = body.title or "New Dialog"
    dialog_id = await engine.create_dialog("", title)
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
    if dialog_id in engine._dialog_mgr._dialogs:
        del engine._dialog_mgr._dialogs[dialog_id]
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
    asyncio.create_task(_run_agent(dialog_id, body.content))
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
    return {"success": True, "data": APIAgentStatusData(
        active_dialogs=active,
        total_dialogs=len(engine._dialog_mgr._dialogs),
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
        skills = engine._skill_mgr.list_skills()
        data = [
            APISkillItem(name=s.id, description=getattr(s, "description", ""),
                         tags="", path="")
            for s in skills
        ]
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
    uvicorn.run("main:app", host=host, port=port, reload=True, log_level="info")
