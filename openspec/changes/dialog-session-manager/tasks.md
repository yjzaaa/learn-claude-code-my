# Dialog Session Manager 实施任务

## Phase A: 基础模块创建（不接入现有代码）

### Task 1: 创建数据模型和异常
**ID**: `T1` | **Status**: 🔵 Pending | **Owner**: -

创建 `core/session/models.py` 和 `core/session/exceptions.py`：
- [x] `SessionStatus` 枚举（生命周期状态）
- [x] `SessionMetadata` 数据类（会话元数据）
- [x] `StreamingContext` 数据类（流式上下文）
- [x] `DialogSession` 数据类（主状态容器）
- [x] 自定义异常：`SessionNotFoundError`, `InvalidTransitionError`, `SessionFullError`

**Files to create**:
- `core/session/__init__.py`
- `core/session/models.py`
- `core/session/exceptions.py`

---

### Task 2: 实现消息存储
**ID**: `T2` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T1

创建 `core/session/storage.py`：
- [x] `MessageStorage` 类实现 `IMessageStorage` 接口（使用 LangChain InMemoryChatMessageHistory）
- [x] 消息追加和索引管理
- [x] `get_messages_for_llm()` 方法（token 估算和截断）
- [x] 轮次边界追踪

**Files to create**:
- `core/session/storage.py`

---

### Task 3: 实现生命周期状态机
**ID**: `T3` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T1

创建 `core/session/lifecycle.py`：
- [x] 状态转换规则验证（在 manager.py 中实现）
- [x] `transition()` 方法实现
- [x] 有效的转换矩阵
- [x] 转换事件通知

**Files to create**:
- `core/session/lifecycle.py`

---

### Task 4: 实现钩子机制
**ID**: `T4` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T1

创建 `core/session/hooks.py`：
- [~] `HookRegistry` 类（跳过）
- [~] 钩子优先级排序（跳过）
- [~] 安全执行（异常捕获）（跳过）
- [~] 预定义钩子（跳过）

**Files to create**:
- `core/session/hooks.py`

---

### Task 5: 实现清理任务
**ID**: `T5` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T1

创建 `core/session/cleanup.py`：
- [x] 过期会话检测（基于 `last_activity_at`，在 manager.py 中实现）
- [x] LRU 清理策略（当会话数超限）
- [x] 定时任务调度

**Files to create**:
- `core/session/cleanup.py`

---

### Task 6: 实现主管理器类
**ID**: `T6` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T2, T3, T4, T5

创建 `core/session/manager.py`：
- [x] `DialogSessionManager` 主类
- [x] 会话生命周期方法（create/get/close）
- [x] 消息操作方法（add_user/start_ai/complete_ai/add_tool）
- [x] 并发控制（每个会话独立锁）
- [~] 集成钩子调用（跳过）（可选，Phase B 实现）

**Files to create**:
- `core/session/manager.py`

---

### Task 7: 单元测试 - 模型和存储
**ID**: `T7` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T6

编写测试：
- [ ] `tests/session/test_models.py` - 数据模型测试
- [ ] `tests/session/test_storage.py` - 消息存储测试
- [ ] `tests/session/test_lifecycle.py` - 状态机转换测试

---

### Task 8: 单元测试 - 管理器
**ID**: `T8` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T6

编写测试：
- [ ] `tests/session/test_manager.py` - 完整管理器测试
- [ ] 并发操作测试
- [ ] 钩子执行测试
- [ ] 清理任务测试

---

## Phase B: SimpleAgentRuntime 试点

### Task 9: 修改 SimpleAgentRuntime 使用 SessionManager
**ID**: `T9` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T6, T8

修改 `core/agent/runtimes/simple_runtime.py`：
- [x] 添加 `session_manager` 参数
- [x] 替换直接操作 `Dialog.messages` 的代码
- [x] 确保所有消息操作通过 SessionManager

---

### Task 10: 更新 Runtime 基类接口
**ID**: `T10` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T9

修改 `core/agent/runtimes/base.py`：
- [x] 更新 `AbstractAgentRuntime` 接口定义
- [x] 添加 `session_manager` 抽象属性

---

### Task 11: 集成测试 - SimpleAgentRuntime
**ID**: `T11` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T9

编写测试：
- [x] `tests/session/test_session_manager.py`
- [x] 验证消息正确存储
- [x] 验证生命周期状态正确转换

---

## Phase C: DeepAgentRuntime 迁移

### Task 12: 修改 DeepAgentRuntime 使用 SessionManager
**ID**: `T12` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T10

修改 `core/agent/runtimes/deep_runtime.py`：
- [x] 移除 `self._dialogs` 直接存储
- [ ] 移除直接操作 `Dialog.messages` 的代码
- [ ] 通过 SessionManager 进行所有消息操作
- [ ] 流式过程中不存储 delta，只透传事件

---

### Task 13: 集成测试 - DeepAgentRuntime
**ID**: `T13` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T12

编写测试：
- [ ] `tests/session/test_deep_runtime_integration.py`
- [ ] 验证流式消息最终正确存储
- [ ] 验证工具消息正确存储
- [ ] 验证状态转换正确

---

## Phase D: EventCoordinator 集成和清理

### Task 14: 创建/更新 EventCoordinator
**ID**: `T14` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T6

修改 `core/agent/event_coordinator.py`（如存在，否则创建）：
- [x] 集成 SessionManager
- [x] 接收 Runtime 的 AgentEvent
- [x] 调用 SessionManager 更新状态
- [x] 生成并广播 snapshot

---

### Task 15: 更新 main.py 集成
**ID**: `T15` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T14

修改 `main.py`：
- [x] 创建全局 `DialogSessionManager` 实例
- [x] 传递给 Runtime 和 EventCoordinator
- [x] 移除 `_status`、`_streaming_msg` 等并行状态

---

### Task 16: 端到端测试
**ID**: `T16` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T15

编写测试：
- [x] `tests/session/test_e2e.py` - 完整流程测试
- [ ] 多会话并发测试
- [ ] 长时间运行稳定性测试

---

### Task 17: 移除旧代码和 shim 层
**ID**: `T17` | **Status**: 🔵 Pending | **Owner**: - | **Depends**: T16

清理代码：
- [ ] 移除 Runtime 中的 `_dialogs` 存储
- [x] 移除 `main.py` 中的冗余状态
- [ ] 移除废弃的 hook/shim
- [x] 更新 CLAUDE.md 文档

---

## 附录：任务依赖图

```
T1 ───┬─── T2 ───┬─── T6 ───┬─── T8 ───┬─── T9 ───┬─── T10 ───┬─── T12 ───┬─── T14 ───┬─── T15 ───┬─── T16 ─── T17
      │          │          │          │                    │           │           │
      └─── T3 ───┘          └─── T7 ───┘                    │           │           │
                                                            └─── T11 ───┘           │
                                                                                    │
                                                            T4 ───┬─────────────────┘
                                                                  │
                                                            T5 ───┘
```
