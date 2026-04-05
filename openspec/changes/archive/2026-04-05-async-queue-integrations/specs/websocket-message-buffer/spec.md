## ADDED Requirements

### Requirement: WebSocket 消息缓冲
系统 SHALL 提供 WebSocketMessageBuffer 类，为每个 WebSocket 连接提供独立的消息缓冲。

#### Scenario: 缓冲待发送消息
- **GIVEN** WebSocketMessageBuffer 实例
- **WHEN** 调用 send_buffered(message)
- **THEN** 消息进入队列，异步发送

#### Scenario: 网络波动时的消息保持
- **GIVEN** WebSocket 连接暂时不可用
- **WHEN** 有新消息需要发送
- **THEN** 消息在缓冲中等待，连接恢复后继续发送

### Requirement: 满队列策略选择
系统 SHALL 支持多种队列满时的处理策略。

#### Scenario: 阻塞等待策略
- **GIVEN** 配置为 block_on_full=True
- **WHEN** 队列满时调用 send_buffered
- **THEN** 调用阻塞直到有空间

#### Scenario: 丢弃策略
- **GIVEN** 配置为 drop_on_full=True
- **WHEN** 队列满时调用 send_buffered
- **THEN** 返回 False，消息被丢弃

#### Scenario: 超时策略
- **GIVEN** 配置 timeout=5.0
- **WHEN** 队列满时调用 send_buffered
- **THEN** 等待最多 5 秒，超时返回 False

### Requirement: 按客户端隔离缓冲
系统 SHALL 为每个 WebSocket 客户端提供独立的缓冲队列。

#### Scenario: 多客户端隔离
- **GIVEN** 客户端 A 和客户端 B 同时连接
- **WHEN** 向客户端 A 发送大量消息
- **THEN** 客户端 B 不受影响，正常收发消息
