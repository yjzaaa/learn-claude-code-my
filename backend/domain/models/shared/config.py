"""
Config Models - 配置模型

所有管理器配置的数据类定义。
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StateConfig(BaseModel):
    """状态管理器配置"""

    state_dir: Path | None = None


class DialogConfig(BaseModel):
    """对话管理器配置"""

    max_history: int = 100
    token_threshold: int = 8000


class ToolManagerConfig(BaseModel):
    """工具管理器配置"""

    pass


class MemoryConfig(BaseModel):
    """记忆管理器配置"""

    max_short_term: int = 50
    max_long_term: int = 1000
    enable_summarization: bool = True


class SkillManagerConfig(BaseModel):
    """技能管理器配置"""

    skills_dir: Path | None = None


class ProviderConfig(BaseModel):
    """Provider 配置

    注意：实际生产代码应优先使用 ProviderManager 获取配置
    此类主要用于向后兼容和类型定义
    """

    model: str | None = None  # None 表示使用 ProviderManager 配置
    api_key: str | None = None
    base_url: str | None = None


class EngineConfig(BaseModel):
    """引擎总配置"""

    state: StateConfig = Field(default_factory=StateConfig)
    dialog: DialogConfig = Field(default_factory=DialogConfig)
    tools: ToolManagerConfig = Field(default_factory=ToolManagerConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    skills: SkillManagerConfig = Field(default_factory=SkillManagerConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)

    @classmethod
    def from_dict(cls, config: dict[str, Any] | None = None) -> "EngineConfig":
        """从字典创建配置"""
        if not config:
            return cls()
        return cls(
            state=StateConfig(**config.get("state", {})),
            dialog=DialogConfig(**config.get("dialog", {})),
            tools=ToolManagerConfig(**config.get("tools", {})),
            memory=MemoryConfig(**config.get("memory", {})),
            skills=SkillManagerConfig(**config.get("skills", {})),
            provider=ProviderConfig(**config.get("provider", {})),
        )


class AgentConfig(BaseModel):
    """Agent 配置

    注意：实际生产代码应优先使用 ProviderManager 获取模型配置
    此类主要用于向后兼容和类型定义
    """

    system: str = ""
    model: str | None = None  # None 表示使用 ProviderManager 配置
    api_key: str | None = None
    base_url: str | None = None
    max_iterations: int = 10
    tools: list[str] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "AgentConfig":
        """从字典创建配置"""
        return cls(
            system=config.get("system", ""),
            model=config.get("model"),  # None 表示使用 ProviderManager
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            max_iterations=config.get("max_iterations", 10),
            tools=config.get("tools", []),
        )
