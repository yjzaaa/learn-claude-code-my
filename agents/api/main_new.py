"""
FastAPI 主应用 (重构版)

后端状态管理架构 - 前端纯渲染设计
"""

from loguru import logger
import asyncio
import json
import os
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
from ..hooks.state_managed_agent_bridge import (
    StateManagedAgentBridge,
    DialogStore,
    dialog_store,
)
from ..hooks.context_compact_hook import ContextCompactHook
from ..hooks.composite.composite_hooks import CompositeHooks
from ..hooks.todo_manager_hook import TodoManagerHook
from ..hooks.session_tracker_hook import SessionTrackerHook
from ..session.skill_edit_hitl import skill_edit_hitl_store
from ..session.todo_hitl import todo_store, is_todo_hook_enabled
from ..session.session_ledger import session_ledger_store
from ..session.runtime_context import set_current_dialog_id, reset_current_dialog_id

# 导入 WebSocket 组件
from ..websocket.server import connection_manager

# 导入 Agent 组件
try:
    from ..agent.s02_with_skill_loader import S02WithSkillLoaderAgent
    from ..utils.agent_helpers import get_last_user_message
    from ..utils.helpers import inject_todo_tool
    from ..s05_skill_loading import SKILL_LOADER
except ImportError:
    from agents.agent.s02_with_skill_loader import S02WithSkillLoaderAgent
    from agents.utils.agent_helpers import get_last_user_message
    from agents.utils.helpers import inject_todo_tool
    from agents.s05_skill_loading import SKILL_LOADER


def _get_agent_name() -> str:
    """获取 Agent 名称"""
    return S02WithSkillLoaderAgent.__name__


def _start_dialog_task(dialog_id: str, bridge: StateManagedAgentBridge) -> None:
    """启动并登记对话任务，供 stop 请求取消。"""
    task = asyncio.create_task(process_agent_request(dialog_id, bridge))
    dialog_store.set_task(dialog_id, task)


def _latest_sql_tool_status(messages: list[dict[str, Any]]) -> tuple[bool, str]:
    """Return whether latest SQL-related tool outcome failed and its error code."""
    for msg in reversed(messages):
        if msg.get("role") != "tool":
            continue

        raw = str(msg.get("content", "")).strip()
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        error = data.get("error")
        if isinstance(error, dict):
            code = str(error.get("code", ""))
            if code in {"SQL_EXECUTION_FAILED", "SQL_VALIDATION_FAILED", "QUERY_ONLY_ENFORCED"}:
                return True, code

        # Consider this a successful SQL query outcome and stop looking further back.
        if "rows" in data and "limit" in data:
            return False, ""

    return False, ""


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

    skill_edit_hitl_store.register_broadcaster(connection_manager.broadcast)

    # 为 todo_store 创建按 dialog_id 广播的包装器
    async def broadcast_todo_event(event: dict[str, Any]) -> None:
        """按 dialog_id 广播 todo 事件到订阅的客户端"""
        dialog_id = event.get("dialog_id")
        if dialog_id:
            await connection_manager.broadcast_to_dialog(dialog_id, event)
        else:
            # 如果没有 dialog_id，广播给所有客户端（向后兼容）
            await connection_manager.broadcast(event)

    todo_store.register_broadcaster(broadcast_todo_event)

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
        _start_dialog_task(dialog_id, bridge)

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

        dialog_store.cancel_task(dialog_id)
        bridge.on_stop()

        return {
            "success": True,
            "data": bridge.get_session().to_dict()
        }

    @app.post("/api/dialogs/{dialog_id}/resume")
    async def resume_dialog(dialog_id: str):
        """继续当前对话框（基于已存在上下文）"""
        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            raise HTTPException(status_code=404, detail="Dialog not found")

        running_task = dialog_store.get_task(dialog_id)
        if running_task and not running_task.done():
            return {
                "success": True,
                "data": {
                    "dialog_id": dialog_id,
                    "status": bridge.get_session().status.value,
                    "message": "Dialog is already running",
                },
            }

        session = bridge.get_session()
        has_user_input = any(m.role == Role.USER for m in session.messages)
        if not has_user_input:
            raise HTTPException(status_code=400, detail="No user context to resume")

        _start_dialog_task(dialog_id, bridge)
        return {
            "success": True,
            "data": {
                "dialog_id": dialog_id,
                "status": "resuming",
            },
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
        active_dialogs = []
        for d in dialogs:
            session = dialog_store.get_session(d.id)
            active_dialogs.append(
                {
                    "dialog_id": d.id,
                    "status": session.status.value if session is not None else "unknown",
                }
            )

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
                dialog_store.cancel_task(summary.id)
                bridge.on_stop()
                stopped.append(summary.id)

        return {
            "success": True,
            "data": {
                "stopped_dialogs": stopped,
                "count": len(stopped)
            }
        }

    @app.get("/api/skill-edits/pending")
    async def get_pending_skill_edits(dialog_id: str | None = None):
        """获取待审批的 skills 修改列表。"""
        return {
            "success": True,
            "data": skill_edit_hitl_store.list_pending(dialog_id=dialog_id),
        }

    @app.post("/api/skill-edits/{approval_id}/decision")
    async def decide_skill_edit(approval_id: str, request: Dict[str, Any]):
        """提交 skills 修改审批结果。"""
        decision_raw = request.get("decision", "")
        decision = str(decision_raw).strip().lower()
        edited_content_raw = request.get("edited_content")
        edited_content = str(edited_content_raw) if edited_content_raw is not None else None

        result = skill_edit_hitl_store.decide(
            approval_id=approval_id,
            decision=decision,
            edited_content=edited_content,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "invalid decision"))
        return result

    # ---- Todo API ----

    @app.get("/api/dialogs/{dialog_id}/todos")
    async def get_dialog_todos(dialog_id: str):
        """获取对话框的任务列表"""
        session = dialog_store.get_session(dialog_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return {
            "success": True,
            "data": todo_store.get_todos(dialog_id)
        }

    @app.post("/api/dialogs/{dialog_id}/todos")
    async def update_dialog_todos(dialog_id: str, request: Dict[str, Any]):
        """手动更新对话框的任务列表"""
        session = dialog_store.get_session(dialog_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")

        items = request.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="items must be a list")

        success, error = todo_store.update_todos(dialog_id, items)
        if not success:
            raise HTTPException(status_code=400, detail=error)

        return {
            "success": True,
            "data": todo_store.get_todos(dialog_id)
        }

    @app.get("/api/dialogs/{dialog_id}/session-ledger")
    async def get_dialog_session_ledger(dialog_id: str):
        """获取对话框的会话追踪账本。"""
        session = dialog_store.get_session(dialog_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return {
            "success": True,
            "data": session_ledger_store.get_snapshot(dialog_id),
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
    dialog_id_raw = message.get("dialog_id")
    dialog_id = dialog_id_raw if isinstance(dialog_id_raw, str) else None

    if msg_type == "subscribe":
        # 订阅对话框 - 立即推送当前快照
        if not dialog_id:
            await websocket.send_json({
                "type": "error",
                "error": {"code": "INVALID_DIALOG_ID", "message": "dialog_id is required for subscribe"},
            })
            return

        connection_manager.subscribe_to_dialog(client_id, dialog_id)
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
        _start_dialog_task(dialog_id, bridge)

    elif msg_type == "stop":
        # 停止 Agent
        if not dialog_id:
            await websocket.send_json({
                "type": "error",
                "error": {"code": "INVALID_DIALOG_ID", "message": "dialog_id is required for stop"},
            })
            return

        bridge = dialog_store.get_bridge(dialog_id)
        if bridge:
            dialog_store.cancel_task(dialog_id)
            bridge.on_stop()

    elif msg_type == "resume":
        # 继续 Agent
        if not dialog_id:
            await websocket.send_json({
                "type": "error",
                "error": {"code": "INVALID_DIALOG_ID", "message": "dialog_id is required for resume"},
            })
            return

        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            await websocket.send_json({
                "type": "error",
                "dialog_id": dialog_id,
                "error": {"code": "DIALOG_NOT_FOUND", "message": "Dialog not found"},
            })
            return

        running_task = dialog_store.get_task(dialog_id)
        if running_task and not running_task.done():
            return

        session = bridge.get_session()
        has_user_input = any(m.role == Role.USER for m in session.messages)
        if not has_user_input:
            await websocket.send_json({
                "type": "error",
                "dialog_id": dialog_id,
                "error": {"code": "NO_CONTEXT", "message": "No user context to resume"},
            })
            return

        _start_dialog_task(dialog_id, bridge)

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

        # 创建 Agent，设置 Hook 委托（Todo Hook + 压缩 Hook + 状态桥接）
        agent = S02WithSkillLoaderAgent()

        # 动态注入 todo 工具（非侵入式）
        inject_todo_tool(agent, dialog_id)

        todo_hook = TodoManagerHook(dialog_id=dialog_id, store=todo_store)
        tracker_hook = SessionTrackerHook(dialog_id=dialog_id, ledger=session_ledger_store)
        compact_hook = ContextCompactHook(bridge=bridge)
        agent.set_hook_delegate(CompositeHooks([tracker_hook, todo_hook, compact_hook, bridge]))

        # 运行 Agent
        dialog_token = set_current_dialog_id(dialog_id)
        try:
            logger.info(f"[ProcessAgent] Running agent...")
            messages = bridge.build_window_messages(last_user_message)

            # Todo 硬约束：存在未完成任务时，本次请求内不得直接结束。
            # 为避免死循环，限制强制续跑次数。
            max_todo_enforce_retries = max(
                0, int(os.getenv("TODO_ENFORCE_MAX_RETRIES", "2"))
            )
            max_sql_enforce_retries = max(
                0, int(os.getenv("SQL_ENFORCE_MAX_RETRIES", "2"))
            )
            enforce_attempt = 0
            sql_enforce_attempt = 0
            final_answer = ""

            while True:
                final_answer = await agent.arun(messages)

                state = todo_store.get_state(dialog_id)
                unfinished_count = sum(
                    1 for item in state.items if item.status != "completed"
                )
                sql_failed, sql_error_code = _latest_sql_tool_status(messages)

                hard_reasons: list[str] = []
                if unfinished_count > 0:
                    hard_reasons.append("TODO_UNFINISHED")
                if sql_failed:
                    hard_reasons.append(sql_error_code or "SQL_FAILED")

                if not hard_reasons:
                    break

                bridge.emit_custom_event(
                    "session:hard_blocked",
                    {
                        "reasons": hard_reasons,
                        "unfinished_todo_count": unfinished_count,
                    },
                )
                session_ledger_store.record_correction(
                    dialog_id,
                    reason=";".join(hard_reasons),
                    action="enforce_retry",
                    blocked=True,
                    metadata={
                        "unfinished_todo_count": unfinished_count,
                        "sql_error_code": sql_error_code,
                        "todo_retries": enforce_attempt,
                        "sql_retries": sql_enforce_attempt,
                    },
                )

                if sql_failed:
                    if sql_enforce_attempt >= max_sql_enforce_retries:
                        logger.warning(
                            "[ProcessAgent] SQL hard-constraint retries exhausted, "
                            f"dialog={dialog_id}"
                        )
                    else:
                        sql_enforce_attempt += 1
                        logger.info(
                            "[ProcessAgent] SQL hard-constraint triggered, "
                            f"attempt={sql_enforce_attempt}"
                        )
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "<reminder>SQL hard constraint: latest SQL execution/validation failed. "
                                    "You MUST correct and re-run SQL before ending this round.</reminder>"
                                ),
                            }
                        )
                        continue

                if enforce_attempt >= max_todo_enforce_retries:
                    logger.warning(
                        "[ProcessAgent] Todo hard-constraint retries exhausted, "
                        f"unfinished={unfinished_count}, dialog={dialog_id}"
                    )
                    break

                enforce_attempt += 1
                logger.info(
                    "[ProcessAgent] Todo hard-constraint triggered, "
                    f"unfinished={unfinished_count}, attempt={enforce_attempt}"
                )

                # 强提醒插入到当前上下文，迫使模型先更新 todo 再继续。
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "<reminder>Todo hard constraint: there are unfinished todo items. "
                            "Before ending this round, you MUST call the todo tool to update "
                            "statuses for completed work and keep exactly one in_progress item "
                            "if any work remains.</reminder>"
                        ),
                    }
                )

            bridge.append_history_round(last_user_message, final_answer)
            logger.info(f"[ProcessAgent] Agent completed")
        except asyncio.CancelledError:
            logger.info(f"[ProcessAgent] Agent was cancelled")
            bridge.on_stop()
            await bridge.flush_pending_events()
        except Exception as e:
            logger.error(f"[ProcessAgent] Agent error: {e}")
            import traceback
            traceback.print_exc()
            bridge.on_error(e)
            await bridge.flush_pending_events()
        finally:
            reset_current_dialog_id(dialog_token)

        await bridge.flush_pending_events()

    except Exception as e:
        logger.error(f"[ProcessAgent] Outer error: {e}")
        import traceback
        traceback.print_exc()
        bridge.on_error(e)
        await bridge.flush_pending_events()
    finally:
        current_task = asyncio.current_task()
        if current_task is not None:
            dialog_store.clear_task(dialog_id, current_task)


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
