# agent-task-queue Specification

## Purpose
TBD - created by archiving change async-queue-integrations. Update Purpose after archive.
## Requirements
### Requirement: Agent 任务队列管理
系统 SHALL 提供 AgentTaskQueue 类，管理待执行的 Agent 任务，支持优先级和并发控制。

#### Scenario: 提交 Agent 任务
- **GIVEN** AgentTaskQueue 实例
- **WHEN** 调用者提交 AgentTask
- **THEN** 任务进入队列等待执行

#### Scenario: 并发数限制
- **GIVEN** AgentTaskQueue(max_concurrent=3) 且已有 3 个任务在执行
- **WHEN** 新任务提交到队列
- **THEN** 新任务等待，直到有执行槽位释放

#### Scenario: 任务执行完成通知
- **GIVEN** 已提交的任务
- **WHEN** 任务执行完成
- **THEN** 调用者收到完成通知（Future 或回调）

### Requirement: 任务优先级支持
系统 SHALL 支持任务优先级，高优先级任务优先执行。

#### Scenario: 高优先级任务插队
- **GIVEN** 队列中有 5 个普通优先级任务
- **WHEN** 提交高优先级任务
- **THEN** 高优先级任务优先于普通任务执行

#### Scenario: 同优先级 FIFO
- **GIVEN** 多个同优先级任务
- **WHEN** 任务依次提交
- **THEN** 按 FIFO 顺序执行

### Requirement: 队列状态查询
系统 SHALL 提供队列状态查询方法。

#### Scenario: 查询队列状态
- **WHEN** 调用 queue.get_stats()
- **THEN** 返回等待中、执行中、已完成任务数

