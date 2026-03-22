"""
Config Models - 配置模型

所有管理器配置的数据类定义。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from dataclasses_json import dataclass_json  # type: ignore[import-not-found]
except ImportError:
    def dataclass_json(cls):  # type: ignore[no-redef]
        return cls


@dataclass_json
@dataclass
class StateConfig:
    """状态管理器配置"""
    state_dir: Optional[Path] = None


@dataclass_json
@dataclass
class DialogConfig:
    """对话管理器配置"""
    max_history: int = 100
    token_threshold: int = 8000


@dataclass_json
@dataclass
class ToolManagerConfig:
    """工具管理器配置"""
    pass


@dataclass_json
@dataclass
class MemoryConfig:
    """记忆管理器配置"""
    max_short_term: int = 50
    max_long_term: int = 1000
    enable_summarization: bool = True


@dataclass_json
@dataclass
class SkillManagerConfig:
    """技能管理器配置"""
    skills_dir: Optional[Path] = None


@dataclass_json
@dataclass
class ProviderConfig:
    """Provider 配置"""
    model: str = "deepseek/deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@dataclass_json
@dataclass
class EngineConfig:
    """引擎总配置"""
    state: StateConfig = field(default_factory=StateConfig)
    dialog: DialogConfig = field(default_factory=DialogConfig)
    tools: ToolManagerConfig = field(default_factory=ToolManagerConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    skills: SkillManagerConfig = field(default_factory=SkillManagerConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)

    @classmethod
    def from_dict(cls, config: Optional[Dict[str, Any]] = None) -> "EngineConfig":
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


@dataclass_json
@dataclass
class AgentConfig:
    """Agent 配置"""
    system: str = ""
    model: str = "deepseek/deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_iterations: int = 10
    tools: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "AgentConfig":
        """从字典创建配置"""
        return cls(
            system=config.get("system", ""),
            model=config.get("model", "deepseek/deepseek-chat"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            max_iterations=config.get("max_iterations", 10),
            tools=config.get("tools", []),
        )
