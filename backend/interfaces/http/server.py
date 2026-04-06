"""
HTTP Server - FastAPI 应用

创建 FastAPI 应用并注册路由。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.application.engine import AgentEngine

from .routes import dialog, health, hitl, skills, tools


def create_app(engine: AgentEngine) -> FastAPI:
    """
    创建 FastAPI 应用

    Args:
        engine: AgentEngine 实例

    Returns:
        FastAPI 应用
    """
    app = FastAPI(title="Agent API", description="Hanako-style Agent API", version="0.2.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 存储引擎实例
    app.state.engine = engine

    # 注册路由
    app.include_router(health.router)
    app.include_router(dialog.router, prefix="/api/dialog")
    app.include_router(skills.router, prefix="/api/skills")
    app.include_router(tools.router, prefix="/api/tools")
    app.include_router(hitl.router, prefix="/api/hitl")

    return app
