## ADDED Requirements

### Requirement: 统一的消息序列化层
系统 SHALL 实现统一的序列化层，使用 LangChain 标准方法 `message_to_dict()` 和 `messages_from_dict()`。

#### Scenario: 自定义消息序列化
- **GIVEN** `CustomHumanMessage(content="Hello", msg_id="abc")`
- **WHEN** 调用 `message_to_dict(msg)`
- **THEN** 结果 SHALL 包含 `type`, `data` 字段
- **AND** `data.additional_kwargs.id` SHALL 等于 "abc"

#### Scenario: 自定义消息反序列化
- **GIVEN** LangChain 标准格式 JSON
- **WHEN** 调用 `messages_from_dict([json])`
- **THEN** 返回 SHALL 是 `BaseMessage` 子类实例
- **AND** 业务字段 SHALL 在 `additional_kwargs` 中

#### Scenario: 批量序列化
- **GIVEN** 消息列表 `[msg1, msg2, ...]`
- **WHEN** 调用 `message_to_dict()` 每个消息
- **THEN** SHALL 返回标准格式列表

### Requirement: 自定义类序列化识别
序列化层 SHALL 正确识别和序列化自定义消息类，保留业务字段。

#### Scenario: CustomHumanMessage 识别
- **GIVEN** `CustomHumanMessage` 实例
- **WHEN** 序列化
- **THEN** `type` SHALL 为 "human"
- **AND** 业务字段 SHALL 在 `data.additional_kwargs` 中

#### Scenario: CustomAIMessage 工具调用序列化
- **GIVEN** `CustomAIMessage` 带 `tool_calls`
- **WHEN** 序列化
- **THEN** `data.tool_calls` SHALL 存在
- **AND** 业务字段 SHALL 在 `additional_kwargs` 中

### Requirement: 消除裸 JSON 格式
系统 SHALL 移除所有裸 JSON/dict 格式的消息传递，统一使用 LangChain 标准格式。

#### Scenario: WebSocket 事件格式
- **GIVEN** 消息需要发送到前端
- **THEN** SHALL 序列化为 LangChain 标准格式
- **AND** SHALL NOT 包含自定义裸字典字段

#### Scenario: API 响应格式
- **GIVEN** `/api/dialogs/{id}/messages` 响应
- **THEN** 返回的消息列表 SHALL 是 LangChain 格式
- **AND** 业务字段 SHALL 在 `additional_kwargs` 中

### Requirement: 向后兼容适配
系统 SHALL 提供适配层，支持读取旧格式并转换为新格式。

#### Scenario: 旧格式检测
- **GIVEN** 旧格式消息 `{"role": "user", "content": "..."}`
- **WHEN** 检测格式
- **THEN** SHALL 识别为旧格式

#### Scenario: 旧格式转换
- **GIVEN** 旧格式消息
- **WHEN** 转换
- **THEN** SHALL 转换为 LangChain 标准格式
- **AND** 业务字段 SHALL 正确映射
