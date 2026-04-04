"""
Tool Models - 工具模型

定义工具、工具规格和工具相关的 DTO。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List

from backend.domain.models.types import JSONSchema

try:
    from dataclasses_json import dataclass_json  # type: ignore[import-not-found]
except ImportError:
    def dataclass_json(cls):  # type: ignore[no-redef]
        return cls


@dataclass_json
@dataclass
class ToolFunction:
    """OpenAI Function 定义 (内部函数描述)"""
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass_json
@dataclass
class ToolSchema:
    """OpenAI Tool Schema (顶层包装，用于 API)"""
    type: str  # "function"
    function: ToolFunction


@dataclass_json
@dataclass
class ToolSpec:
    """工具规格 (从 __tool_spec__ 属性解析)"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, spec: Dict[str, Any], default_name: str = "") -> "ToolSpec":
        """从工具规格字典创建"""
        return cls(
            name=spec.get("name", default_name),
            description=spec.get("description", ""),
            parameters=spec.get("parameters", {"type": "object", "properties": {}}),
        )


@dataclass_json
@dataclass
class ToolDefinition:
    """工具定义 (用于注册和存储)"""
    name: str
    handler: Optional[Callable] = None  # 运行时填充
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass_json
@dataclass
class ToolInfo:
    """工具信息 (序列化后返回给客户端)"""
    name: str
    description: str
    parameters: JSONSchema


@dataclass_json
@dataclass
class ToolExecutionResult:
    """工具执行结果"""
    tool_call_id: str
    tool_name: str
    result: str
    error: Optional[str] = None


@dataclass_json
@dataclass
class ActiveToolInfo:
    """激活的工具信息 (包含技能关联)"""
    skill_id: str
    skill_name: str
    tool: Dict[str, Any]  # ToolInfo 的字典形式


@dataclass_json
@dataclass
class ToolCallBuffer:
    """流式响应中的工具调用缓冲"""
    id: str = ""
    name: str = ""
    arguments: str = ""

    def reset(self):
        """重置缓冲区"""
        self.id = ""
        self.name = ""
        self.arguments = ""
