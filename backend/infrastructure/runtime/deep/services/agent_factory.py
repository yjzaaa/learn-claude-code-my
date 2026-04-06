"""Agent Factory - 统一创建 Deep Agent，消除重复构建逻辑。

本模块提供统一的 Agent 构建入口，解决以下问题：
1. facade.py、initializer.py、model_switcher.py 中重复的 Builder 链
2. 配置分散，难以维护和测试
3. 模型切换时需要重建 Agent 的逻辑重复

Usage:
    context = AgentBuildContext(...)
    agent = AgentFactory.build(context)

    # 模型切换时重建
    new_agent = AgentFactory.rebuild_for_model_switch(context, new_model)
"""

from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass(frozen=True)
class AgentBuildContext:
    """构建 Agent 所需的全部上下文。

    Attributes:
        agent_id: Agent 唯一标识
        name: 显示名称（可选，默认使用 agent_id）
        model: LangChain 模型实例
        tools: 工具列表
        system_prompt: 系统提示词
        backend: Backend 实例（如 WindowsShellBackend）
        checkpointer: LangGraph checkpointer
        store: LangGraph store
        skills: 技能名称列表
        skill_sources: 技能路径列表（与 backend 的 virtual_root 一致）
        interrupt_on: HITL 配置（可选）
    """

    agent_id: str
    model: Any
    tools: list[Any]
    system_prompt: str
    backend: Any
    checkpointer: Any
    store: Any
    skills: list[str]
    name: str | None = None
    skill_sources: list[str] | None = None
    interrupt_on: dict[str, bool] | None = None


class AgentFactory:
    """统一 Agent 构建工厂。

    提供两种构建方式：
    1. build: 从零构建新 Agent
    2. rebuild_for_model_switch: 保留配置，仅切换模型
    """

    @staticmethod
    def build(context: AgentBuildContext) -> Any:
        """根据上下文构建 Agent。

        Args:
            context: 构建所需的完整上下文

        Returns:
            构建好的 CompiledStateGraph Agent

        Raises:
            RuntimeError: 构建失败时抛出
        """
        from backend.infrastructure.runtime.deep.agents import AgentBuilder

        try:
            skill_sources = context.skill_sources or AgentFactory._build_skill_sources(
                context.skills
            )

            builder = (
                AgentBuilder()
                .with_name(context.name or context.agent_id)
                .with_model(context.model)
                .with_tools(context.tools)
                .with_system_prompt(context.system_prompt)
                .with_backend(context.backend)
                .with_checkpointer(context.checkpointer)
                .with_store(context.store)
                .with_skills(context.skills, sources=skill_sources)
                .with_todo_list()
                .with_filesystem()
                .with_claude_compression(level="standard", enable_session_memory=True)
                .with_prompt_caching()
            )

            if context.interrupt_on:
                builder.with_human_in_the_loop(interrupt_on=context.interrupt_on)

            agent = builder.build()
            logger.info(f"[AgentFactory] Built agent: {context.agent_id}")
            return agent

        except Exception as e:
            logger.error(f"[AgentFactory] Failed to build agent: {e}")
            raise RuntimeError(f"Failed to build agent: {e}") from e

    @staticmethod
    def rebuild_for_model_switch(
        context: AgentBuildContext,
        new_model: Any,
    ) -> Any:
        """模型切换时重建 Agent，保留其他所有配置。

        Args:
            context: 原始构建上下文
            new_model: 新的模型实例

        Returns:
            使用新模型重建的 Agent
        """
        logger.info(f"[AgentFactory] Rebuilding agent {context.agent_id} with new model")
        new_context = AgentBuildContext(
            agent_id=context.agent_id,
            name=context.name,
            model=new_model,
            tools=context.tools,
            system_prompt=context.system_prompt,
            backend=context.backend,
            checkpointer=context.checkpointer,
            store=context.store,
            skills=context.skills,
            skill_sources=context.skill_sources,
            interrupt_on=context.interrupt_on,
        )
        return AgentFactory.build(new_context)

    @staticmethod
    def _build_skill_sources(skills: list[str]) -> list[str]:
        """根据技能名称列表构建默认的 skill_sources 路径。

        路径格式与 backend 的 virtual_root 一致：/workspace/skills/{skill}/

        Args:
            skills: 技能名称列表

        Returns:
            skill 路径列表
        """
        return [f"/workspace/skills/{skill}/" for skill in skills]


__all__ = ["AgentFactory", "AgentBuildContext"]
