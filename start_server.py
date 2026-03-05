#!/usr/bin/env python3
"""
启动 FastAPI 服务器

使用方法:
    python start_server.py              # 默认端口 8001
    python start_server.py --port 8000  # 指定端口
    python start_server.py --host 0.0.0.0 --port 8001
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from agents.api import start_api_server
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保已安装依赖: pip install -r requirements.txt")
    sys.exit(1)


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
        help="启用热重载模式 (开发时使用)",
    )

    args = parser.parse_args()

    print("=" * 60)
    if args.reload:
        print("🚀 启动 FastAPI Agent 服务器 [热重载模式]")
    else:
        print("🚀 启动 FastAPI Agent 服务器")
    print("=" * 60)
    print(f"\n📡 服务器地址: http://{args.host}:{args.port}")
    print(f"🔗 WebSocket: ws://{args.host}:{args.port}/ws/{{client_id}}")
    print("\n📚 API 端点:")
    print(f"   - GET  http://{args.host}:{args.port}/")
    print(f"   - GET  http://{args.host}:{args.port}/api/dialogs")
    print(f"   - POST http://{args.host}:{args.port}/api/dialogs")
    print(f"   - GET  http://{args.host}:{args.port}/api/dialogs/{{id}}")
    print(f"   - POST http://{args.host}:{args.port}/api/dialogs/{{id}}/messages")
    print(f"   - GET  http://{args.host}:{args.port}/api/skills")
    print(f"   - POST http://{args.host}:{args.port}/api/skills/{{name}}/update")
    print(f"   - GET  http://{args.host}:{args.port}/api/agent/status")
    print("\n" + "=" * 60)

    try:
        asyncio.run(start_api_server(host=args.host, port=args.port, reload=args.reload))
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
