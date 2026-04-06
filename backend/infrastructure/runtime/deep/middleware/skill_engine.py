"""
Skill Engine Middleware - 技能引擎中间件

实现技能发现、排序、注入和两阶段执行的核心中间件。
与 MemoryMiddleware 协调工作，SkillEngineMiddleware 先于 MemoryMiddleware 执行。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import SystemMessage
from langgraph.runtime import Runtime

from backend.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from backend.infrastructure.services.skill_manager import SkillManager
    from backend.infrastructure.services.skill_ranker import RankedSkill, SkillRanker

logger = get_logger(__name__)

# Backend hints for available tools
BACKEND_HINTS = {
    "shell": "Use shell tools for running scripts, file operations, and system commands.",
    "mcp": "Use MCP tools for external integrations and third-party services.",
    "gui": "Use GUI automation tools for interacting with desktop applications.",
    "docker": "Use Docker tools for container management and sandboxed execution.",
    "browser": "Use browser tools for web navigation and data extraction.",
    "database": "Use database tools for SQL queries and data manipulation.",
}

# Resource access guidance
RESOURCE_ACCESS_TIPS = """
## Resource Access Tips

- Use `read_file` / `write_file` for file operations
- Use `list_dir` / `search_files` for directory exploration
- File paths are relative to each skill's directory (listed under each skill heading)
- Always verify file existence before reading
"""


@dataclass
class SkillEngineConfig:
    """技能引擎配置"""

    enabled: bool = True
    max_select: int = 2
    embedding_enabled: bool = False
    two_phase_enabled: bool = True
    quality_threshold: float = 0.3


@dataclass
class SkillExecutionState:
    """技能执行状态跟踪"""

    phase: str = "idle"  # idle, phase1, phase2, completed
    selected_skills: list[str] = field(default_factory=list)
    phase1_iterations: int = 0
    phase2_iterations: int = 0
    fallback_triggered: bool = False
    workspace_snapshot: set[str] = field(default_factory=set)


class SkillEngineMiddleware(AgentMiddleware):
    """技能引擎中间件

    职责：
    1. 在模型调用前发现、排序和注入相关技能
    2. 协调两阶段执行：Skill-First → Tool-Fallback
    3. 跟踪执行指标并更新技能质量数据

    执行顺序（相对于 MemoryMiddleware）：
    1. SkillEngineMiddleware.abefore_model() → 发现技能、注入提示词
    2. MemoryMiddleware.abefore_model() → 加载相关记忆
    3. LLM 调用
    4. SkillEngineMiddleware.aafter_model() → 追踪执行结果

    Attributes:
        skill_manager: 技能管理器
        skill_ranker: 技能排序器
        config: 技能引擎配置
        _execution_state: 当前执行状态
    """

    tools = ()

    def __init__(
        self,
        skill_manager: SkillManager,
        skill_ranker: SkillRanker | None = None,
        config: SkillEngineConfig | None = None,
    ):
        """初始化 SkillEngineMiddleware

        Args:
            skill_manager: 技能管理器实例
            skill_ranker: 技能排序器实例（可选）
            config: 技能引擎配置（可选）
        """
        self.skill_manager = skill_manager
        self.skill_ranker = skill_ranker
        self.config = config or SkillEngineConfig()
        self._execution_state = SkillExecutionState()

        # 验证配置
        self._validate_config()

        logger.info(
            f"[SkillEngineMiddleware] Initialized with enabled={self.config.enabled}, "
            f"max_select={self.config.max_select}, two_phase={self.config.two_phase_enabled}"
        )

    def _validate_config(self) -> None:
        """验证配置有效性"""
        if self.config.max_select < 1:
            logger.warning(
                f"[SkillEngineMiddleware] max_select ({self.config.max_select}) < 1, "
                "setting to 1"
            )
            self.config.max_select = 1

        if self.config.max_select > 5:
            logger.warning(
                f"[SkillEngineMiddleware] max_select ({self.config.max_select}) > 5, "
                "consider reducing to prevent prompt bloat"
            )

    async def abefore_model(
        self,
        state: AgentState,
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """在模型调用前发现技能并注入提示词

        1. 获取最后一条用户消息作为查询
        2. 使用 SkillRanker 发现和排序技能
        3. 注入技能提示词到系统消息

        Args:
            state: Agent 状态
            runtime: 运行时上下文

        Returns:
            包含修改后 messages 的字典，如果没有技能则返回 None
        """
        if not self.config.enabled:
            logger.debug("[SkillEngineMiddleware] Disabled, skipping skill discovery")
            return None

        messages = list(state.get("messages", []))
        if not messages:
            logger.debug("[SkillEngineMiddleware] No messages, skipping")
            return None

        # 获取查询
        query = self._get_last_user_message(messages)
        if not query:
            logger.debug("[SkillEngineMiddleware] No user message found")
            return None

        try:
            # 发现和排序技能
            ranked_skills = await self._discover_and_rank_skills(query)

            if not ranked_skills:
                logger.debug("[SkillEngineMiddleware] No skills found for query")
                return None

            # 质量过滤
            filtered_skills = self._apply_quality_filter(ranked_skills)

            if not filtered_skills:
                logger.debug("[SkillEngineMiddleware] All skills filtered by quality")
                return None

            # 选择前 N 个技能
            selected_skills = filtered_skills[: self.config.max_select]
            self._execution_state.selected_skills = [s.skill.id for s in selected_skills]

            # 注入技能提示词
            new_messages = self._inject_skill_prompts(messages, selected_skills)

            logger.info(
                f"[SkillEngineMiddleware] Injected {len(selected_skills)} skills: "
                f"{self._execution_state.selected_skills}"
            )

            return {"messages": new_messages}

        except Exception as e:
            logger.error(f"[SkillEngineMiddleware] Error in abefore_model: {e}")
            # 错误时优雅降级：不注入技能，继续执行
            return None

    async def _discover_and_rank_skills(self, query: str) -> list[RankedSkill]:
        """发现并排序技能

        Args:
            query: 用户查询

        Returns:
            排序后的技能列表
        """
        # 获取所有可用技能
        all_skills = self.skill_manager.list_skills()

        if not all_skills:
            logger.debug("[SkillEngineMiddleware] No skills available")
            return []

        # 如果有 SkillRanker，使用混合排序
        if self.skill_ranker:
            try:
                ranked = await self.skill_ranker.hybrid_rank(
                    query=query,
                    skills=all_skills,
                    top_k=max(self.config.max_select * 2, 5),
                )
                logger.debug(f"[SkillEngineMiddleware] Ranked {len(ranked)} skills")
                return ranked
            except Exception as e:
                logger.error(f"[SkillEngineMiddleware] SkillRanker failed: {e}")
                # 回退：按名称简单匹配
                return self._fallback_rank(query, all_skills)

        # 无 SkillRanker：使用简单匹配
        return self._fallback_rank(query, all_skills)

    def _fallback_rank(self, query: str, skills: list[Any]) -> list[Any]:
        """回退排序：简单的关键词匹配

        Args:
            query: 用户查询
            skills: 技能列表

        Returns:
            排序后的技能列表
        """
        query_lower = query.lower()
        scored = []

        for skill in skills:
            score = 0.0
            name = skill.definition.name.lower()
            description = skill.definition.description.lower()

            # 名称匹配权重更高
            if name in query_lower:
                score += 2.0
            # 关键词匹配
            query_words = set(query_lower.split())
            name_words = set(name.split())
            desc_words = set(description.split())

            score += len(query_words & name_words) * 0.5
            score += len(query_words & desc_words) * 0.2

            if score > 0:
                scored.append((skill, score))

        # 按分数排序
        scored.sort(key=lambda x: x[1], reverse=True)

        # 转换为 RankedSkill 格式
        from backend.infrastructure.services.skill_ranker import RankedSkill

        return [
            RankedSkill(skill=skill, bm25_score=score, final_score=score)
            for skill, score in scored
        ]

    def _apply_quality_filter(self, ranked_skills: list[RankedSkill]) -> list[RankedSkill]:
        """应用质量过滤

        过滤规则：
        1. 分数低于阈值的技能
        2. 被标记为低质量的技能

        Args:
            ranked_skills: 排序后的技能列表

        Returns:
            过滤后的技能列表
        """
        filtered = []
        for ranked in ranked_skills:
            # 分数过滤
            if ranked.final_score < self.config.quality_threshold:
                logger.debug(
                    f"[SkillEngineMiddleware] Skill '{ranked.skill.id}' "
                    f"filtered by score ({ranked.final_score:.3f} < {self.config.quality_threshold})"
                )
                continue

            # TODO: 从 SkillStore 获取质量数据并过滤
            # if skill_store and skill_store.is_filtered(ranked.skill.id):
            #     continue

            filtered.append(ranked)

        return filtered

    def _get_available_backends(self) -> list[str]:
        """获取可用后端列表

        从运行时配置中解析可用的后端工具类型。

        Returns:
            可用后端类型列表
        """
        # 从运行时配置获取 backend_scope
        backends = []

        # 检查是否有 backend 配置
        if hasattr(self, "_backend") and self._backend:
            backend_id = getattr(self._backend, "id", "")
            if backend_id:
                backends.append(backend_id)

        # 从技能管理器获取工具类型
        if self.skill_manager:
            active_tools = self.skill_manager.get_active_tools()
            for tool_info in active_tools:
                tool_name = tool_info.tool.get("name", "")
                # 根据工具名称推断后端类型
                if "shell" in tool_name or "execute" in tool_name:
                    backends.append("shell")
                elif "mcp" in tool_name:
                    backends.append("mcp")
                elif "docker" in tool_name:
                    backends.append("docker")
                elif "browser" in tool_name:
                    backends.append("browser")
                elif "sql" in tool_name or "db" in tool_name:
                    backends.append("database")

        # 去重并返回
        return list(set(backends)) if backends else ["shell"]

    def _build_backend_hint(self, backends: list[str] | None = None) -> str:
        """构建后端提示词

        根据可用后端动态生成工具使用提示。

        Args:
            backends: 可用后端列表，默认自动检测

        Returns:
            后端提示词
        """
        if backends is None:
            backends = self._get_available_backends()

        hints = []
        for backend in backends:
            if backend in BACKEND_HINTS:
                hints.append(f"- {BACKEND_HINTS[backend]}")

        if not hints:
            return ""

        return "\n".join(["## Available Tools", ""] + hints)

    def _replace_basedir_placeholder(self, content: str, skill_path: str | None) -> str:
        """替换 {baseDir} 占位符

        将技能内容中的 {baseDir} 替换为实际的技能目录绝对路径。

        Args:
            content: 技能内容
            skill_path: 技能目录路径

        Returns:
            替换后的内容
        """
        if not skill_path or "{baseDir}" not in content:
            return content

        base_dir = Path(skill_path).resolve()
        return content.replace("{baseDir}", str(base_dir))

    def _build_skill_section(self, ranked: RankedSkill) -> str:
        """构建单个技能的提示词部分

        Args:
            ranked: 排序后的技能

        Returns:
            技能提示词部分
        """
        skill = ranked.skill
        skill_id = getattr(skill, "id", skill.definition.name)
        skill_path = getattr(skill, "path", None)

        # 获取技能提示词内容
        prompt = self.skill_manager.get_skill_prompt(skill.id)
        if not prompt:
            prompt = skill.definition.description

        # 替换 {baseDir} 占位符
        prompt = self._replace_basedir_placeholder(prompt, skill_path)

        # 构建技能部分
        lines = [
            f"### Skill: {skill_id}",
        ]

        if skill_path:
            lines.append(f"**Skill directory**: `{skill_path}`")

        lines.append("")
        lines.append(prompt)

        return "\n".join(lines)

    def _build_context_injection(
        self,
        selected_skills: list[RankedSkill],
        backends: list[str] | None = None,
    ) -> str:
        """构建完整的上下文注入内容

        包含：
        1. Active Skills header
        2. 使用说明
        3. 后端提示
        4. 资源访问提示
        5. 技能内容（用 --- 分隔）

        Args:
            selected_skills: 选中的技能列表
            backends: 可用后端列表

        Returns:
            完整的注入内容
        """
        if not selected_skills:
            return ""

        # 构建技能部分
        skill_sections = []
        for ranked in selected_skills:
            section = self._build_skill_section(ranked)
            if section:
                skill_sections.append(section)

        if not skill_sections:
            return ""

        # 构建 header
        header_lines = [
            "# Active Skills",
            "",
            "## How to use skills",
            "- Each skill provides specialized capabilities for specific tasks",
            "- Follow the instructions in each skill section carefully",
            "- Use file tools relative to the skill directory listed under each skill heading",
            "- If multiple skills apply, combine their guidance appropriately",
            "",
        ]

        # 添加后端提示
        backend_hint = self._build_backend_hint(backends)
        if backend_hint:
            header_lines.extend([backend_hint, ""])

        # 添加资源访问提示
        header_lines.extend([RESOURCE_ACCESS_TIPS, ""])

        # 组合所有内容
        full_content = "\n".join(header_lines)
        full_content += "\n\n---\n\n".join(skill_sections)

        return full_content

    def _inject_skill_prompts(
        self,
        messages: list[Any],
        selected_skills: list[RankedSkill],
    ) -> list[Any]:
        """将技能提示词注入到系统消息

        使用 Backend-Aware Prompt Injection 构建完整的技能上下文。

        Args:
            messages: 原始消息列表
            selected_skills: 选中的技能列表

        Returns:
            修改后的消息列表
        """
        if not selected_skills:
            return messages

        # 获取可用后端
        backends = self._get_available_backends()

        # 构建完整的上下文注入
        full_prompt = self._build_context_injection(selected_skills, backends)

        if not full_prompt:
            return messages

        # 注入到消息列表
        return self._inject_into_system_message(messages, full_prompt)

    def _inject_into_system_message(
        self,
        messages: list[Any],
        skill_prompt: str,
    ) -> list[Any]:
        """将技能提示词注入到系统消息

        Args:
            messages: 原始消息列表
            skill_prompt: 技能提示词

        Returns:
            修改后的消息列表
        """
        new_messages = list(messages)

        # 查找现有的 system message
        system_idx = -1
        for i, msg in enumerate(new_messages):
            if isinstance(msg, SystemMessage):
                system_idx = i
                break
            # 处理 dict 格式的消息
            if isinstance(msg, dict):
                role = msg.get("role", msg.get("type", ""))
                if role in ("system", "SystemMessage"):
                    system_idx = i
                    break

        if system_idx >= 0:
            # 在现有 system message 后追加技能提示
            existing_msg = new_messages[system_idx]
            if isinstance(existing_msg, SystemMessage):
                new_content = f"{existing_msg.content}\n\n{skill_prompt}"
                new_messages[system_idx] = SystemMessage(content=new_content)
            else:
                # dict 格式
                existing_content = existing_msg.get("content", "")
                new_content = f"{existing_content}\n\n{skill_prompt}"
                new_messages[system_idx] = {
                    **existing_msg,
                    "content": new_content,
                }
        else:
            # 在开头插入新的 system message
            new_messages.insert(0, SystemMessage(content=skill_prompt))

        return new_messages

    async def aafter_model(
        self,
        state: AgentState,
        runtime: Runtime,
        output: Any,
    ) -> dict[str, Any] | None:
        """在模型调用后跟踪执行结果

        1. 检测执行状态（成功/失败）
        2. 更新技能质量指标
        3. 如果 Phase 1 失败且启用了两阶段执行，触发回退

        Args:
            state: Agent 状态
            runtime: 运行时上下文
            output: 模型输出

        Returns:
            None（不修改状态）
        """
        if not self.config.enabled:
            return None

        try:
            # 检测执行状态
            status = self._detect_execution_status(state, output)

            # 更新执行状态
            if self._execution_state.phase == "phase1":
                self._execution_state.phase1_iterations += 1

                if status == "success":
                    self._execution_state.phase = "completed"
                    await self._track_skill_completion(success=True)
                elif status in ("error", "incomplete"):
                    if self.config.two_phase_enabled:
                        logger.info(
                            "[SkillEngineMiddleware] Phase 1 failed, triggering fallback"
                        )
                        self._execution_state.fallback_triggered = True
                        await self._track_skill_completion(success=False)
                        # 触发回退逻辑在 runtime 层处理

            elif self._execution_state.phase == "phase2":
                self._execution_state.phase2_iterations += 1

            # 记录指标
            logger.debug(
                f"[SkillEngineMiddleware] Execution status: {status}, "
                f"phase: {self._execution_state.phase}"
            )

        except Exception as e:
            logger.error(f"[SkillEngineMiddleware] Error in aafter_model: {e}")

        return None

    def _detect_execution_status(self, state: AgentState, output: Any) -> str:
        """检测执行状态

        Args:
            state: Agent 状态
            output: 模型输出

        Returns:
            状态: "success", "incomplete", "error", "ongoing"
        """
        # 检查是否有错误
        if output is None:
            return "error"

        # 检查是否完成
        if hasattr(output, "finish_reason"):
            if output.finish_reason == "stop":
                return "success"
            if output.finish_reason == "error":
                return "error"

        # 检查 dict 格式
        if isinstance(output, dict):
            if output.get("finish_reason") == "stop":
                return "success"
            if output.get("error"):
                return "error"

        # 检查是否有待处理的工具调用
        if self._has_pending_tool_calls(output):
            return "ongoing"

        # 检查状态中的迭代次数
        iterations = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 20)

        if iterations >= max_iterations:
            return "incomplete"

        return "ongoing"

    def _has_pending_tool_calls(self, output: Any) -> bool:
        """检查是否有待处理的工具调用"""
        if output is None:
            return False

        if hasattr(output, "tool_calls") and output.tool_calls:
            return True

        if isinstance(output, dict):
            if output.get("tool_calls"):
                return True
            if output.get("tool_call_ids"):
                return True

        try:
            from langchain_core.messages import AIMessage

            if isinstance(output, AIMessage) and output.tool_calls:
                return True
        except ImportError:
            pass

        return False

    async def _track_skill_completion(self, success: bool) -> None:
        """跟踪技能完成情况

        Args:
            success: 是否成功
        """
        # TODO: 更新 SkillStore 中的指标
        # for skill_id in self._execution_state.selected_skills:
        #     if skill_store:
        #         skill_store.record_completion(skill_id, success)

        logger.debug(
            f"[SkillEngineMiddleware] Tracked completion: success={success}, "
            f"skills={self._execution_state.selected_skills}"
        )

    def _get_last_user_message(self, messages: list[Any]) -> str | None:
        """获取最后一条用户消息

        Args:
            messages: 消息列表

        Returns:
            用户消息内容或 None
        """
        from langchain_core.messages import HumanMessage

        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
            if isinstance(msg, dict):
                role = msg.get("role", msg.get("type", ""))
                if role in ("human", "user", "HumanMessage"):
                    content = msg.get("content", "")
                    return str(content) if content else None
        return None

    def get_execution_state(self) -> SkillExecutionState:
        """获取当前执行状态"""
        return self._execution_state

    def reset_execution_state(self) -> None:
        """重置执行状态"""
        self._execution_state = SkillExecutionState()
        logger.debug("[SkillEngineMiddleware] Execution state reset")


__all__ = [
    "SkillEngineMiddleware",
    "SkillEngineConfig",
    "SkillExecutionState",
]
