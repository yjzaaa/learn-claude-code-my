"""
HTTP Interface - HTTP REST API

提供 FastAPI 路由和依赖注入。
"""

from .server import create_app

__all__ = ["create_app"]
