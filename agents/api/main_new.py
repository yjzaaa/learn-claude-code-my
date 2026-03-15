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

# 导入新的状态管理类型 (Pydantic 模型)
from ..models.dialog_types import (
    DialogStatus,
    Role,
    CreateDialogRequest,
    CreateDialogResponse,
    SendMessageRequest,
    SendMessageResponse,
    DialogListResponse,
    DialogDetailResponse,
    ErrorResponse,
    DialogSession,
    WebSocketErrorMessage,
    WebSocketSnapshotMessage,
)
from ..models.responses import (
    SkillListResponse,
    SkillDetailResponse,
    SkillUpdateResponse,
    AgentStatusResponse,
    StopAgentResponse,
    SkillEditDecisionResponse,
    TodoUpdateResponse,
)
from pydantic import BaseModel, Field
from ..hooks.state_managed_agent_bridge import (
    StateManagedAgentBridge,
    DialogStore,
    dialog_store,
)
from ..hooks.context_compact_hook import ContextCompactHook
from ..hooks.composite.composite_hooks import CompositeHooks
from ..hooks.todo_manager_hook import TodoManagerHook
from ..session.skill_edit_hitl import skill_edit_hitl_store
from ..session.todo_hitl import todo_store
from ..session.runtime_context import set_current_dialog_id, reset_current_dialog_id, set_current_monitoring_bridge, reset_current_monitoring_bridge

# 导入 WebSocket 组件
from ..websocket.server import connection_manager

# 导入 Agent 组件
try:
    from ..agent.s_full import SFullAgent
    from ..utils.agent_helpers import get_last_user_message
    from ..utils.helpers import inject_todo_tool
    from ..core.s05_skill_loading import SKILL_LOADER
    # 导入监控系统 (新增)
    from ..monitoring import event_bus
    from ..monitoring.bridge import CompositeMonitoringBridge
    # 导入 AgentBuilder 和插件 (测试用)
    from ..core import AgentBuilder
    from ..plugins import BackgroundPlugin
except ImportError:
    from agents.agent.s_full import SFullAgent
    from agents.utils.agent_helpers import get_last_user_message
    from agents.utils.helpers import inject_todo_tool
    from agents.core.s05_skill_loading import SKILL_LOADER
    # 导入监控系统 (新增)
    from agents.monitoring import event_bus
    from agents.monitoring.bridge import CompositeMonitoringBridge
    # 导入 AgentBuilder 和插件 (测试用)
    from agents.core import AgentBuilder
    from agents.plugins import BackgroundPlugin


# ============================================================================
# API 请求模型 (Pydantic)
# ============================================================================


class UpdateSkillRequest(BaseModel):
    """更新技能请求"""
    old_text: str = ""
    new_text: str = ""
    full_content: str = ""
    reason: str = ""


class SkillEditDecisionRequest(BaseModel):
    """Skill Edit 审批请求"""
    decision: str
    edited_content: Optional[str] = None


class UpdateTodosRequest(BaseModel):
    """更新任务列表请求"""
    items: list[dict[str, Any]]


class RootResponse(BaseModel):
    """根端点响应"""
    message: str
    version: str
    endpoints: dict[str, str]


# ============================================================================
# 辅助函数
# ============================================================================


def _get_agent_name() -> str:
    """获取 Agent 名称"""
    return SFullAgent.__name__


def _start_dialog_task(dialog_id: str, bridge: StateManagedAgentBridge) -> None:
    """启动并登记对话任务，供 stop 请求取消。"""
    task = asyncio.create_task(process_agent_request(dialog_id, bridge))
    dialog_store.set_task(dialog_id, task)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 FastAPI Server starting (重构版)...")

    # 初始化监控系统集成
    monitoring_integration: Any = None
    try:
        from ..monitoring.integrations import setup_monitoring_integration
        monitoring_integration = setup_monitoring_integration(connection_manager)
        await monitoring_integration.initialize()
        logger.info("✅ Monitoring system initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize monitoring system: {e}")

    yield

    # 关闭监控系统
    try:
        if monitoring_integration:
            await monitoring_integration.shutdown()
            logger.info("✅ Monitoring system shutdown")
    except Exception as e:
        logger.error(f"❌ Error shutting down monitoring system: {e}")

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

    @app.get("/", response_model=RootResponse)
    async def root() -> RootResponse:
        """根端点"""
        return RootResponse(
            message="Agent API Server (重构版 - 后端状态管理)",
            version="3.0.0",
            endpoints={
                "dialogs": "/api/dialogs",
                "skills": "/api/skills",
                "agent": "/api/agent/status",
                "websocket": "/ws/{client_id}",
            }
        )

    # ---- 对话框 API ----

    @app.get("/api/dialogs", response_model=DialogListResponse)
    async def get_dialogs() -> DialogListResponse:
        """获取所有对话框列表"""
        summaries = dialog_store.list_dialogs()
        return DialogListResponse(
            success=True,
            data=summaries
        )

    @app.post("/api/dialogs", response_model=CreateDialogResponse)
    async def create_dialog(request: CreateDialogRequest) -> CreateDialogResponse:
        """创建新对话框"""
        dialog_id = str(uuid.uuid4())

        bridge = dialog_store.create_dialog(
            dialog_id=dialog_id,
            title=request.title,
            agent_name=_get_agent_name(),
        )

        # 立即推送初始快照
        bridge._push_snapshot()

        return CreateDialogResponse(
            success=True,
            data=bridge.get_session()
        )

    @app.get("/api/dialogs/{dialog_id}", response_model=DialogDetailResponse)
    async def get_dialog(dialog_id: str) -> DialogDetailResponse:
        """获取特定对话框完整状态"""
        session = dialog_store.get_session(dialog_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return DialogDetailResponse(
            success=True,
            data=session
        )

    @app.post("/api/dialogs/{dialog_id}/messages", response_model=SendMessageResponse)
    async def send_message(dialog_id: str, request: SendMessageRequest) -> SendMessageResponse:
        """发送消息到对话框"""
        if not request.content:
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
        bridge.on_user_input(request.content)

        # 异步启动 Agent 处理
        _start_dialog_task(dialog_id, bridge)

        return SendMessageResponse(
            success=True,
            data={
                "dialog_id": dialog_id,
                "status": bridge.get_session().status.value,
            }
        )

    @app.post("/api/dialogs/{dialog_id}/stop", response_model=DialogDetailResponse)
    async def stop_dialog(dialog_id: str) -> DialogDetailResponse:
        """停止当前对话框的 Agent 运行"""
        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            raise HTTPException(status_code=404, detail="Dialog not found")

        dialog_store.cancel_task(dialog_id)
        bridge.on_stop()

        return DialogDetailResponse(
            success=True,
            data=bridge.get_session()
        )

    @app.post("/api/dialogs/{dialog_id}/resume", response_model=SendMessageResponse)
    async def resume_dialog(dialog_id: str) -> SendMessageResponse:
        """继续当前对话框（基于已存在上下文）"""
        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            raise HTTPException(status_code=404, detail="Dialog not found")

        running_task = dialog_store.get_task(dialog_id)
        if running_task and not running_task.done():
            return SendMessageResponse(
                success=True,
                data={
                    "dialog_id": dialog_id,
                    "status": bridge.get_session().status.value,
                    "message": "Dialog is already running",
                },
            )

        session = bridge.get_session()
        has_user_input = any(m.role == Role.USER for m in session.messages)
        if not has_user_input:
            raise HTTPException(status_code=400, detail="No user context to resume")

        _start_dialog_task(dialog_id, bridge)
        return SendMessageResponse(
            success=True,
            data={
                "dialog_id": dialog_id,
                "status": "resuming",
            },
        )

    @app.delete("/api/dialogs/{dialog_id}", response_model=ErrorResponse)
    async def delete_dialog(dialog_id: str) -> ErrorResponse:
        """删除对话框"""
        success = dialog_store.delete_dialog(dialog_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return ErrorResponse(
            success=True,
            error={"message": "Dialog deleted"}
        )

    # ---- Skills API ----

    @app.get("/api/skills", response_model=SkillListResponse)
    async def get_skills() -> SkillListResponse:
        """获取所有可用的skills"""
        from ..models.responses import SkillInfo
        skills = []
        for name, skill in SKILL_LOADER.skills.items():
            skills.append(SkillInfo(
                name=name,
                description=skill["meta"].get("description", "No description"),
                tags=skill["meta"].get("tags", ""),
                path=skill["path"],
            ))

        return SkillListResponse(data=skills)

    @app.get("/api/skills/{skill_name}", response_model=SkillDetailResponse)
    async def get_skill(skill_name: str) -> SkillDetailResponse:
        """获取特定skill的详情"""
        from ..models.responses import SkillDetail
        content = SKILL_LOADER.get_content(skill_name)
        if content.startswith("Error:"):
            raise HTTPException(status_code=404, detail="Skill not found")

        return SkillDetailResponse(
            data=SkillDetail(
                name=skill_name,
                content=content,
            )
        )

    @app.post("/api/skills/{skill_name}/load", response_model=SkillDetailResponse)
    async def load_skill(skill_name: str) -> SkillDetailResponse:
        """加载skill（触发工具调用）"""
        from ..models.responses import SkillDetail
        content = SKILL_LOADER.get_content(skill_name)
        if content.startswith("Error:"):
            raise HTTPException(status_code=404, detail="Skill not found")

        return SkillDetailResponse(
            data=SkillDetail(
                name=skill_name,
                content=content,
            )
        )

    @app.post("/api/skills/{skill_name}/update", response_model=SkillUpdateResponse)
    async def update_skill(skill_name: str, request: UpdateSkillRequest) -> SkillUpdateResponse:
        """更新skill"""
        result = SKILL_LOADER.update_skill(
            skill_name,
            old_text=request.old_text,
            new_text=request.new_text,
            full_content=request.full_content,
            reason=request.reason
        )

        if result.startswith("Error:"):
            raise HTTPException(status_code=400, detail=result)

        return SkillUpdateResponse(data={"message": result})

    # ---- Agent控制 API ----

    @app.get("/api/agent/status", response_model=AgentStatusResponse)
    async def get_agent_status() -> AgentStatusResponse:
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

        return AgentStatusResponse(
            data={
                "active_dialogs": active_dialogs,
                "total_dialogs": len(dialogs),
            }
        )

    @app.post("/api/agent/stop", response_model=StopAgentResponse)
    async def stop_agent() -> StopAgentResponse:
        """停止当前所有运行中的Agent"""
        stopped = []
        for summary in dialog_store.list_dialogs():
            bridge = dialog_store.get_bridge(summary.id)
            if bridge and bridge.get_session().status in [DialogStatus.THINKING, DialogStatus.TOOL_CALLING]:
                dialog_store.cancel_task(summary.id)
                bridge.on_stop()
                stopped.append(summary.id)

        return StopAgentResponse(
            data={
                "stopped_dialogs": stopped,
                "count": len(stopped)
            }
        )

    @app.get("/api/skill-edits/pending", response_model=AgentStatusResponse)
    async def get_pending_skill_edits(dialog_id: Optional[str] = None) -> AgentStatusResponse:
        """获取待审批的 skills 修改列表。"""
        return AgentStatusResponse(
            data={"pending": skill_edit_hitl_store.list_pending(dialog_id=dialog_id)}
        )

    @app.post("/api/skill-edits/{approval_id}/decision", response_model=SkillEditDecisionResponse)
    async def decide_skill_edit(approval_id: str, request: SkillEditDecisionRequest) -> SkillEditDecisionResponse:
        """提交 skills 修改审批结果。"""
        decision = request.decision.strip().lower()
        edited_content = request.edited_content

        result = skill_edit_hitl_store.decide(
            approval_id=approval_id,
            decision=decision,
            edited_content=edited_content,
        )
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message or "invalid decision")
        return result

    # ---- Todo API ----

    @app.get("/api/dialogs/{dialog_id}/todos", response_model=TodoUpdateResponse)
    async def get_dialog_todos(dialog_id: str) -> TodoUpdateResponse:
        """获取对话框的任务列表"""
        session = dialog_store.get_session(dialog_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")

        todos = todo_store.get_todos(dialog_id)
        return TodoUpdateResponse(
            success=True,
            dialog_id=dialog_id,
            item_count=len(todos.get("items", [])),
            items=todos.get("items", [])
        )

    @app.post("/api/dialogs/{dialog_id}/todos", response_model=TodoUpdateResponse)
    async def update_dialog_todos(dialog_id: str, request: UpdateTodosRequest) -> TodoUpdateResponse:
        """手动更新对话框的任务列表"""
        session = dialog_store.get_session(dialog_id)
        if not session:
            raise HTTPException(status_code=404, detail="Dialog not found")

        items = request.items
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="items must be a list")

        success, error = todo_store.update_todos(dialog_id, items)
        if not success:
            raise HTTPException(status_code=400, detail=error)

        return TodoUpdateResponse(
            success=True,
            dialog_id=dialog_id,
            item_count=len(items),
            items=items
        )

    # ========== WebSocket 端点 ==========

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
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


async def handle_websocket_message(websocket: WebSocket, client_id: str, message: Dict[str, Any]) -> None:
    """处理 WebSocket 消息"""
    msg_type = message.get("type")
    dialog_id_raw = message.get("dialog_id")
    dialog_id = dialog_id_raw if isinstance(dialog_id_raw, str) else None

    if msg_type == "subscribe":
        # 订阅对话框 - 立即推送当前快照
        if not dialog_id:
            await websocket.send_json(WebSocketErrorMessage.invalid_dialog_id("dialog_id is required for subscribe").model_dump())
            return

        connection_manager.subscribe_to_dialog(client_id, dialog_id)
        bridge = dialog_store.get_bridge(dialog_id)
        if bridge:
            await websocket.send_json(WebSocketSnapshotMessage(
                dialog_id=bridge.dialog_id,
                data=bridge.get_session()
            ).model_dump())
        else:
            await websocket.send_json(WebSocketErrorMessage.dialog_not_found(dialog_id).model_dump())

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
            await websocket.send_json(WebSocketErrorMessage.invalid_dialog_id("dialog_id is required for stop").model_dump())
            return

        bridge = dialog_store.get_bridge(dialog_id)
        if bridge:
            dialog_store.cancel_task(dialog_id)
            bridge.on_stop()

    elif msg_type == "resume":
        # 继续 Agent
        if not dialog_id:
            await websocket.send_json(WebSocketErrorMessage.invalid_dialog_id("dialog_id is required for resume").model_dump())
            return

        bridge = dialog_store.get_bridge(dialog_id)
        if not bridge:
            await websocket.send_json(WebSocketErrorMessage.dialog_not_found(dialog_id).model_dump())
            return

        running_task = dialog_store.get_task(dialog_id)
        if running_task and not running_task.done():
            return

        session = bridge.get_session()
        has_user_input = any(m.role == Role.USER for m in session.messages)
        if not has_user_input:
            await websocket.send_json(WebSocketErrorMessage.no_context(dialog_id).model_dump())
            return

        _start_dialog_task(dialog_id, bridge)

    else:
        # 未知消息类型
        await websocket.send_json(WebSocketErrorMessage.unknown_type(msg_type).model_dump())


async def process_agent_request(dialog_id: str, bridge: StateManagedAgentBridge) -> None:
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

        # 创建 Agent（使用 AgentBuilder + BackgroundPlugin 测试）
        logger.info("[ProcessAgent] Creating agent with AgentBuilder + BackgroundPlugin")
        agent = AgentBuilder() \
            .with_base_tools() \
            .with_plugin(BackgroundPlugin(max_workers=4)) \
            .with_monitoring(dialog_id=dialog_id) \
            .build()
        agent_name = agent.__class__.__name__
        logger.info(f"[ProcessAgent] Agent created: {agent_name}")

        # 创建监控系统桥接器 (动态获取 Agent 类名)
        monitor_bridge = CompositeMonitoringBridge(
            dialog_id=dialog_id,
            agent_name=agent_name,
            event_bus=event_bus
        )
        monitor_bridge.initialize()  # 初始化监控桥接器
        logger.info(f"[ProcessAgent] Monitoring bridge initialized for dialog: {dialog_id}, agent: {agent_name}")

        # 测试模式：只使用 BackgroundPlugin，不注入 todo
        # inject_todo_tool(agent, dialog_id)
        # todo_hook = TodoManagerHook(dialog_id=dialog_id, store=todo_store)

        compact_hook = ContextCompactHook(bridge=bridge)

        # 组合所有 hooks，包括新的监控桥接器
        all_hooks = CompositeHooks([
            # todo_hook,  # 测试模式：禁用 todo
            compact_hook,
            bridge,
            monitor_bridge  # 新增监控桥接器
        ])
        agent.set_hook_delegate(all_hooks)

        # 运行 Agent
        dialog_token = set_current_dialog_id(dialog_id)
        monitoring_token = set_current_monitoring_bridge(monitor_bridge)
        try:
            logger.info(f"[ProcessAgent] Running agent...")
            messages = bridge.build_window_messages(last_user_message)

            # 测试模式：简化运行逻辑，只使用 BackgroundPlugin
            logger.info("[ProcessAgent] Running with BackgroundPlugin only mode")
            final_answer = await agent.arun(messages)

            # Todo 硬约束（测试模式禁用）
            # max_todo_enforce_retries = max(
            #     0, int(os.getenv("TODO_ENFORCE_MAX_RETRIES", "2"))
            # )
            # enforce_attempt = 0
            # final_answer = ""
            # while True:
            #     final_answer = await agent.arun(messages)
            #     state = todo_store.get_state(dialog_id)
            #     unfinished_count = sum(
            #         1 for item in state.items if item.status != "completed"
            #     )
            #     if unfinished_count == 0:
            #         break
            #     if enforce_attempt >= max_todo_enforce_retries:
            #         logger.warning(
            #             "[ProcessAgent] Todo hard-constraint retries exhausted, "
            #             f"unfinished={unfinished_count}, dialog={dialog_id}"
            #         )
            #         break
            #     enforce_attempt += 1
            #     logger.info(
            #         "[ProcessAgent] Todo hard-constraint triggered, "
            #         f"unfinished={unfinished_count}, attempt={enforce_attempt}"
            #     )
            #     messages.append(
            #         {
            #             "role": "system",
            #             "content": (

            bridge.append_history_round(last_user_message, final_answer)
            logger.info(f"[ProcessAgent] Agent completed")

            # 通知监控桥接器完成 (新增)
            monitor_bridge.on_complete(final_answer)
            monitor_bridge.on_after_run(messages, rounds=1)
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
            reset_current_monitoring_bridge(monitoring_token)

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
