"""
Tool Models - 工具模型 (Pydantic BaseModel 版本)

定义工具相关的 Pydantic 模型，替代 TypedDict。
合并自 tool_models.py 和 tool.py。
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ═══════════════════════════════════════════════════════════
# JSON Schema 相关
# ═══════════════════════════════════════════════════════════


class JSONSchemaProperty(BaseModel):
    """JSON Schema 属性定义"""

    type: str = "string"
    description: str | None = None
    items: dict[str, Any] | None = None  # for array type
    enum: list[str] | None = None
    properties: dict[str, "JSONSchemaProperty"] | None = None

    model_config = ConfigDict(extra="allow")


class JSONSchema(BaseModel):
    """JSON Schema (OpenAI function parameters 格式)"""

    type: str = "object"
    properties: dict[str, JSONSchemaProperty] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    description: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证 type 字段"""
        allowed = ["object", "array", "string", "number", "integer", "boolean", "null"]
        if v not in allowed:
            raise ValueError(f"type must be one of {allowed}, got {v}")
        return v

    model_config = ConfigDict(extra="allow")


# ═══════════════════════════════════════════════════════════
# OpenAI 格式工具定义
# ═══════════════════════════════════════════════════════════


class OpenAIFunctionSchema(BaseModel):
    """OpenAI Function Schema"""

    name: str
    description: str
    parameters: JSONSchema | dict[str, Any]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证 name 不为空"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v


class OpenAIToolSchema(BaseModel):
    """OpenAI Tool Schema (顶层包装)"""

    type: str = "function"
    function: OpenAIFunctionSchema

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证 type 必须是 function"""
        if v != "function":
            raise ValueError(f"type must be 'function', got {v}")
        return v


# ═══════════════════════════════════════════════════════════
# 工具规格和定义
# ═══════════════════════════════════════════════════════════


class ToolSpec(BaseModel):
    """工具规格定义 (从 __tool_spec__ 属性解析)"""

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parameters", mode="before")
    @classmethod
    def convert_parameters(cls, v: Any) -> Any:
        """将 JSONSchema 对象转换为字典"""
        if isinstance(v, BaseModel):
            return v.model_dump()
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证 name 不为空"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """验证 description 不为空"""
        if not v or not v.strip():
            raise ValueError("description cannot be empty")
        return v

    @classmethod
    def from_dict(cls, spec: dict[str, Any], default_name: str = "") -> "ToolSpec":
        """从工具规格字典创建"""
        return cls(
            name=spec.get("name", default_name),
            description=spec.get("description", ""),
            parameters=spec.get("parameters", {"type": "object", "properties": {}}),
        )


class ToolFunction(BaseModel):
    """OpenAI Function 定义 (内部函数描述)"""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolSchema(BaseModel):
    """OpenAI Tool Schema (顶层包装，用于 API)"""

    type: str = "function"
    function: ToolFunction


class ToolDefinition(BaseModel):
    """工具定义 (用于注册和存储)"""

    name: str
    handler: Callable | None = None  # 运行时填充
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ToolInfo(BaseModel):
    """工具信息 (序列化后返回给客户端)"""

    name: str
    description: str
    parameters: JSONSchema


class ToolExecutionResult(BaseModel):
    """工具执行结果"""

    tool_call_id: str
    tool_name: str
    result: str
    error: str | None = None


class ActiveToolInfo(BaseModel):
    """激活的工具信息 (包含技能关联)"""

    skill_id: str
    skill_name: str
    tool: dict[str, Any]  # ToolInfo 的字典形式


class ToolCallBuffer(BaseModel):
    """流式响应中的工具调用缓冲"""

    id: str = ""
    name: str = ""
    arguments: str = ""

    def reset(self):
        """重置缓冲区"""
        self.id = ""
        self.name = ""
        self.arguments = ""


class SkillToolRegistration(BaseModel):
    """技能工具注册信息"""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})
    handler: Callable | None = None  # 可选的处理函数

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MergedToolItem(BaseModel):
    """build_tools 返回的合并工具项"""

    name: str
    description: str
    parameters: JSONSchema
    handler: Callable[..., Any]

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ═══════════════════════════════════════════════════════════
# 向后兼容别名
# ═══════════════════════════════════════════════════════════

ToolFunctionSchema = OpenAIFunctionSchema
ToolSchemaType = OpenAIToolSchema


# ═══════════════════════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════════════════════

__all__ = [
    # JSON Schema
    "JSONSchemaProperty",
    "JSONSchema",
    # OpenAI 格式
    "OpenAIFunctionSchema",
    "OpenAIToolSchema",
    # 工具规格和定义
    "ToolSpec",
    "ToolFunction",
    "ToolSchema",
    "ToolDefinition",
    "ToolInfo",
    "ToolExecutionResult",
    "ActiveToolInfo",
    "ToolCallBuffer",
    "SkillToolRegistration",
    "MergedToolItem",
    # 别名
    "ToolFunctionSchema",
    "ToolSchemaType",
]
