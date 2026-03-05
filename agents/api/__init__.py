"""
FastAPI API 模块

提供 REST API + WebSocket 的统一服务
"""

from .main import create_app, app, start_api_server

__all__ = [
    'create_app',
    'app',
    'start_api_server',
]
