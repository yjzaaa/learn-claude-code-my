"""
main.py — 后端入口点（简化版）

启动 FastAPI + WebSocket 服务器。
端口: PORT env (默认 8001)

注意：主要逻辑已拆分到 backend/interfaces/http/app.py
"""

import os
import logging

import uvicorn
from loguru import logger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# 创建 FastAPI 应用
from backend.interfaces.http.app import create_app
app = create_app()

# 入口点
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    logger.info("Starting Hana Agent API on %s:%d", host, port)
    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
