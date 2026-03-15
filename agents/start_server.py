#!/usr/bin/env python3
"""
启动 FastAPI 服务器

使用方法:
    python start_server.py              # 默认端口 8001（默认热重载）
    python start_server.py --port 8000  # 指定端口
    python start_server.py --no-reload  # 关闭热重载
    python start_server.py --host 0.0.0.0 --port 8001
    python start_server.py --force      # 强制杀死占用端口的旧实例
"""

import argparse
import sys
import os
import subprocess
import signal
from pathlib import Path
from contextlib import suppress

import uvicorn
from loguru import logger
from agents.base.basetool import WorkspaceOps
from agents.utils.logging_config import configure_project_logging

configure_project_logging()

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

def kill_process_on_port(port: int) -> bool:
    """查找并杀死占用指定端口的进程。"""
    killed = False
    try:
        if os.name == 'nt':  # Windows
            # 查找占用端口的进程
            result = subprocess.run(
                ['netstat', '-ano', '|', 'findstr', f':{port}'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 5 and f':{port}' in line:
                        pid = parts[-1]
                        if pid.isdigit():
                            try:
                                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                                logger.warning(f"已终止占用端口 {port} 的进程 PID={pid}")
                                killed = True
                            except Exception as e:
                                logger.error(f"终止进程失败 PID={pid}: {e}")
            else:  # Linux/Mac
                # 使用 lsof 查找占用端口的进程
                result = subprocess.run(
                    ['lsof', '-t', '-i', f':{port}'],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout:
                    for pid in result.stdout.strip().split('\n'):
                        pid = pid.strip()
                        if pid.isdigit():
                            try:
                                os.kill(int(pid), signal.SIGTERM)
                                logger.warning(f"已终止占用端口 {port} 的进程 PID={pid}")
                                killed = True
                            except Exception as e:
                                logger.error(f"终止进程失败 PID={pid}: {e}")
    except Exception as e:
        logger.error(f"查找端口占用进程时出错: {e}")
    return killed


def main():
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
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        default=False,
        help="强制杀死占用端口的旧实例后启动",
    )

    args = parser.parse_args()

    # 强制模式：杀死占用端口的旧实例
    if args.force:
        logger.info(f"🔍 检查端口 {args.port} 是否被占用...")
        kill_process_on_port(args.port)

    # 单实例保护
    lock = SingleInstanceGuard(Path(__file__).parent / ".runtime" / "start_server.lock")
    if not lock.acquire():
        if args.force:
            logger.warning("检测到已有 start_server.py 实例，尝试强制终止...")
            # 在 Windows 上尝试终止其他 Python 进程
            try:
                if os.name == 'nt':
                    subprocess.run(
                        ['taskkill', '/F', '/FI', 'IMAGENAME eq python.exe', '/FI', 'WINDOWTITLE eq *start_server*'],
                        capture_output=True
                    )
                else:
                    # 查找并终止其他 start_server.py 进程
                    result = subprocess.run(
                        ['pgrep', '-f', 'start_server.py'],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        for pid in result.stdout.strip().split('\n'):
                            if pid.strip() and pid.strip() != str(os.getpid()):
                                try:
                                    os.kill(int(pid.strip()), signal.SIGTERM)
                                except:
                                    pass
            except Exception as e:
                logger.error(f"强制终止旧实例失败: {e}")
            # 再次尝试获取锁
            import time
            time.sleep(1)
            if not lock.acquire():
                logger.error("仍无法获取单实例锁，退出。")
                sys.exit(1)
        else:
            logger.error("检测到已有 start_server.py 实例在运行，已阻止重复启动。")
            logger.info("提示: 使用 --force 参数强制杀死旧实例并启动新实例")
            sys.exit(1)

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
            "agents.api.main_new:app",
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

