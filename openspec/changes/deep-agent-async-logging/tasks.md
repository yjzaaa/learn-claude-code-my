## 1. 日志配置模块扩展

- [x] 1.1 导入必要的类型定义（Optional, logger.__class__）
- [x] 1.2 添加 Deep Agent 日志配置常量（DEEP_LOG_DIR, DEEP_LOG_ROTATION, DEEP_LOG_RETENTION）
- [x] 1.3 定义全局 logger 变量（deep_msg_logger, deep_update_logger, deep_value_logger）
- [x] 1.4 实现 `_create_deep_logger()` 辅助函数，使用 bind + filter + enqueue=True
- [x] 1.5 实现 `setup_deep_loggers()` 初始化函数
- [x] 1.6 实现三个 getter 函数（get_deep_msg_logger, get_deep_update_logger, get_deep_value_logger）
- [x] 1.7 在 `setup_logging()` 中调用 `setup_deep_loggers()`
- [x] 1.8 更新 `__all__` 导出列表

## 2. Deep Runtime 集成日志

- [x] 2.1 导入三个专用 logger 函数
- [x] 2.2 在 `__init__` 中初始化三个 logger
- [x] 2.3 实现 `_log_values()` 方法，记录完整状态
- [x] 2.4 实现 `_log_messages_from_values()` 方法，提取 AIMessage 详情
- [x] 2.5 实现 `_log_updates_from_values()` 方法，推断节点更新
- [x] 2.6 修改 `send_message()` 方法，添加三种日志调用
- [x] 2.7 在 `create_dialog()` 中添加创建日志
- [x] 2.8 在 `stop()` 中添加停止日志

## 3. 配置和环境变量

- [x] 3.1 在 `.env.example` 中添加 `DEEP_LOG_DIR` 配置
- [x] 3.2 在 `.env.example` 中添加 `DEEP_LOG_ROTATION` 配置
- [x] 3.3 在 `.env.example` 中添加 `DEEP_LOG_RETENTION` 配置
- [x] 3.4 添加配置说明注释

## 4. 验证和测试

- [ ] 4.1 验证语法正确性（`python -m py_compile`）
- [ ] 4.2 运行 Deep Agent 测试对话，检查日志文件生成
- [ ] 4.3 验证三种日志文件内容符合预期
- [ ] 4.4 测试日志轮转功能
