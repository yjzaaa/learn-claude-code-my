## 1. 日志抽象 (Logging Abstraction)

- [ ] 1.1 创建 `backend/infrastructure/logging/logger_factory.py`，实现 LoggerFactory 类
- [ ] 1.2 创建 `backend/infrastructure/logging/__init__.py`，导出 LoggerFactory
- [ ] 1.3 更新 `backend/infrastructure/runtime/deep.py`，使用 LoggerFactory
- [ ] 1.4 更新 `backend/infrastructure/services/provider_manager.py`，使用 LoggerFactory
- [ ] 1.5 更新 `backend/domain/models/dialog/manager.py`，使用 LoggerFactory
- [ ] 1.6 更新 `backend/infrastructure/event_bus/handlers.py`，使用 LoggerFactory
- [ ] 1.7 更新 `backend/interfaces/http/routes/` 下的所有路由文件，使用 LoggerFactory
- [ ] 1.8 更新 `backend/infrastructure/services/` 下的所有服务文件，使用 LoggerFactory
- [ ] 1.9 验证所有 logger 定义都通过工厂创建，搜索 `logging.getLogger` 应该只在工厂中出现
- [ ] 1.10 运行测试确保日志功能正常

## 2. ProviderManager 拆分

- [ ] 2.1 创建 `backend/infrastructure/services/model_discovery.py`，提取模型发现逻辑
- [ ] 2.2 创建 `backend/infrastructure/services/model_connectivity.py`，提取连通性测试逻辑
- [ ] 2.3 创建 `backend/infrastructure/services/model_factory.py`，提取模型实例创建逻辑
- [ ] 2.4 更新 `backend/infrastructure/services/provider_manager.py`，使用新拆分的模块
- [ ] 2.5 确保 ProviderManager 向后兼容，现有 API 不变
- [ ] 2.6 验证每个新模块行数小于 250 行
- [ ] 2.7 运行测试确保模型发现、连通性测试、实例创建功能正常

## 3. Dialog Manager 拆分

- [ ] 3.1 创建 `backend/domain/models/dialog/session_lifecycle.py`，提取会话生命周期管理
- [ ] 3.2 创建 `backend/domain/models/dialog/message_ops.py`，提取消息操作
- [ ] 3.3 创建 `backend/domain/models/dialog/event_emitter.py`，提取事件发射
- [ ] 3.4 更新 `backend/domain/models/dialog/manager.py`，使用新拆分的模块
- [ ] 3.5 在 `backend/domain/models/dialog/__init__.py` 中导出所有新模块
- [ ] 3.6 验证每个新模块行数符合要求
- [ ] 3.7 运行测试确保对话管理功能正常

## 4. Deep Runtime 模块化

- [ ] 4.1 创建 `backend/infrastructure/runtime/deep_agent.py`，提取 agent 生命周期管理（< 250 行）
- [ ] 4.2 创建 `backend/infrastructure/runtime/deep_events.py`，提取事件流处理（< 250 行）
- [ ] 4.3 创建 `backend/infrastructure/runtime/deep_model.py`，提取模型切换逻辑（< 250 行）
- [ ] 4.4 创建 `backend/infrastructure/runtime/deep_checkpoint.py`，提取 checkpoint 管理（< 200 行）
- [ ] 4.5 创建 `backend/infrastructure/runtime/deep_types.py`，提取共享类型定义
- [ ] 4.6 更新 `backend/infrastructure/runtime/deep.py`，作为 facade 组合新模块
- [ ] 4.7 确保所有现有导入继续工作，保持向后兼容
- [ ] 4.8 验证 `deep.py` 总行数减少到 300 行以下
- [ ] 4.9 运行完整测试套件确保运行时功能正常

## 5. 前端组件拆分

- [ ] 5.1 创建 `web/src/components/chat/ModelSelector.tsx`，提取模型选择器（< 150 行）
- [ ] 5.2 创建 `web/src/components/chat/SlashCommandMenu.tsx`，提取斜杠命令菜单（< 100 行）
- [ ] 5.3 创建 `web/src/components/chat/FileAttachment.tsx`，提取文件附件组件（< 100 行）
- [ ] 5.4 更新 `web/src/components/chat/InputArea.tsx`，使用拆分的子组件（< 250 行）
- [ ] 5.5 在 `web/src/components/chat/index.ts` 中导出所有新组件
- [ ] 5.6 验证组件 props 接口清晰、类型安全
- [ ] 5.7 运行前端构建确保无 TypeScript 错误

## 6. Agent Store 拆分

- [ ] 6.1 更新 `web/src/stores/dialog-store.ts`，分离对话相关状态（< 150 行）
- [ ] 6.2 更新 `web/src/stores/message-store.ts`，分离消息相关状态（< 150 行）
- [ ] 6.3 创建 `web/src/stores/status-store.ts`，分离状态管理（< 100 行）
- [ ] 6.4 更新 `web/src/agent/agent-store.ts`，作为组合入口或废弃
- [ ] 6.5 更新所有使用 agent-store 的组件，使用新的拆分 store
- [ ] 6.6 验证 store 之间没有循环依赖
- [ ] 6.7 运行前端测试确保状态管理正常

## 7. WebSocket Hooks 抽象

- [ ] 7.1 重构 `web/src/hooks/useWebSocket.ts`，提取通用 WebSocket 逻辑（< 200 行）
- [ ] 7.2 创建 `web/src/hooks/useAgentEvents.ts`，封装 Agent 特定事件
- [ ] 7.3 更新 `web/src/components/chat/ChatArea.tsx`，使用新的 hooks
- [ ] 7.4 验证 hooks 返回类型清晰、文档完善
- [ ] 7.5 运行测试确保 WebSocket 连接和事件处理正常

## 8. 目录重组

- [ ] 8.1 创建 `logs/runtime/` 目录，移动运行时日志
- [ ] 8.2 创建 `logs/debug/` 目录，移动调试日志
- [ ] 8.3 更新所有代码中的日志路径引用
- [ ] 8.4 创建 `backend/infrastructure/runtime/middleware/compression/` 目录
- [ ] 8.5 移动 `claude_compression.py` 到压缩中间件目录
- [ ] 8.6 更新中间件导入路径
- [ ] 8.7 更新 `.gitignore` 添加新的日志目录模式
- [ ] 8.8 创建 `tests/unit/`、`tests/integration/`、`tests/e2e/` 目录结构
- [ ] 8.9 移动现有测试文件到对应目录
- [ ] 8.10 更新测试导入路径和配置

## 9. 验证和文档

- [ ] 9.1 运行完整后端测试套件，确保所有测试通过
- [ ] 9.2 运行前端测试套件，确保所有测试通过
- [ ] 9.3 执行端到端测试，验证完整功能流程
- [ ] 9.4 检查所有文件行数符合架构要求（< 300 行）
- [ ] 9.5 验证没有重复代码（logger 定义、模型配置等）
- [ ] 9.6 更新 `CLAUDE.md` 中的架构文档
- [ ] 9.7 创建重构说明文档，记录主要变更点
- [ ] 9.8 代码审查，确保代码质量符合项目标准

## 10. 部署准备

- [ ] 10.1 创建功能分支 `feature/architectural-refactoring`
- [ ] 10.2 分阶段提交，每个阶段一个 commit
- [ ] 10.3 创建 Pull Request，包含详细变更说明
- [ ] 10.4 在 staging 环境部署测试
- [ ] 10.5 监控 24 小时，确认无异常
- [ ] 10.6 合并到 main 分支
- [ ] 10.7 创建归档说明，标记 openspec 变更完成
