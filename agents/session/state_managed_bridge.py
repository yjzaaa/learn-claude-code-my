"""Compatibility wrapper for StateManagedAgentBridge.

Implementation now lives in ``agents.hooks.state_managed_agent_bridge``.
"""

try:
    from ..hooks.state_managed_agent_bridge import *  # noqa: F401,F403
except ImportError:
    from agents.hooks.state_managed_agent_bridge import *  # type: ignore # noqa: F401,F403
