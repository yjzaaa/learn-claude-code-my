"""Skill Selector - 根据用户问题选择相关技能

解决所有 skill 同时加载导致提示词过长的问题。
"""

from typing import TYPE_CHECKING

from backend.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from .skill_manager import SkillManager

logger = get_logger(__name__)


class SkillSelector:
    """技能选择器

    根据用户问题的关键词，从所有可用技能中选择最相关的技能。
    """

    # 技能触发关键词映射
    SKILL_TRIGGERS: dict[str, list[str]] = {
        "finance": [
            # 财务相关
            "费用",
            "分摊",
            "预算",
            "实际",
            "对比",
            "fy",
            "财年",
            "year",
            "scenario",
            "budget",
            "actual",
            "allocation",
            "分摊给",
            "allocated to",
            "it费用",
            "hr费用",
            "cost",
            "amount",
            "ct",
            "xp",
            "业务线",
            "成本中心",
            "cc",
            "insightbot",
            "ssme",
        ],
        "code-review": [
            "review",
            "代码审查",
            "code review",
            "审查",
            "重构",
            "refactor",
            "优化代码",
            "改进代码",
        ],
        "agent-builder": [
            "agent",
            "智能体",
            "create agent",
            "创建agent",
            "build agent",
            "agent框架",
        ],
        "skill-creator": [
            "create skill",
            "创建技能",
            "skill",
            "技能",
            "package skill",
            "打包技能",
        ],
        "pdf": [
            "pdf",
            "pdf处理",
            "pdf转换",
            "pdf提取",
        ],
        "deep-agents-core": [
            "deep agent",
            "todo",
            "middleware",
            "langgraph",
        ],
        "langchain-fundamentals": [
            "langchain",
            "create_agent",
            "@tool",
            "tool()",
        ],
        "langgraph-fundamentals": [
            "langgraph",
            "stategraph",
            "workflow",
        ],
        "langchain-rag": [
            "rag",
            "retrieval",
            "embedding",
            "vector",
            "chroma",
        ],
        "mcp-builder": [
            "mcp",
            "model context protocol",
            "mcp server",
        ],
    }

    def __init__(self, skill_manager: "SkillManager"):
        self._skill_mgr = skill_manager

    def select_skills(self, user_message: str) -> list[str]:
        """根据用户问题选择相关技能

        Args:
            user_message: 用户输入消息

        Returns:
            选中的 skill ID 列表
        """
        if not user_message:
            return []

        message_lower = user_message.lower()
        selected = set()

        # 检查每个技能的触发词
        for skill_id, triggers in self.SKILL_TRIGGERS.items():
            # 确保技能存在
            if not any(s.id == skill_id for s in self._skill_mgr.list_skills()):
                continue

            for trigger in triggers:
                if trigger.lower() in message_lower:
                    selected.add(skill_id)
                    logger.debug(f"[SkillSelector] '{trigger}' matched skill '{skill_id}'")
                    break

        # 如果没有匹配任何技能，返回空列表（不加载任何技能）
        if not selected:
            logger.debug("[SkillSelector] No skills matched")
            return []

        logger.info(f"[SkillSelector] Selected skills: {selected}")
        return list(selected)

    def select_skills_with_scores(self, user_message: str) -> list[tuple[str, float]]:
        """选择技能并返回匹配分数

        Args:
            user_message: 用户输入消息

        Returns:
            [(skill_id, score), ...] 按分数降序排列
        """
        if not user_message:
            return []

        message_lower = user_message.lower()
        scores: dict[str, float] = {}

        for skill_id, triggers in self.SKILL_TRIGGERS.items():
            if not any(s.id == skill_id for s in self._skill_mgr.list_skills()):
                continue

            matched_triggers = 0
            for trigger in triggers:
                if trigger.lower() in message_lower:
                    matched_triggers += 1

            if matched_triggers > 0:
                # 简单计分：匹配触发词数量 / 总触发词数量
                scores[skill_id] = matched_triggers / len(triggers)

        # 按分数降序排列
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        logger.info(f"[SkillSelector] Scores: {sorted_scores}")
        return sorted_scores


def create_skill_selector(skill_manager: "SkillManager") -> SkillSelector:
    """创建技能选择器"""
    return SkillSelector(skill_manager)
