## 1. 代码去重 - Logger 统一 (Code Deduplication - Logger)

### 1.1 创建 Logger 基础组件
- [ ] 1.1.1 创建 `backend/infrastructure/logging/factory.py`，实现 LoggerFactory 类
- [ ] 1.1.2 创建 `backend/infrastructure/logging/mixins.py`，实现 LoggerMixin 类
- [ ] 1.1.3 更新 `backend/infrastructure/logging/__init__.py`，导出 `get_logger` 函数和 LoggerMixin
- [ ] 1.1.4 验证 LoggerFactory 配置一致性（formatter、level、handler）

### 1.2 批量替换 Logger 定义 (22个文件)
- [ ] 1.2.1 更新 `backend/infrastructure/runtime/deep.py`
- [ ] 1.2.2 更新 `backend/infrastructure/runtime/manager.py`
- [ ] 1.2.3 更新 `backend/infrastructure/runtime/simple.py`
- [ ] 1.2.4 更新 `backend/infrastructure/services/provider_manager.py`
- [ ] 1.2.5 更新 `backend/infrastructure/services/dialog_manager.py`
- [ ] 1.2.6 更新 `backend/infrastructure/services/memory_manager.py`
- [ ] 1.2.7 更新 `backend/infrastructure/services/model_discovery.py`
- [ ] 1.2.8 更新 `backend/infrastructure/services/skill_manager.py`
- [ ] 1.2.9 更新 `backend/infrastructure/services/state_manager.py`
- [ ] 1.2.10 更新 `backend/infrastructure/services/tool_manager.py`
- [ ] 1.2.11 更新 `backend/infrastructure/event_bus/handlers.py`
- [ ] 1.2.12 更新 `backend/infrastructure/event_bus/queued_event_bus.py`
- [ ] 1.2.13 更新 `backend/infrastructure/agent_queue/task_queue.py`
- [ ] 1.2.14 更新 `backend/infrastructure/llm_adapter/streaming.py`
- [ ] 1.2.15 更新 `backend/infrastructure/websocket_buffer/buffer.py`
- [ ] 1.2.16 更新 `backend/infrastructure/runtime/middleware/claude_compression.py`
- [ ] 1.2.17 更新 `backend/infrastructure/runtime/event_bus.py`
- [ ] 1.2.18 更新 `backend/interfaces/http/routes/dialogs.py`
- [ ] 1.2.19 更新 `backend/interfaces/http/routes/messages.py`
- [ ] 1.2.20 更新 `backend/interfaces/websocket/broadcast.py`
- [ ] 1.2.21 更新 `backend/interfaces/websocket/server.py`
- [ ] 1.2.22 更新 `backend/interfaces/websocket/handler.py`
- [ ] 1.2.23 更新 `backend/application/engine.py`

### 1.3 验证和测试
- [ ] 1.3.1 全局搜索确保没有遗留的 `logging.getLogger(__name__)` 定义
- [ ] 1.3.2 运行测试确保日志输出格式一致
- [ ] 1.3.3 验证日志级别配置生效

## 2. 代码去重 - 工具函数统一 (Code Deduplication - Utils)

### 2.1 创建 TimeUtils 工具类
- [ ] 2.1.1 创建 `backend/domain/utils/__init__.py`
- [ ] 2.1.2 创建 `backend/domain/utils/time_utils.py`，实现 TimeUtils 类
- [ ] 2.1.3 导出 `timestamp_ms`, `iso_timestamp` 便捷函数

### 2.2 迁移时间函数使用
- [ ] 2.2.1 更新 `backend/domain/services/dialog_service.py`，移除本地定义，使用工具函数
- [ ] 2.2.2 更新 `backend/infrastructure/event_bus/handlers.py` 中的多处使用
- [ ] 2.2.3 更新 `backend/interfaces/websocket/handler.py`
- [ ] 2.2.4 更新 `backend/interfaces/http/routes/agent.py`
- [ ] 2.2.5 更新 `backend/interfaces/http/routes/messages.py`
- [ ] 2.2.6 验证所有时间戳调用统一

### 2.3 创建 SnapshotBuilder
- [ ] 2.3.1 创建 `backend/domain/utils/snapshot_builder.py`，实现 SnapshotBuilder 类
- [ ] 2.3.2 合并 `manager.py` 和 `dialog_service.py` 的构建逻辑
- [ ] 2.3.3 提供向后兼容的 `build_dialog_snapshot()` 函数
- [ ] 2.3.4 更新 `backend/domain/models/dialog/manager.py`，使用 SnapshotBuilder
- [ ] 2.3.5 更新 `backend/domain/services/dialog_service.py`，使用 SnapshotBuilder

## 3. 代码去重 - Mixin 优化 (Code Deduplication - Mixins)

### 3.1 创建基础 Mixin 类
- [ ] 3.1.1 创建 `backend/domain/models/shared/base_mixins.py`
- [ ] 3.1.2 实现 `ComparableMixin`，提供 `__eq__` 和 `__hash__`
- [ ] 3.1.3 实现 `SerializableMixin`，提供 `to_dict()` 和 `from_dict()`
- [ ] 3.1.4 实现 `ValidatableMixin`，提供 `validate()` 框架

### 3.2 优化现有 Mixin
- [ ] 3.2.1 检查 `backend/domain/models/shared/mixins.py` 中的 Mixin
- [ ] 3.2.2 检查 `backend/infrastructure/runtime/mixins.py` 中的 Mixin
- [ ] 3.2.3 识别可以继承基础 Mixin 的类
- [ ] 3.2.4 在合适的类中使用 `LoggerMixin` 替代外部 logger 定义

## 4. 代码去重 - 异常层次统一 (Code Deduplication - Exceptions)

### 4.1 创建异常目录结构
- [ ] 4.1.1 创建 `backend/domain/exceptions/__init__.py`
- [ ] 4.1.2 创建 `backend/domain/exceptions/base.py`，定义 `DomainError` 基础类
- [ ] 4.1.3 创建 `backend/domain/exceptions/dialog.py`

### 4.2 定义基础异常类
- [ ] 4.2.1 实现 `DomainError`，包含 `code`, `message`, `details` 属性
- [ ] 4.2.2 实现 `NotFoundError` 继承 `DomainError`
- [ ] 4.2.3 实现 `AlreadyExistsError` 继承 `DomainError`
- [ ] 4.2.4 实现 `StateError` 继承 `DomainError`
- [ ] 4.2.5 实现 `ValidationError` 继承 `DomainError`
- [ ] 4.2.6 实现 `LimitExceededError` 继承 `DomainError`

### 4.3 重构具体异常
- [ ] 4.3.1 重构 `SessionNotFoundError` 继承 `NotFoundError`
- [ ] 4.3.2 重构 `SessionAlreadyExistsError` 继承 `AlreadyExistsError`
- [ ] 4.3.3 重构 `InvalidTransitionError` 继承 `StateError`
- [ ] 4.3.4 重构 `SessionFullError` 继承 `LimitExceededError`
- [ ] 4.3.5 重构 `SkillNotFoundError` 继承 `NotFoundError`
- [ ] 4.3.6 重构 `DialogNotFoundError` 继承 `NotFoundError`
- [ ] 4.3.7 保持所有异常向后兼容（导入路径、构造函数）

## 5. ProviderManager 拆分

### 5.1 创建 Provider 子模块
- [ ] 5.1.1 创建 `backend/infrastructure/services/provider/__init__.py`
- [ ] 5.1.2 创建 `backend/infrastructure/services/provider/discovery.py`，提取模型发现逻辑（< 200行）
- [ ] 5.1.3 创建 `backend/infrastructure/services/provider/connectivity.py`，提取连通性测试逻辑（< 250行）
- [ ] 5.1.4 创建 `backend/infrastructure/services/provider/factory.py`，提取模型实例创建逻辑（< 200行）
- [ ] 5.1.5 创建 `backend/infrastructure/services/provider/manager.py`，作为 facade（< 150行）

### 5.2 迁移和兼容性
- [ ] 5.2.1 从 `provider_manager.py` 迁移代码到新模块
- [ ] 5.2.2 更新 `provider_manager.py` 为向后兼容的导入文件
- [ ] 5.2.3 更新所有使用 ProviderManager 的导入语句
- [ ] 5.2.4 验证现有 API 完全向后兼容

### 5.3 测试
- [ ] 5.3.1 测试模型发现功能
- [ ] 5.3.2 测试连通性测试功能
- [ ] 5.3.3 测试模型实例创建功能
- [ ] 5.3.4 运行完整测试套件

## 6. Dialog Manager 拆分

### 6.1 创建 Dialog 子模块
- [ ] 6.1.1 创建 `backend/domain/models/dialog/session_lifecycle.py`，提取会话生命周期（< 250行）
- [ ] 6.1.2 创建 `backend/domain/models/dialog/message_ops.py`，提取消息操作（< 200行）
- [ ] 6.1.3 创建 `backend/domain/models/dialog/event_emitter.py`，提取事件发射（< 150行）
- [ ] 6.1.4 创建 `backend/domain/models/dialog/snapshot.py`，提取快照构建（< 150行）

### 6.2 重构 Manager
- [ ] 6.2.1 重构 `backend/domain/models/dialog/manager.py` 使用新模块（< 200行）
- [ ] 6.2.2 更新 `backend/domain/models/dialog/__init__.py` 导出所有新模块
- [ ] 6.2.3 确保 DialogSessionManager API 向后兼容

### 6.3 测试
- [ ] 6.3.1 测试会话生命周期管理
- [ ] 6.3.2 测试消息操作
- [ ] 6.3.3 测试事件发射
- [ ] 6.3.4 测试快照构建
- [ ] 6.3.5 运行完整测试套件

## 7. Deep Runtime 模块化

### 7.1 创建 Deep 子包
- [ ] 7.1.1 创建 `backend/infrastructure/runtime/deep/__init__.py`
- [ ] 7.1.2 创建 `backend/infrastructure/runtime/deep/types.py`，定义共享类型（< 100行）
- [ ] 7.1.3 创建 `backend/infrastructure/runtime/deep/agent.py`，agent 生命周期（< 250行）
- [ ] 7.1.4 创建 `backend/infrastructure/runtime/deep/events.py`，事件流处理（< 250行）
- [ ] 7.1.5 创建 `backend/infrastructure/runtime/deep/model.py`，模型切换逻辑（< 250行）
- [ ] 7.1.6 创建 `backend/infrastructure/runtime/deep/checkpoint.py`，checkpoint 管理（< 200行）
- [ ] 7.1.7 创建 `backend/infrastructure/runtime/deep/facade.py`，统一入口（< 150行）

### 7.2 迁移代码
- [ ] 7.2.1 从 `deep.py` 迁移代码到新子包
- [ ] 7.2.2 更新 `deep.py` 为向后兼容的导入文件
- [ ] 7.2.3 更新所有内部导入引用

### 7.3 验证
- [ ] 7.3.1 验证每个新文件行数符合要求
- [ ] 7.3.2 验证所有现有导入继续工作
- [ ] 7.3.3 运行完整测试套件

## 8. 前端组件拆分

### 8.1 创建 Input 子组件
- [ ] 8.1.1 创建 `web/src/components/chat/input/ModelSelector.tsx`（< 150行）
- [ ] 8.1.2 创建 `web/src/components/chat/input/SlashCommandMenu.tsx`（< 100行）
- [ ] 8.1.3 创建 `web/src/components/chat/input/FileAttachment.tsx`（< 100行）
- [ ] 8.1.4 创建 `web/src/components/chat/input/types.ts`，定义共享类型
- [ ] 8.1.5 创建 `web/src/components/chat/input/index.ts`，统一导出

### 8.2 重构 InputArea
- [ ] 8.2.1 重构 `web/src/components/chat/InputArea.tsx` 使用子组件（< 250行）
- [ ] 8.2.2 更新 `web/src/components/chat/index.ts` 导出所有组件
- [ ] 8.2.3 验证所有 props 类型安全

### 8.3 测试
- [ ] 8.3.1 运行 TypeScript 类型检查
- [ ] 8.3.2 运行前端构建
- [ ] 8.3.3 手动测试组件功能

## 9. Agent Store 拆分

### 9.1 拆分 Store
- [ ] 9.1.1 重构 `web/src/stores/dialog-store.ts`（< 150行）
- [ ] 9.1.2 重构 `web/src/stores/message-store.ts`（< 150行）
- [ ] 9.1.3 创建 `web/src/stores/status-store.ts`（< 100行）
- [ ] 9.1.4 更新 `web/src/agent/agent-store.ts` 作为组合入口

### 9.2 更新使用方
- [ ] 9.2.1 更新 `web/src/components/chat/ChatArea.tsx`
- [ ] 9.2.2 更新 `web/src/components/chat/ChatShell.tsx`
- [ ] 9.2.3 更新其他使用 agent-store 的组件
- [ ] 9.2.4 验证没有循环依赖

### 9.3 测试
- [ ] 9.3.1 验证状态管理正常
- [ ] 9.3.2 运行前端测试

## 10. WebSocket Hooks 抽象

### 10.1 创建 Hooks
- [ ] 10.1.1 重构 `web/src/hooks/useWebSocket.ts`（< 200行）
- [ ] 10.1.2 创建 `web/src/hooks/websocket/useWebSocketBase.ts`（< 150行）
- [ ] 10.1.3 创建 `web/src/hooks/websocket/useAgentEvents.ts`（< 100行）
- [ ] 10.1.4 创建 `web/src/hooks/websocket/index.ts`

### 10.2 更新使用方
- [ ] 10.2.1 更新 `web/src/components/chat/ChatArea.tsx` 使用新 hooks
- [ ] 10.2.2 更新其他使用 WebSocket 的组件

### 10.3 测试
- [ ] 10.3.1 测试 WebSocket 连接
- [ ] 10.3.2 测试事件处理

## 11. 目录重组

### 11.1 日志目录
- [ ] 11.1.1 创建 `logs/runtime/` 目录
- [ ] 11.1.2 移动 `logs/deep/` 到 `logs/runtime/`
- [ ] 11.1.3 创建 `logs/debug/` 目录
- [ ] 11.1.4 移动 `logs/session_debug.jsonl` 到 `logs/debug/`
- [ ] 11.1.5 更新代码中的日志路径
- [ ] 11.1.6 更新 `.gitignore`

### 11.2 中间件目录
- [ ] 11.2.1 创建 `backend/infrastructure/runtime/middleware/compression/` 目录
- [ ] 11.2.2 移动 `claude_compression.py` 到压缩目录
- [ ] 11.2.3 更新所有导入路径

### 11.3 测试目录
- [ ] 11.3.1 创建 `tests/unit/` 目录结构
- [ ] 11.3.2 创建 `tests/integration/` 目录结构
- [ ] 11.3.3 创建 `tests/e2e/` 目录结构
- [ ] 11.3.4 移动现有测试文件
- [ ] 11.3.5 更新测试配置

## 12. 验证和文档

### 12.1 代码验证
- [ ] 12.1.1 运行完整后端测试套件
- [ ] 12.1.2 运行前端测试套件
- [ ] 12.1.3 执行端到端测试
- [ ] 12.1.4 检查所有文件行数 < 300行
- [ ] 12.1.5 验证无重复 logger 定义
- [ ] 12.1.6 验证无重复时间函数定义
- [ ] 12.1.7 验证 Snapshot 构建统一

### 12.2 文档更新
- [ ] 12.2.1 更新 `CLAUDE.md` 架构文档
- [ ] 12.2.2 创建重构说明文档
- [ ] 12.2.3 更新 API 文档（如有变化）
- [ ] 12.2.4 代码审查

## 13. 部署准备

### 13.1 版本控制
- [ ] 13.1.1 创建功能分支 `feature/architectural-refactoring`
- [ ] 13.1.2 分阶段提交（每阶段一个 commit）
- [ ] 13.1.3 创建详细的 Pull Request

### 13.2 部署验证
- [ ] 13.2.1 在 staging 环境部署
- [ ] 13.2.2 监控 24 小时
- [ ] 13.2.3 确认无异常后合并到 main
- [ ] 13.2.4 标记 openspec 变更完成
