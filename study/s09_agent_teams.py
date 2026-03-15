#!/usr/bin/env python3
"""
s09_agent_teams.py - 简化版 TeamLeadAgent (使用 BaseAgentLoop + 插件系统)

重构后使用 BaseAgentLoop 和 provider 直接调用。
支持插件：SkillPlugin, CompactPlugin
支持真正的子 Agent spawn
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional, List, Type, Dict, Callable

from dotenv import load_dotenv
from loguru import logger

try:
    from .base import PluginEnabledAgent, WorkspaceOps, tool, build_tools_and_handlers
    from .models import ChatMessage, ChatEvent
    from .plugins import AgentPlugin
    from .plugins.skill_plugin import SkillPlugin
    from .plugins.compact_plugin import CompactPlugin
except ImportError:
    from agents.base import PluginEnabledAgent, WorkspaceOps, tool, build_tools_and_handlers
    from agents.models import ChatMessage, ChatEvent
    from agents.plugins import AgentPlugin
    from agents.plugins.skill_plugin import SkillPlugin
    from agents.plugins.compact_plugin import CompactPlugin

load_dotenv(override=True)

WORKDIR = Path.cwd()
OPS = WorkspaceOps(workdir=WORKDIR)

# ========== 子 Agent 管理 ==========

class SubAgentManager:
    """
    子 Agent 管理器 - 管理真正运行的子 Agent 实例
    """

    def __init__(self):
        self._subagents: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def spawn(
        self,
        name: str,
        role: str,
        prompt: str,
        dialog_id: str,
        get_hook_kwargs: Callable[[str], Dict[str, Callable]]
    ) -> str:
        """
        创建并启动一个子 Agent

        Args:
            name: 子 Agent 名称
            role: 角色描述
            prompt: 初始提示
            dialog_id: 所属对话框ID
            get_hook_kwargs: 获取 WebSocket 钩子的函数
        """
        with self._lock:
            if name in self._subagents:
                subagent = self._subagents[name]
                if subagent["status"] == "running":
                    return f"Error: '{name}' is already running"
                # 重新启动已存在的子 Agent
                subagent["status"] = "running"
            else:
                self._subagents[name] = {
                    "name": name,
                    "role": role,
                    "status": "running",
                    "dialog_id": dialog_id,
                    "messages": [],
                }

        # 在后台线程中启动子 Agent
        thread = threading.Thread(
            target=self._run_subagent,
            args=(name, role, prompt, dialog_id, get_hook_kwargs),
            daemon=True,
        )
        thread.start()

        with self._lock:
            self._subagents[name]["thread"] = thread

        return f"Spawned '{name}' (role: {role})"

    def _run_subagent(
        self,
        name: str,
        role: str,
        prompt: str,
        dialog_id: str,
        get_hook_kwargs: Callable[[str], Dict[str, Callable]]
    ):
        """在独立线程中运行子 Agent（带插件支持）"""
        try:
            # 获取 WebSocket 钩子（使用子 Agent 自己的名称）
            from agents.api.agent_bridge import AgentWebSocketBridge
            bridge = AgentWebSocketBridge(dialog_id=dialog_id, agent_name=name)
            hooks = bridge.get_hook_kwargs()

            # 创建带插件的子 Agent
            sub_agent = self._create_subagent_with_plugins(
                name=name,
                role=role,
                hooks=hooks
            )

            # 运行子 Agent
            messages = [{"role": "user", "content": prompt}]
            logger.info(f"[SubAgent:{name}] Starting with prompt: {prompt[:100]}...")
            result = sub_agent.run_with_inbox(messages)
            logger.info(f"[SubAgent:{name}] Run completed, result length: {len(result)}")

            # 更新状态
            with self._lock:
                if name in self._subagents:
                    self._subagents[name]["status"] = "completed"
                    self._subagents[name]["result"] = result

            logger.info(f"[SubAgent:{name}] Completed with result: {result[:100]}...")

        except Exception as e:
            logger.error(f"[SubAgent:{name}] Error: {e}")
            with self._lock:
                if name in self._subagents:
                    self._subagents[name]["status"] = "error"
                    self._subagents[name]["error"] = str(e)

    def _create_subagent_with_plugins(
        self,
        name: str,
        role: str,
        hooks: Dict[str, Callable]
    ) -> 'SubAgentWithPlugins':
        """创建带插件支持的子 Agent"""
        logger.info(f"[SubAgentManager] Creating subagent '{name}' with role '{role}'")
        subagent = SubAgentWithPlugins(
            name=name,
            role=role,
            **hooks
        )
        logger.info(f"[SubAgentManager] Subagent '{name}' created with {len(subagent.tools)} tools")
        return subagent

    def get_status(self, name: str) -> Optional[str]:
        """获取子 Agent 状态"""
        with self._lock:
            subagent = self._subagents.get(name)
            return subagent["status"] if subagent else None

    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有子 Agent"""
        with self._lock:
            return [
                {
                    "name": s["name"],
                    "role": s["role"],
                    "status": s["status"],
                }
                for s in self._subagents.values()
            ]

    def stop(self, name: str) -> str:
        """停止子 Agent"""
        with self._lock:
            subagent = self._subagents.get(name)
            if not subagent:
                return f"Error: '{name}' not found"
            if subagent["status"] != "running":
                return f"'{name}' is not running (status: {subagent['status']})"
            # 标记为停止请求（实际停止由 Agent 自己检查）
            subagent["status"] = "stopping"
            return f"Stop requested for '{name}'"


# 全局子 Agent 管理器
SUBAGENT_MANAGER = SubAgentManager()

# 主管代理系统提示词
LEAD_SYSTEM = f"""You are a team lead at {WORKDIR}.
Your job is to coordinate tasks and help users accomplish their goals.

Available actions:
1. spawn_teammate(name, role, prompt) - Create a new teammate with a specific role
2. send_message(to, content) - Send a message to a specific teammate
3. broadcast(content) - Send a message to all teammates

Remember to:
- Plan before acting
- Use teammates for parallel tasks
- Report progress regularly
- Ask clarifying questions if the task is unclear
"""


def with_base_prompt(system: str) -> str:
    """添加基础提示词"""
    base = f"""You are Claude Code, an AI assistant.
Working directory: {WORKDIR}

Always:
1. Be concise but thorough
2. Use tools when available
3. Report progress regularly
4. Ask clarifying questions if needed

"""
    return base + system


class TeamLeadAgent(PluginEnabledAgent):
    """简化版主管代理 - 使用 PluginEnabledAgent + 子 Agent 支持"""

    # 默认插件：技能加载 + 上下文压缩
    _default_plugins = [SkillPlugin, CompactPlugin]

    def __init__(
        self,
        dialog_id: str,
        plugins: Optional[List[Type[AgentPlugin]]] = None,
        **kwargs,
    ):
        self.dialog_id = dialog_id

        # 构建基础工具
        tools, handlers = self._build_toolkit()

        # 构建系统提示词
        system_prompt = with_base_prompt(LEAD_SYSTEM)

        # 初始化 PluginEnabledAgent（会自动注册 _default_plugins）
        super().__init__(
            system=system_prompt,
            tools=tools,
            tool_handlers=handlers,
            plugins=plugins,
            enable_default_plugins=True,  # 启用默认插件
            **kwargs
        )

    def _build_toolkit(self) -> tuple[list, dict]:
        """构建工具集（带插件支持）"""
        dialog_id = self.dialog_id

        @tool(description="Spawn a persistent teammate that runs in its own thread with a specific role.")
        def spawn_teammate(name: str, role: str, prompt: str) -> str:
            """Spawn a teammate with the given name, role and initial task."""
            return SUBAGENT_MANAGER.spawn(
                name=name,
                role=role,
                prompt=prompt,
                dialog_id=dialog_id,
                get_hook_kwargs=lambda n: self._get_subagent_hooks(n)
            )

        @tool(description="List all spawned teammates and their status.")
        def list_teammates() -> str:
            """List all teammates with their current status."""
            teammates = SUBAGENT_MANAGER.list_all()
            if not teammates:
                return "No teammates spawned yet."
            lines = ["Teammates:"]
            for t in teammates:
                lines.append(f"  - {t['name']} ({t['role']}): {t['status']}")
            return "\n".join(lines)

        @tool(description="Get the status of a specific teammate.")
        def get_teammate_status(name: str) -> str:
            """Get the current status of a teammate."""
            status = SUBAGENT_MANAGER.get_status(name)
            if status is None:
                return f"Teammate '{name}' not found."
            return f"'{name}' status: {status}"

        @tool(description="Send a message to a specific teammate.")
        def send_message(to: str, content: str) -> str:
            return f"Message sent to {to}: {content[:50]}..."

        @tool(description="Broadcast a message to all teammates.")
        def broadcast(content: str) -> str:
            return f"Broadcast: {content[:50]}..."

        tools, handlers = build_tools_and_handlers([spawn_teammate, list_teammates, get_teammate_status, send_message, broadcast])

        return tools, handlers

    def _get_subagent_hooks(self, agent_name: str) -> Dict[str, Callable]:
        """
        为子 Agent 生成 WebSocket 钩子

        子 Agent 有自己的 agent_name，但使用相同的 dialog_id
        """
        from agents.api.agent_bridge import AgentWebSocketBridge

        bridge = AgentWebSocketBridge(
            dialog_id=self.dialog_id,
            agent_name=agent_name
        )
        return bridge.get_hook_kwargs()

    def run_with_inbox(self, messages: list[dict]) -> str:
        """运行代理处理消息（带插件支持）"""
        # 转换消息格式
        converted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        # 提取文本内容
                        text_parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                        content = "".join(text_parts)
                    converted_messages.append({"role": "user", "content": content})
                elif msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                        content = "".join(text_parts)
                    converted_messages.append({"role": "assistant", "content": content})
                elif msg.get("role") == "tool":
                    # 保留 tool 消息
                    converted_messages.append(msg)

        if not converted_messages:
            converted_messages = [{"role": "user", "content": "Hello"}]

        # 插件：运行前处理
        self.plugin_manager.on_before_run(converted_messages)

        # 运行代理循环
        result = self.run(converted_messages)

        # 插件：运行后处理（如果有需要）
        # self.plugin_manager.on_after_run(converted_messages)

        return result


class SubAgentWithPlugins(PluginEnabledAgent):
    """
    带插件支持的子 Agent

    使用 PluginEnabledAgent 作为基类，简化实现
    """

    # 默认插件：技能加载 + 上下文压缩
    _default_plugins = [SkillPlugin, CompactPlugin]

    def __init__(
        self,
        name: str,
        role: str,
        **kwargs,
    ):
        self.name = name
        self.role = role

        # 构建系统提示词
        system_prompt = f"""You are '{name}', a specialized teammate with role: {role}.
Working directory: {WORKDIR}

You are part of a team. Complete your assigned task efficiently and thoroughly.
IMPORTANT: Provide complete, detailed answers. Do not stop until you have fully addressed the task.
When done, summarize your work.
"""

        # 初始化 PluginEnabledAgent（会自动注册 _default_plugins）
        super().__init__(
            system=system_prompt,
            tools=OPS.get_tools(),
            enable_default_plugins=True,  # 启用默认插件
            **kwargs
        )

    def run_with_inbox(self, messages: list[dict]) -> str:
        """运行子 Agent 处理消息"""
        # 转换消息格式
        converted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                        content = "".join(text_parts)
                    converted_messages.append({"role": "user", "content": content})
                elif msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                        content = "".join(text_parts)
                    converted_messages.append({"role": "assistant", "content": content})
                elif msg.get("role") == "tool":
                    converted_messages.append(msg)

        if not converted_messages:
            converted_messages = [{"role": "user", "content": "Hello"}]

        # 使用父类的 run_with_plugins
        return self.run_with_plugins(converted_messages)


# 兼容性导出
__all__ = ["TeamLeadAgent", "SubAgentWithPlugins", "SkillPlugin", "CompactPlugin", "SUBAGENT_MANAGER"]
