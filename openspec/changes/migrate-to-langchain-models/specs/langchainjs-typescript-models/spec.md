## ADDED Requirements

### Requirement: 前端自定义消息类继承 LangChain.js 基础类
前端 SHALL 创建自定义消息类，继承自 `@langchain/core` 中的对应基础类（`HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage`）。

#### Scenario: CustomHumanMessage TypeScript 继承
- **WHEN** 定义用户消息类
- **THEN** `CustomHumanMessage` SHALL 继承 `@langchain/core/messages.HumanMessage`
- **AND** SHALL 通过 `additional_kwargs` 添加业务字段

#### Scenario: CustomAIMessage TypeScript 继承
- **WHEN** 定义助手消息类
- **THEN** `CustomAIMessage` SHALL 继承 `@langchain/core/messages.AIMessage`
- **AND** SHALL 支持工具调用字段

#### Scenario: CustomToolMessage TypeScript 继承
- **WHEN** 定义工具消息类
- **THEN** `CustomToolMessage` SHALL 继承 `@langchain/core/messages.ToolMessage`

### Requirement: 前端业务字段通过 additional_kwargs 存储
前端自定义消息类的业务字段（id, createdAt, metadata 等）SHALL 存储在 `additional_kwargs` 对象中。

#### Scenario: 前端消息 ID 存储
- **GIVEN** 创建 `new CustomHumanMessage("hi", { msgId: "abc" })`
- **THEN** id SHALL 存储在 `additional_kwargs.id`
- **AND** 可通过 `msg.msgId` getter 访问

#### Scenario: 前端时间戳存储
- **GIVEN** 创建自定义消息
- **THEN** createdAt SHALL 存储在 `additional_kwargs.created_at`

### Requirement: 前端类型定义使用自定义消息类
前端所有消息类型定义 SHALL 使用自定义消息类，而非裸对象或 interface。

#### Scenario: WebSocket 消息类型
- **WHEN** 定义 `SendMessageRequest`
- **THEN** `content` 类型 SHALL 是 `BaseMessage` 或子类
- **AND** SHALL NOT 使用 `string` 或裸对象

#### Scenario: 状态管理类型
- **WHEN** 定义消息列表状态
- **THEN** 类型 SHALL 是 `BaseMessage[]`
- **AND** 实际存储 SHALL 是自定义消息实例

### Requirement: 移除前端裸对象消息处理
前端 SHALL NOT 在核心业务逻辑中使用裸对象表示消息。所有消息 SHALL 是自定义消息类实例。

#### Scenario: 消息发送
- **WHEN** 用户发送消息
- **THEN** SHALL 创建 `CustomHumanMessage` 实例
- **AND** SHALL NOT 使用 `{role: "user", content: "..."}` 裸对象

#### Scenario: 流式消息处理
- **WHEN** 处理流式响应
- **THEN** SHALL 逐步构建 `CustomAIMessage` 实例
- **AND** 增量 SHALL 添加到实例内容中
