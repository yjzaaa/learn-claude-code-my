## ADDED Requirements

### Requirement: InputArea 组件必须拆分
系统 SHALL 将 `web/src/components/chat/InputArea.tsx` (776 行) 拆分为专注的子组件。

#### Scenario: ModelSelector 组件分离
- **WHEN** 检查 `web/src/components/chat/ModelSelector.tsx`
- **THEN** 它 SHALL 只包含模型下拉选择和切换逻辑
- **AND** 代码行数 SHALL 小于 150 行
- **AND** 它 SHALL 通过 props 接收 `models`, `selectedModel`, `onModelChange`

#### Scenario: SlashCommandMenu 组件分离
- **WHEN** 检查 `web/src/components/chat/SlashCommandMenu.tsx`
- **THEN** 它 SHALL 只包含斜杠命令建议和下拉菜单
- **AND** 代码行数 SHALL 小于 100 行
- **AND** 它 SHALL 通过 props 接收 `commands`, `filter`, `onSelect`

#### Scenario: FileAttachment 组件分离
- **WHEN** 检查 `web/src/components/chat/FileAttachment.tsx`
- **THEN** 它 SHALL 只包含文件上传和预览逻辑
- **AND** 代码行数 SHALL 小于 100 行

#### Scenario: InputArea 精简
- **WHEN** 检查重构后的 `web/src/components/chat/InputArea.tsx`
- **THEN** 它 SHALL 只包含核心输入和提交逻辑
- **AND** 代码行数 SHALL 小于 250 行
- **AND** 它 SHALL 使用拆分出的子组件

### Requirement: Agent store 必须拆分为领域特定 store
系统 SHALL 将 `web/src/agent/agent-store.ts` (256 行) 拆分为专注的 store。

#### Scenario: Dialog store 分离
- **WHEN** 检查 `web/src/stores/dialog-store.ts`
- **THEN** 它 SHALL 只包含对话列表和当前对话状态
- **AND** 代码行数 SHALL 小于 150 行

#### Scenario: Message store 分离
- **WHEN** 检查 `web/src/stores/message-store.ts`
- **THEN** 它 SHALL 只包含消息列表和流式消息状态
- **AND** 代码行数 SHALL 小于 150 行

#### Scenario: Status store 分离
- **WHEN** 检查 `web/src/stores/status-store.ts`
- **THEN** 它 SHALL 只包含连接状态和加载状态
- **AND** 代码行数 SHALL 小于 100 行

### Requirement: WebSocket hooks 必须抽象
系统 SHALL 创建可复用的 WebSocket hooks。

#### Scenario: useWebSocket hook 抽象
- **WHEN** 检查 `web/src/hooks/useWebSocket.ts`
- **THEN** 它 SHALL 提供通用的 WebSocket 连接管理
- **AND** 它 SHALL 与具体业务逻辑解耦

#### Scenario: useAgentEvents hook 创建
- **WHEN** 检查 `web/src/hooks/useAgentEvents.ts`
- **THEN** 它 SHALL 封装 Agent 特定的事件处理
- **AND** 它 SHALL 使用 useWebSocket 作为基础
