#!/usr/bin/env python3
"""
启动 FastAPI 服务器

使用方法:
    python start_server.py              # 默认端口 8001（默认热重载）
    python start_server.py --port 8000  # 指定端口
    python start_server.py --no-reload  # 关闭热重载
    python start_server.py --host 0.0.0.0 --port 8001
"""

import argparse
import sys
import os
from pathlib import Path
from contextlib import suppress

import uvicorn
from loguru import logger
from agents.base.basetool import WorkspaceOps

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


class SingleInstanceGuard:
    """Prevent multiple start_server launchers from running simultaneously."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fh = None

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+", encoding="utf-8")

        if msvcrt is None:
            # Non-Windows fallback: best-effort PID check.
            self._fh.seek(0)
            existing = self._fh.read().strip()
            if existing and existing.isdigit():
                try:
                    os.kill(int(existing), 0)
                    return False
                except OSError:
                    pass
            self._fh.seek(0)
            self._fh.truncate()
            self._fh.write(str(os.getpid()))
            self._fh.flush()
            return True

        try:
            # Lock one byte; fails if another start_server holds the lock.
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
            self._fh.seek(0)
            self._fh.truncate()
            self._fh.write(str(os.getpid()))
            self._fh.flush()
            return True
        except OSError:
            return False

    def release(self):
        if not self._fh:
            return
        if msvcrt is not None:
            with suppress(OSError):
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
        self._fh.close()
        self._fh = None

def main():
    lock = SingleInstanceGuard(Path(__file__).parent / ".runtime" / "start_server.lock")
    if not lock.acquire():
        logger.error("检测到已有 start_server.py 实例在运行，已阻止重复启动。")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="启动 Agent FastAPI 服务器")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器主机地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="服务器端口 (默认: 8001)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=True,
        help="启用热重载模式 (默认: 启用)",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="关闭热重载模式",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    if args.reload:
        logger.info("🚀 启动 FastAPI Agent 服务器 [热重载模式]")
    else:
        logger.info("🚀 启动 FastAPI Agent 服务器")
    logger.info("=" * 60)
    logger.info(f"\n📡 服务器地址: http://{args.host}:{args.port}")
    logger.info(f"🔗 WebSocket: ws://{args.host}:{args.port}/ws/{{client_id}}")
    logger.info("\n📚 API 端点:")
    logger.info(f"   - GET  http://{args.host}:{args.port}/")
    logger.info(f"   - GET  http://{args.host}:{args.port}/api/dialogs")
    logger.info(f"   - POST http://{args.host}:{args.port}/api/dialogs")
    logger.info(f"   - GET  http://{args.host}:{args.port}/api/dialogs/{{id}}")
    logger.info(f"   - POST http://{args.host}:{args.port}/api/dialogs/{{id}}/messages")
    logger.info(f"   - GET  http://{args.host}:{args.port}/api/skills")
    logger.info(f"   - POST http://{args.host}:{args.port}/api/skills/{{name}}/update")
    logger.info(f"   - GET  http://{args.host}:{args.port}/api/agent/status")
    logger.info("\n" + "=" * 60)

    # Show effective tool access policy for auditing (no secrets printed).
    ops = WorkspaceOps(Path(__file__).parent, auto_build_tools=False)
    bash_scopes: list[str] = []
    for scope in ops.bash_script_scopes:
        scope_label = (
            str(scope.relative_to(Path(__file__).parent))
            if scope.is_relative_to(Path(__file__).parent)
            else str(scope)
        )
        bash_scopes.append(scope_label)
    write_scope = (
        str(ops.write_scope.relative_to(Path(__file__).parent))
        if ops.write_scope.is_relative_to(Path(__file__).parent)
        else str(ops.write_scope)
    )
    write_scopes: list[str] = []
    for scope in ops.write_scopes:
        label = (
            str(scope.relative_to(Path(__file__).parent))
            if scope.is_relative_to(Path(__file__).parent)
            else str(scope)
        )
        write_scopes.append(label)
    edit_scopes: list[str] = []
    for scope in ops.edit_scopes:
        label = (
            str(scope.relative_to(Path(__file__).parent))
            if scope.is_relative_to(Path(__file__).parent)
            else str(scope)
        )
        edit_scopes.append(label)
    read_blacklist_scopes: list[str] = []
    for scope in ops.read_blacklist_scopes:
        label = (
            str(scope.relative_to(Path(__file__).parent))
            if scope.is_relative_to(Path(__file__).parent)
            else str(scope)
        )
        read_blacklist_scopes.append(label)
    logger.info(f"🔐 BASH_SCRIPT_WHITELIST: {';'.join(ops.bash_script_whitelist)}")
    logger.info(f"🔐 BASH_SCRIPT_SCOPES: {', '.join(bash_scopes) if bash_scopes else '(none)'}")
    logger.info(f"📝 WRITE_TOOL_WHITELIST: {';'.join(ops.write_tool_whitelist)}")
    logger.info(f"📝 WRITE_SCOPES: {', '.join(write_scopes) if write_scopes else write_scope}")
    logger.info(f"✏️ EDIT_TOOL_WHITELIST: {';'.join(ops.edit_tool_whitelist)}")
    logger.info(f"✏️ EDIT_SCOPES: {', '.join(edit_scopes) if edit_scopes else '(none)'}")
    logger.info(f"📖 READ_TOOL_BLACKLIST: {';'.join(ops.read_tool_blacklist)}")
    logger.info(f"📖 READ_BLOCKED_SCOPES: {', '.join(read_blacklist_scopes) if read_blacklist_scopes else '(none)'}")

    try:
        uvicorn.run(
            "agents.api.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            reload_dirs=["agents"] if args.reload else None,
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("\n\n👋 服务器已停止")
        sys.exit(0)
    except Exception as e:
        logger.info(f"\n❌ 启动失败: {e}")
        sys.exit(1)
    finally:
        lock.release()


if __name__ == "__main__":
    main()

