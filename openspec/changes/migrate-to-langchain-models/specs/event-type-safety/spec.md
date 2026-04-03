## ADDED Requirements

### Requirement: 基于自定义消息类的强类型事件
WebSocket 和内部事件 SHALL 使用自定义消息类作为 payload 类型，确保类型安全。

#### Scenario: Stream Delta 事件
- **WHEN** 发送 `stream:delta` 事件
- **THEN** payload 中的消息数据 SHALL 来自 `CustomAIMessage` 序列化
- **AND** SHALL 可通过反序列化恢复为自定义消息实例

#### Scenario: Dialog Snapshot 事件
- **WHEN** 发送 `dialog:snapshot` 事件
- **THEN** `messages` 数组中的每个元素 SHALL 是自定义消息类的序列化格式
- **AND** 前端 SHALL 能够恢复为对应自定义消息实例

#### Scenario: Message Added 事件
- **WHEN** 广播新消息添加事件
- **THEN** SHALL 使用 `message_to_dict()` 序列化自定义消息
- **AND** 包含完整的业务字段

### Requirement: TypeScript 类型守卫
前端 SHALL 实现类型守卫函数，用于运行时验证自定义消息格式。

#### Scenario: 自定义消息格式验证
- **WHEN** 从 WebSocket 接收消息数据
- **THEN** SHALL 使用类型守卫验证是否为有效的自定义消息格式
- **AND** 无效格式 SHALL 触发错误处理

#### Scenario: 类型收窄
- **GIVEN** 未知的消息对象
- **WHEN** 通过类型守卫检查
- **THEN** TypeScript 编译器 SHALL 能够收窄类型到具体自定义消息类
- **AND** 支持 `instanceof CustomHumanMessage` 检查

### Requirement: 事件 Schema 使用自定义类型
所有事件类型 SHALL 使用自定义消息类定义，而非裸字典。

#### Scenario: WebSocket 事件类型定义
- **GIVEN** 事件系统
- **THEN** SHALL 存在 TypeScript/Python 类型定义所有可能的服务器事件
- **AND** 消息字段类型 SHALL 是自定义消息类

#### Scenario: 类型导出
- **WHEN** 其他模块需要消息类型
- **THEN** SHALL 从自定义消息模块导入
- **AND** SHALL NOT 重复定义事件结构

### Requirement: 自定义消息类属性访问类型安全
前端自定义消息类的属性访问 SHALL 类型安全。

#### Scenario: 访问业务字段
- **GIVEN** `CustomHumanMessage` 实例
- **WHEN** 访问 `msg.msgId`
- **THEN** TypeScript SHALL 识别返回类型为 `string`
- **AND** SHALL NOT 返回 `any` 类型

#### Scenario: 访问 LangChain 字段
- **GIVEN** `CustomAIMessage` 实例
- **WHEN** 访问 `msg.tool_calls`
- **THEN** TypeScript SHALL 识别返回类型
- **AND** SHALL 与 LangChain 类型定义一致
