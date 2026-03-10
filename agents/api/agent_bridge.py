"""Compatibility wrapper for AgentWebSocketBridge.

Implementation now lives in ``agents.hooks.agent_websocket_bridge``.
"""

try:
    from ..hooks.agent_websocket_bridge import *  # noqa: F401,F403
except ImportError:
    from agents.hooks.agent_websocket_bridge import *  # type: ignore # noqa: F401,F403
