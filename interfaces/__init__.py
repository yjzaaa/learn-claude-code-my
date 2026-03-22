"""
Interfaces - 接口层

提供 HTTP REST API 和 WebSocket 接口。
所有接口只做协议转换，无业务逻辑。

使用示例:
    from interfaces.http.server import create_app
    from core.engine import AgentEngine
    
    engine = AgentEngine(config)
    app = create_app(engine)
"""

__version__ = "0.1.0"
