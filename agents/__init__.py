# agents/ - Python teaching agents (s01-s12) + reference agent (s_full)
# Each file is self-contained and runnable: python agents/s01_agent_loop.py

from .utils.logging_config import configure_project_logging

configure_project_logging()

# New modular agent framework (Phase 1 exports)
# Note: Import plugins and agents directly to avoid circular imports
# - from agents.plugins import TodoPlugin, TaskPlugin
# - from agents.agents import FullAgent
# - from agents.core import AgentBuilder
from . import core

__all__ = ["core"]
