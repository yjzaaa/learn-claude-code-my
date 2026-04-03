## Why

当前项目仅支持 SimpleAgent（无框架）实现，缺乏高级 Agent 能力（任务规划、子代理、持久化记忆）。需要引入 deep-agents 框架，同时保持现有前后端接口不变，实现无框架版本与框架版本使用**同一套门面接口**。

## What Changes

1. **新增 AgentRuntime 统一门面** - 为上层提供与实现无关的 Agent 执行接口
2. **新增 DeepAgentAdapter** - 适配 deep-agents 框架到 AgentInterface
3. **改造 SimpleAgent 为 SimpleAdapter** - 统一实现 AgentInterface
4. **新增 AgentFactory** - 根据配置创建对应 Agent 实现（simple/deep）
5. **更新 AgentBridge** - 改为通过 AgentRuntime 调用，而非直接调用 AgentEngine
6. **保留所有现有 API/WebSocket 接口** - 前端无需任何修改

## Capabilities

### New Capabilities
- `agent-runtime-facade`: Agent 运行时统一门面，抽象 Agent 执行能力
- `deep-agent-adapter`: Deep-Agents 框架适配器，包装 create_deep_agent()
- `simple-agent-adapter`: 无框架 Agent 适配器（现有 SimpleAgent 改造）
- `agent-factory`: Agent 创建工厂，支持运行时切换实现

### Modified Capabilities
- 无现有 spec 需要修改（当前项目无 openspec/specs/ 目录）

## Impact

- **core/agent/**: 新增 adapters/ 目录，改造现有 simple/ 目录
- **interfaces/agent_bridge.py**: 改为使用 AgentRuntime 而非直接调用 AgentEngine
- **依赖**: 新增 `deepagents` SDK 依赖
- **配置**: 新增 `AGENT_TYPE=simple|deep` 环境变量
- **API**: 无变化，所有现有接口保持不变
