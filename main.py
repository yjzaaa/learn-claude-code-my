"""
main.py — 后端入口点（简化版）

启动 FastAPI + WebSocket 服务器。
端口: PORT env (默认 8001)

注意：主要逻辑已拆分到 backend/interfaces/http/app.py
"""

import os
import warnings

# 尽早安装 warnings 处理器（在任何 Pydantic 导入之前）
from pathlib import Path
import json
from datetime import datetime

_warning_log_file = Path("logs/deep/serialization_warnings.jsonl")
_warning_log_file.parent.mkdir(parents=True, exist_ok=True)
_original_showwarning = warnings.showwarning

def _custom_showwarning(message, category, filename, lineno, file=None, line=None):
    """将序列化警告写入文件，不输出到控制台"""
    msg_str = str(message)
    # 只处理 Pydantic 序列化相关警告
    if "PydanticSerialization" in category.__name__ or "Serialized" in msg_str or "Expected" in msg_str:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "category": category.__name__,
            "message": msg_str[:500],  # 限制长度
            "filename": filename,
            "lineno": lineno,
        }
        try:
            with open(_warning_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # 静默失败，不输出到控制台
    # 其他警告使用默认行为
    else:
        _original_showwarning(message, category, filename, lineno, file, line)

warnings.showwarning = _custom_showwarning

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
