## Context

项目最近完成了从裸 `dict` 到 Pydantic `BaseModel` / `TypedDict` 的大规模重构 (`0c6c860`)，但由于涉及文件众多，部分边界模块的类型签名仍然不一致。当前运行 `mypy core interfaces main.py` 会报告约 50 处错误，主要集中在：

1. `core/models/types.py` `__all__` 导出列表缺失大量新迁移到独立文件中的类型
2. `AgentRuntime` 抽象基类定义了 `EngineConfig` 作为 `initialize` 参数，但子类实现和调用方传入的是 `dict`
3. `send_message` 在基类中定义为 `async def -> AsyncIterator`，但 mypy 认为子类重写与协程返回类型不兼容
4. `ToolManager` 历史遗留了旧版 `ToolSpec` 的导入路径，与新版 `core.models.tool_models.ToolSpec` 混用
5. `StreamToolCallDict` (TypedDict) 在多处被当作普通 `dict` 进行 `.get()` 和索引访问
6. `runtime/logging_config.py` 的辅助函数返回签名与实际返回值不一致
7. `interfaces/agent_runtime_bridge.py` 直接传递 `dict` 给需要 `EngineConfig` 的接口

## Goals / Non-Goals

**Goals:**
- 运行 `mypy core interfaces main.py --ignore-missing-imports --show-error-codes` 零错误通过
- 保持现有运行时行为不变（纯类型修复，不改动逻辑）
- 所有修复符合 CLAUDE.md 中定义的代码规范（Pydantic 优先、显式类型注解、禁止裸 `dict`）

**Non-Goals:**
- 不新增业务功能或 API 端点
- 不重构整体架构（如不改写 Runtime 的异步生成器为 callback 模式）
- 不修复前端 TypeScript 类型问题

## Decisions

### 1. `AgentRuntime.initialize` 统一接受 `dict[str, Any] | EngineConfig`
- **原因**：大量调用方（bridge、测试、skill）直接传入 `dict`，强制要求所有调用方先构造 `EngineConfig` 会扩大变更范围。让基类参数类型更宽泛（`dict | EngineConfig`），在实现内部使用 `EngineConfig.model_validate(config)` 兜底，兼容现有调用代码。
- **替代方案**：修改所有调用方传入 `EngineConfig` —— Rejected，因为会引入 10+ 文件的额外变更，增加回归风险。

### 2. `send_message` 保持 `async def -> AsyncIterator` 不变，通过类型适配绕过 mypy override 报错
- **原因**：这是 Python 异步生成器的已知 mypy 限制（[mypy#7858](https://github.com/python/mypy/issues/7858)）。`async def` 返回 `AsyncIterator` 在运行时完全正确，但 mypy 的 override 检查过于严格。我们将对子类方法添加 `# type: ignore[override]`，同时在注释中说明原因。
- **替代方案**：把基类改为非 `async` 的生成器函数 —— Rejected，因为这会破坏 `async` 初始化代码的已有模式。

### 3. `ToolSpec` 统一收敛到 `core.models.tool_models.ToolSpec`
- **原因**：`core.models.tool.ToolSpec` 是旧定义（可能是遗留的 Pydantic 模型或类），而新版 JSON schema 和序列化逻辑在 `core.models.tool_models` 中。`ToolManager` 和 `SimpleAgent` 同时引用两者导致 mypy 报错。删除/废弃旧路径，统一导入到新路径。

### 4. `core/models/types.py` 恢复为重新导出模块（re-export shim）
- **原因**：大量历史代码通过 `from core.models.types import X` 引用类型。在之前的重构中，这些类型被迁移到 `core.models.websocket_models`、`core.models.response_models` 等子模块，但 `types.py` 的 `__all__` 未同步更新，导致 `main.py` 批量导入失败。不恢复这些导出会破坏 backward compatibility。

## Risks / Trade-offs

- **[Risk]** 修改 `ToolManager` 的类型签名可能影响 Skill 注册时的运行时行为（如把 `dict` 传给 `JSONSchema` 参数）
  → **Mitigation**: 在 `register()` 内部继续使用 `JSONSchema.model_validate(parameters)` 或 `JSONSchema(**parameters)` 做兼容处理，确保现有 skill 脚本不经修改仍可注册工具。

- **[Risk]** `EngineConfig` 的字段定义可能在某些调用方传入的 `dict` 中缺少字段
  → **Mitigation**: `EngineConfig` 已配置合理的默认值，使用 `model_validate` 不会报错。

- **[Risk]** 添加 `type: ignore` 会掩盖未来真正的类型问题
  → **Mitigation**: 只在已知 mypy bug/limitation 的位置添加，并附带详细注释说明原因和引用链接。

## Migration Plan

无需迁移步骤。变更仅涉及类型修复，不涉及数据库、配置或部署流程修改。回滚策略为直接 `git revert` 对应提交。
