# 提取 Runtime 抽象基类

## 问题陈述

`SimpleRuntime` (689 行) 和 `DeepRuntime` (670 行) 都实现了 `AgentRuntime` 接口，但存在大量重复代码：

1. **相同属性**: `_agent_id`, `_config`, `_tools`, `_dialogs`
2. **相同属性实现**: `runtime_id`, `agent_type`
3. **相同接口**: `initialize`, `shutdown`, `send_message`, `create_dialog`, `get_dialog`, `list_dialogs`, `stop`, `register_tool`, `unregister_tool`
4. **重复工具缓存模型**: 两个文件都定义了相同的 `ToolCache` 类

当前 `AgentRuntime` 抽象类仅定义接口，没有提供任何可复用的实现。

## 目标

创建一个类型安全的抽象基类 `AbstractAgentRuntime[ConfigT]`，使用模板方法模式提供：

1. **通用属性管理**: 使用泛型类型处理不同配置类型
2. **默认实现**: 对话管理、工具管理、生命周期管理的通用实现
3. **抽象钩子**: 子类只需实现特定行为
4. **代码复用**: 消除两个 Runtime 之间的重复代码

## 预期收益

| 指标 | 当前 | 目标 |
|------|------|------|
| SimpleRuntime 行数 | 689 | ~400 (-40%) |
| DeepRuntime 行数 | 670 | ~350 (-45%) |
| ToolCache 重复定义 | 2 次 | 1 次 |
| 新增抽象基类 | 0 | 1 个 (~200 行) |

## 影响范围

- **新增**: `core/agent/runtimes/base.py` - 抽象基类
- **修改**: `core/agent/runtimes/simple_runtime.py` - 继承基类
- **修改**: `core/agent/runtimes/deep_runtime.py` - 继承基类
- **无影响**: 外部接口 `AgentRuntime` 保持不变

## 兼容性

- 保持 `AgentRuntime` 接口不变
- 现有工厂创建代码无需修改
- `AgentRuntimeBridge` 和其他使用者不受影响
