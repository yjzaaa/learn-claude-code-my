"""HTTP Application - FastAPI 应用实例

创建和配置 FastAPI 应用，整合所有路由和中间件。
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env", override=True)

from backend.infrastructure.container import container
from backend.infrastructure.runtime.runtime_factory import AgentRuntimeFactory
from backend.infrastructure.services import ProviderManager
from backend.domain.models.config import EngineConfig
from backend.infrastructure.event_bus import QueuedEventBus
from backend.infrastructure.agent_queue import AgentTaskQueue
from backend.infrastructure.event_bus.handlers import EventHandlers


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        # 初始化
        await _initialize()
        yield
        # 清理
        await _shutdown()

    app = FastAPI(
        title="Hana Agent API",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    _register_routes(app)

    # 注册异常处理器
    _register_exception_handlers(app)

    return app


async def _initialize() -> None:
    """初始化应用组件"""
    logger.info("[App] Initializing...")

    # 项目根目录
    project_root = Path(__file__).resolve().parent.parent.parent.parent

    # 创建 ProviderManager（统一配置来源）
    provider_manager = ProviderManager()
    model_config = provider_manager.get_model_config()
    logger.info(f"[App] ProviderManager initialized: model={model_config.model}, provider={model_config.provider}")

    # 创建 Runtime
    agent_type = os.getenv("AGENT_TYPE", "simple")
    if agent_type == "deep":
        try:
            import deepagents
        except ImportError:
            logger.warning("deepagents not installed, falling back to simple runtime")
            agent_type = "simple"

    factory = AgentRuntimeFactory()

    # 配置现在主要由 ProviderManager 管理，EngineConfig 作为补充
    config = EngineConfig.from_dict({
        "skills": {"skills_dir": str(project_root / "skills")},
        "provider": {
            "model": model_config.model,  # 从 ProviderManager 获取
            "api_key": model_config.api_key,
            "base_url": model_config.base_url,
        },
        "system": "You are a helpful AI assistant...",
    })

    runtime = factory.create(agent_type, "main-agent", config, provider_manager=provider_manager)
    await runtime.initialize(config)

    if hasattr(runtime, 'setup_workspace_tools'):
        runtime.setup_workspace_tools(project_root)

    # Session Manager
    from backend.domain.models.dialog import DialogSessionManager
    session_manager = DialogSessionManager(max_sessions=100, session_ttl_seconds=1800)
    if hasattr(runtime, 'set_session_manager'):
        runtime.set_session_manager(session_manager)

    # AsyncQueue 组件
    task_queue = AgentTaskQueue(max_concurrent=3)
    await task_queue.start()

    event_bus = QueuedEventBus(maxsize=500, num_consumers=2)
    await event_bus.start()

    # 注册事件处理器
    handlers = EventHandlers(event_bus)
    handlers.register_all()

    # 保存到容器
    container.runtime = runtime
    container.session_manager = session_manager
    container.task_queue = task_queue
    container.event_bus = event_bus
    container.config = config

    logger.info("[App] Initialization complete")


async def _shutdown() -> None:
    """关闭应用组件"""
    logger.info("[App] Shutting down...")

    # 关闭事件总线
    if container.event_bus:
        await container.event_bus.shutdown()
        container.event_bus = None

    # 关闭任务队列
    if container.task_queue:
        await container.task_queue.shutdown()
        container.task_queue = None

    # 关闭 WebSocket 缓冲区
    from backend.interfaces.websocket.broadcast import cleanup_client
    for client_id in list(container.state.client_buffers.keys()):
        await cleanup_client(client_id)

    # 关闭 Runtime
    if container.runtime:
        await container.runtime.shutdown()
        container.runtime = None

    logger.info("[App] Shutdown complete")


def _register_routes(app: FastAPI) -> None:
    """注册路由"""
    from backend.interfaces.http.routes import dialogs, messages, agent

    app.include_router(dialogs.router)
    app.include_router(messages.router)
    app.include_router(agent.router)

    # WebSocket
    from backend.interfaces.websocket.handler import handle_websocket

    from fastapi import WebSocket

    @app.websocket("/ws/{client_id}")
    async def ws_endpoint(websocket: WebSocket, client_id: str):
        await handle_websocket(websocket, client_id)


def _register_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器"""
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("[Exception] Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {"code": "internal_error", "message": str(exc)}
            }
        )
