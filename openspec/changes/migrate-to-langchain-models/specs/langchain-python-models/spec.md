## ADDED Requirements

### Requirement: 自定义消息类继承 LangChain 基础类
后端 SHALL 创建自定义消息类，继承自 `langchain_core.messages` 中的对应基础类（`HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage`）。

#### Scenario: CustomHumanMessage 继承
- **WHEN** 定义用户消息类
- **THEN** `CustomHumanMessage` SHALL 继承 `HumanMessage`
- **AND** SHALL 通过 `additional_kwargs` 添加业务字段

#### Scenario: CustomAIMessage 继承
- **WHEN** 定义助手消息类
- **THEN** `CustomAIMessage` SHALL 继承 `AIMessage`
- **AND** SHALL 支持 `tool_calls` 字段
- **AND** SHALL 通过 `additional_kwargs` 添加业务字段

#### Scenario: CustomToolMessage 继承
- **WHEN** 定义工具消息类
- **THEN** `CustomToolMessage` SHALL 继承 `ToolMessage`
- **AND** SHALL 包含 `tool_call_id` 字段（通过父类）

### Requirement: 业务字段通过 additional_kwargs 存储
自定义消息类的业务字段（id, created_at, metadata 等）SHALL 存储在 `additional_kwargs` 字典中，以确保与 LangChain 序列化兼容。

#### Scenario: 消息 ID 存储
- **GIVEN** 创建 `CustomHumanMessage`
- **WHEN** 指定 `msg_id="msg_abc123"`
- **THEN** id SHALL 存储在 `additional_kwargs["id"]`
- **AND** 序列化后 SHALL 出现在 `data.additional_kwargs.id`

#### Scenario: 时间戳存储
- **GIVEN** 创建自定义消息
- **WHEN** 自动生成时间戳
- **THEN** `created_at` SHALL 存储在 `additional_kwargs["created_at"]`

#### Scenario: 元数据存储
- **GIVEN** 创建带元数据的消息
- **WHEN** 传入 `metadata={"source": "web"}`
- **THEN** metadata SHALL 存储在 `additional_kwargs["metadata"]`

### Requirement: 自定义消息类提供便捷访问属性
自定义消息类 SHALL 提供属性访问器，便于获取业务字段。

#### Scenario: 访问消息 ID
- **GIVEN** `msg = CustomHumanMessage(content="hi", msg_id="abc")`
- **WHEN** 访问 `msg.msg_id`
- **THEN** SHALL 返回 "abc"

#### Scenario: 访问创建时间
- **GIVEN** 已创建的消息实例
- **WHEN** 访问 `msg.created_at`
- **THEN** SHALL 返回 ISO 格式时间字符串

### Requirement: 移除裸字典消息处理
后端 SHALL NOT 在核心业务逻辑中使用裸字典表示消息。所有消息 SHALL 是 `BaseMessage` 子类实例（自定义类）。

#### Scenario: Dialog 消息列表类型
- **WHEN** `Dialog.messages` 存储消息
- **THEN** 类型 SHALL 是 `List[BaseMessage]`
- **AND** 实际实例 SHALL 是自定义消息类

#### Scenario: WebSocket 消息构造
- **WHEN** 构造消息事件
- **THEN** SHALL 从自定义消息实例序列化
- **AND** SHALL NOT 直接构造裸字典
