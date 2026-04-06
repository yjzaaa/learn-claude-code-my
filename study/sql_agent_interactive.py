"""
Interactive SQL Agent - 基于新架构的 SQL Agent

基于 BaseInteractiveAgent，自动集成前端交互能力
保留 V2 的核心功能：
- Master-Worker 架构
- LearningMemory 学习系统
- ToolCallMonitor 工具监控

优化点：
- 无需手动管理 WebSocket 回调
- 统一使用 models.py 中的类型
- 子类只需关注业务逻辑
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from .base import StreamingAgent, tool
from .s05_skill_loading import TOOLS as S05_TOOLS
from .sql_agent_loop_v2 import (
    MASTER_SYSTEM,
    LearningMemory,
    ToolCallMonitor,
    WorkerSubAgent,
)


class InteractiveSQLAgent(StreamingAgent):
    """
    交互式 SQL Agent

    继承 StreamingAgent，自动处理前端交互 (通过 Transport 层)
    内置 LearningMemory 和 Master-Worker 架构
    """

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        dialog_id: str,
        system: str = MASTER_SYSTEM,
        tools: list[Any] | None = None,
        max_tokens: int = 8000,
        max_rounds: int | None = 20,
        enable_learning: bool = True,
        memory_dir: Path | None = None,
        **base_kwargs
    ):
        # 准备工具（添加 task 工具和学习监控）
        self._learning_memory = LearningMemory(memory_dir) if enable_learning else None
        base_tools = list(tools or S05_TOOLS)
        task_tool = self._create_task_tool()
        base_tools.append(task_tool)

        # 添加工具监控
        if self._learning_memory:
            monitor = ToolCallMonitor(self._learning_memory)
            base_tools = self._wrap_tools_with_monitor(base_tools, monitor)

        # 保存供子代理使用的配置
        self._client = client
        self._model = model
        self._base_tools = S05_TOOLS  # 子代理使用基础工具

        # 初始化基类（会自动处理前端交互）
        super().__init__(
            client=client,
            model=model,
            system=system,
            tools=base_tools,
            dialog_id=dialog_id,
            agent_type=AgentType.MASTER.value,
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            enable_streaming=True,
            **base_kwargs
        )

        logger.info(f"[InteractiveSQLAgent] Initialized with learning={enable_learning}")

    def _wrap_tools_with_monitor(self, tools: list, monitor: ToolCallMonitor) -> list:
        """包装工具以启用监控"""
        wrapped = []
        for tool_fn in tools:
            tool_name = getattr(tool_fn, "__tool_spec__", {}).get("name", "unknown")
            wrapped.append(monitor.wrap_tool(tool_fn, tool_name))
        return wrapped

    def _create_task_tool(self):
        """创建 task 工具用于子代理委派"""

        @tool(name="task", description="""Delegate a task to a specialized worker subagent.

Args:
    worker_type: Type of worker - 'sql_executor', 'schema_explorer', 'data_validator', or 'analyzer'
    objective: Clear description of what the worker should accomplish
    context: Relevant context, schema info, or constraints

Returns:
    Summary of the worker's execution results
""")
        def task(worker_type: str, objective: str, context: str = "") -> str:
            """委派任务给子代理"""
            logger.info(f"> task [{worker_type}]: {objective[:60]}...")

            # 切换 agent_type 为 worker 类型
            prev_agent_type = self.agent_type
            self.agent_type = f"worker:{worker_type}"
            self.bridge.agent_type = self.agent_type

            try:
                # 创建子代理
                worker = WorkerSubAgent(
                    worker_type=worker_type,
                    client=self._client,
                    model=self._model,
                    tools=self._base_tools,
                    callbacks={"should_stop": self.state.check_should_stop}
                )

                # 运行并获取摘要
                summary = worker.run(objective=objective, context=context)
                logger.info(f"< task [{worker_type}] result: {summary[:100]}...")
                return summary

            except Exception as e:
                logger.error(f"Task delegation failed: {e}")
                return f"[Task Error: {e}]"

            finally:
                # 恢复 agent_type
                self.agent_type = prev_agent_type
                self.bridge.agent_type = prev_agent_type

        return task

    def run_conversation(self, messages: list[dict]) -> None:
        """
        运行完整对话

        流程:
        1. 初始化会话
        2. 执行标准 Agent 循环
        3. 完成会话收尾
        """
        self.initialize_session()

        try:
            # 使用基类的 run 方法执行标准循环
            # 所有消息和工具调用会自动发送到前端
            super().run(messages)
        except Exception as e:
            logger.error(f"[InteractiveSQLAgent] Run error: {e}")
            self.send_error(str(e))
            raise
        finally:
            self.finalize_session()

    def get_learning_summary(self) -> dict | None:
        """获取学习系统摘要"""
        if self._learning_memory:
            return self._learning_memory.get_session_summary()
        return None


# 保留工厂函数用于兼容

def build_interactive_sql_agent(
    *,
    client: Any,
    model: str,
    dialog_id: str,
    enable_learning: bool = True,
    memory_dir: Path | None = None,
    **kwargs
) -> InteractiveSQLAgent:
    """工厂函数：创建 InteractiveSQLAgent 实例"""
    return InteractiveSQLAgent(
        client=client,
        model=model,
        dialog_id=dialog_id,
        enable_learning=enable_learning,
        memory_dir=memory_dir,
        **kwargs
    )


__all__ = [
    "InteractiveSQLAgent",
    "build_interactive_sql_agent",
]
