"""
Config Models - 配置模型

所有管理器配置的数据类定义。
"""

from typing import Optional, Dict, Any
from pathlib import Path

from pydantic import BaseModel, Field

class StateConfig(BaseModel):
    """状态管理器配置"""
    state_dir: Optional[Path] = None

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
    skills_dir: Optional[Path] = None

class ProviderConfig(BaseModel):
    """Provider 配置"""
    model: str = "deepseek/deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class EngineConfig(BaseModel):
    """引擎总配置"""
    state: StateConfig = Field(default_factory=StateConfig)
    dialog: DialogConfig = Field(default_factory=DialogConfig)
    tools: ToolManagerConfig = Field(default_factory=ToolManagerConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    skills: SkillManagerConfig = Field(default_factory=SkillManagerConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)

    @classmethod
    def from_dict(cls, config: Optional[dict[str, Any]] = None) -> "EngineConfig":
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
    """Agent 配置"""
    system: str = ""
    model: str = "deepseek/deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_iterations: int = 10
    tools: list = Field(default_factory=list)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "AgentConfig":
        """从字典创建配置"""
        return cls(
            system=config.get("system", ""),
            model=config.get("model", "deepseek/deepseek-chat"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            max_iterations=config.get("max_iterations", 10),
            tools=config.get("tools", []),
        )
