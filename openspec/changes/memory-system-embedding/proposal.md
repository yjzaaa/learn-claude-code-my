## Why

当前 Agent Runtime 缺乏跨会话的上下文持久化机制。用户需要重复提供偏好、项目背景和反馈指导，导致交互效率低下。借鉴 free-code 的记忆系统设计，我们需要一个能够自动提取、持久化和检索对话上下文的记忆系统，使 Agent 能够在多次会话中保持对用户和项目的理解。

## What Changes

- **新增记忆存储架构**: 基于文件系统的四层记忆类型存储（user/feedback/project/reference），采用 Markdown + Frontmatter 格式
- **新增 MemoryMixin**: 集成到 DeepAgentRuntime，提供记忆初始化、保存、检索和自动提取功能
- **新增记忆提取服务**: 在对话结束时自动分析并提取有价值的记忆
- **新增记忆检索服务**: 基于查询智能选择最相关的记忆（最多5个）
- **新增 HTTP 接口**: `/memory` 命令用于手动管理记忆
- **新增事件集成**: MemoryCreatedEvent / MemoryExtractedEvent / MemoryRetrievedEvent
- **修改 DeepAgentRuntime**: 在查询前后自动加载和提取记忆

## Capabilities

### New Capabilities
- `memory-storage`: 四层记忆类型存储系统，支持 user/feedback/project/reference 类型的记忆持久化
- `memory-retrieval`: 智能记忆检索，基于查询选择最相关的记忆（最多5个）
- `memory-extraction`: 自动从对话历史中提取和保存有价值的记忆
- `memory-aging`: 记忆老化管理，追踪记忆新鲜度并提供过期警告

### Modified Capabilities
- `deep-agent-runtime`: 集成 MemoryMixin，在查询生命周期中自动加载和提取记忆

## Impact

- **代码库**: Domain 层新增 memory 模型，Application 层新增 memory 服务，Infrastructure 层新增 MemoryMixin 和文件系统仓库
- **API**: 新增 `/memory` HTTP 端点，支持创建、列出、搜索记忆
- **存储**: 在项目目录下创建 `.claude/memory/` 目录存储记忆文件
- **事件流**: 新增记忆相关事件，通过 EventBus 解耦
- **Runtime**: DeepAgentRuntime 初始化时自动加载 MemoryMixin
- **依赖**: 新增可选依赖（未来扩展向量嵌入时使用）
