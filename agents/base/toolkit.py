from __future__ import annotations

import inspect
import types
from typing import Any, Callable, get_args, get_origin


class ToolDefinitionError(ValueError):
    """工具定义不合法时抛出。"""


def _map_python_type_to_json_schema(annotation: Any) -> dict[str, Any]:
    """将常见 Python 类型映射为 JSON Schema。"""
    if annotation is inspect._empty:
        return {"type": "string"}

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Optional[T] / Union[T, None]
    if origin is not None and str(origin).endswith("Union"):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _map_python_type_to_json_schema(non_none[0])
        return {"type": "string"}

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}

    if origin in (list, tuple):
        item_schema = _map_python_type_to_json_schema(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item_schema}

    if origin is dict or annotation is dict:
        return {"type": "object"}

    return {"type": "string"}


def _build_parameters_from_signature(func: Callable[..., Any]) -> dict[str, Any]:
    """根据函数签名自动构建工具的 parameters（OpenAI 格式）。"""
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in sig.parameters.values():
        if param.kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
            raise ToolDefinitionError(
                f"Tool function '{func.__name__}' contains unsupported parameter kind: {param.kind}"
            )

        properties[param.name] = _map_python_type_to_json_schema(param.annotation)
        if param.default is inspect._empty:
            required.append(param.name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _summary_from_docstring(func: Callable[..., Any]) -> str:
    """提取函数文档字符串首行作为工具描述。"""
    doc = inspect.getdoc(func) or ""
    for line in doc.splitlines():
        text = line.strip()
        if text:
            return text
    return ""


def tool(
    _func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]] | Callable[..., Any]:
    """将普通函数标记为工具（OpenAI 格式）。

    支持两种写法：
    1) `@tool`
    2) `@tool(name="...", description="...")`
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or func.__name__
        tool_description = description or _summary_from_docstring(func) or f"Tool: {tool_name}"
        params = parameters or _build_parameters_from_signature(func)

        setattr(
            func,
            "__tool_spec__",
            {
                "name": tool_name,
                "description": tool_description,
                "parameters": params,
            },
        )
        return func

    if _func is not None:
        return decorator(_func)
    return decorator


def build_tools_and_handlers(functions: list[Callable[..., Any]]) -> tuple[list[dict[str, Any]], dict[str, Callable[..., Any]]]:
    """从工具函数列表自动构建 TOOLS 和 TOOL_HANDLERS（OpenAI 格式）。"""
    merged_tools = build_tools(functions)
    tools: list[dict[str, Any]] = []
    handlers: dict[str, Callable[..., Any]] = {}

    for item in merged_tools:
        name = item["name"]
        handler = item["handler"]
        # OpenAI format: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
        tools.append({
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item["description"],
                "parameters": item["parameters"],
            }
        })
        handlers[name] = handler

    return tools, handlers


def build_tools(functions: list[Callable[..., Any]]) -> list[dict[str, Any]]:
    """从工具函数列表构建合并后的 tools（每项内含 handler，OpenAI 格式）。"""
    tools: list[dict[str, Any]] = []
    names: set[str] = set()

    for func in functions:
        spec = getattr(func, "__tool_spec__", None)
        if not spec:
            raise ToolDefinitionError(
                f"Function '{func.__name__}' is not a tool. Add @tool decorator first."
            )

        name = spec["name"]
        if name in names:
            raise ToolDefinitionError(f"Duplicate tool name: '{name}'")
        names.add(name)

        tools.append(
            {
                "name": name,
                "description": spec["description"],
                "parameters": spec["parameters"],
                "handler": func,
            }
        )

    return tools


def scan_tools_and_handlers(namespace: dict[str, Any] | types.ModuleType) -> tuple[list[dict[str, Any]], dict[str, Callable[..., Any]]]:
    """自动扫描命名空间中被 @tool 标记的函数并构建 TOOLS/handlers。"""
    if isinstance(namespace, types.ModuleType):
        values = vars(namespace).values()
    else:
        values = namespace.values()

    functions: list[Callable[..., Any]] = []
    for value in values:
        if callable(value) and hasattr(value, "__tool_spec__"):
            functions.append(value)

    return build_tools_and_handlers(functions)


def scan_tools(namespace: dict[str, Any] | types.ModuleType) -> list[dict[str, Any]]:
    """自动扫描命名空间中被 @tool 标记的函数并构建合并 tools。"""
    if isinstance(namespace, types.ModuleType):
        values = vars(namespace).values()
    else:
        values = namespace.values()

    functions: list[Callable[..., Any]] = []
    for value in values:
        if callable(value) and hasattr(value, "__tool_spec__"):
            functions.append(value)

    return build_tools(functions)
