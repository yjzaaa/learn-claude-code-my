"""
Config Adapter - Deep Agent 配置适配器

将 EngineConfig 转换为 DeepAgentConfig。
"""
import os
from typing import Any
from pydantic import BaseModel, Field
from core.models.config import EngineConfig


class DeepAgentConfig(BaseModel):
    """Deep Agent 配置模型"""
    name: str = ""
    model: str = Field(default_factory=lambda: os.getenv("MODEL_ID", "claude-sonnet-4-6"))
    system: str = ""
    system_prompt: str = ""  # 别名
    skills: list[str] = Field(default_factory=list)
    subagents: list[Any] = Field(default_factory=list)
    interrupt_on: dict[str, Any] = Field(default_factory=dict)


class DeepConfigAdapter:
    """Deep Agent 配置适配器"""

    @staticmethod
    def adapt(config: EngineConfig | dict, agent_id: str) -> DeepAgentConfig:
        """将配置转换为 DeepAgentConfig"""
        if isinstance(config, DeepAgentConfig):
            return config

        if isinstance(config, dict):
            return DeepAgentConfig.model_validate(config)

        # EngineConfig
        config_dict = config.model_dump()

        # 处理 skills
        skills_value = config_dict.get("skills", [])
        if isinstance(skills_value, dict):
            skills_list = []
            if skills_value.get("skills_dir"):
                skills_dir = skills_value["skills_dir"]
                if os.path.exists(skills_dir):
                    skills_list = [
                        d for d in os.listdir(skills_dir)
                        if os.path.isdir(os.path.join(skills_dir, d))
                    ]
            skills_value = skills_list

        # 获取模型名称
        model = os.getenv("MODEL_ID")
        if not model:
            model = config_dict.get("provider", {}).get("model", "claude-sonnet-4-6")

        return DeepAgentConfig(
            name=config_dict.get("name", agent_id),
            model=model,
            system=config_dict.get("system", ""),
            system_prompt=config_dict.get("system_prompt", ""),
            skills=skills_value if isinstance(skills_value, list) else [],
            subagents=config_dict.get("subagents", []),
            interrupt_on=config_dict.get("interrupt_on", {}),
        )
