# Agent 插件与监控联调测试指南

## 测试目标
验证 Agent 插件功能正常，且监控事件能正确显示在网页端。

## 测试环境要求
- 后端: http://localhost:8001
- 前端: http://localhost:3000
- 浏览器: Chrome/Edge

## 测试问题列表

### 问题 1: 测试基础对话
**问题**: "你好，请简单介绍一下自己"

**正常标准**:
- [ ] 前端能正常显示对话界面
- [ ] Agent 能回复消息
- [ ] 监控页面能看到 AGENT_STARTED 事件
- [ ] 监控页面能看到 AGENT_COMPLETED 事件

---

### 问题 2: 测试 Todo 插件
**问题**: "我有一个任务需要完成：1. 分析代码结构 2. 找出bug 3. 修复并测试。请帮我跟踪进度"

**正常标准**:
- [ ] Agent 调用 todo 工具创建任务列表
- [ ] 前端显示 todo 列表
- [ ] 监控页面能看到 TODO_UPDATED 事件
- [ ] 监控页面能看到工具调用记录

---

### 问题 3: 测试 Background 插件
**问题**: "请帮我后台运行一个命令：ping localhost -n 5，然后检查状态"

**正常标准**:
- [ ] Agent 调用 bg_run 启动后台任务
- [ ] 监控页面能看到 BG_TASK_STARTED 事件
- [ ] 后台任务完成后能看到 BG_TASK_COMPLETED 事件
- [ ] 事件包含 command、exit_code、duration_ms 字段

---

### 问题 4: 测试 Subagent 插件
**问题**: "我有一个复杂的任务需要分解：请使用子代理帮我分析一下当前目录的文件结构"

**正常标准**:
- [ ] Agent 调用 subagent 工具
- [ ] 监控页面能看到 SUBAGENT_STARTED 事件
- [ ] 监控页面能看到 SUBAGENT_COMPLETED 事件
- [ ] 事件包含 subagent_name、subagent_type 字段

---

### 问题 5: 测试 Task 持久化
**问题**: "请创建一个持久化任务：标题\"测试任务\"，描述\"用于测试任务持久化功能\""

**正常标准**:
- [ ] Agent 调用 task_create 创建任务
- [ ] 任务被保存到 .tasks/ 目录
- [ ] 刷新页面后任务仍然存在
- [ ] 能通过 task_list 查看所有任务

---

## 监控事件检查清单

### 必须看到的事件类型
- [ ] AGENT_STARTED - Agent 开始执行
- [ ] AGENT_COMPLETED - Agent 执行完成
- [ ] TOOL_CALL - 工具调用
- [ ] TOOL_RESULT - 工具返回结果
- [ ] TODO_UPDATED - Todo 列表更新
- [ ] BG_TASK_STARTED - 后台任务开始
- [ ] BG_TASK_COMPLETED - 后台任务完成
- [ ] SUBAGENT_STARTED - 子代理开始
- [ ] SUBAGENT_COMPLETED - 子代理完成

### 事件字段检查
每个事件应该包含:
- [ ] event_type - 事件类型
- [ ] dialog_id - 对话ID
- [ ] timestamp - 时间戳
- [ ] payload - 事件详情

## 测试步骤

### 手动测试流程
1. 打开浏览器访问 http://localhost:3000/en/
2. 创建新对话或选择已有对话
3. 发送测试问题
4. 打开 http://localhost:3000/en/monitoring 监控页面
5. 检查对应的事件是否出现

### 自动化测试
运行测试脚本:
```bash
cd agents/tests
python test_e2e_monitoring.py
```

## 常见问题排查

### 问题: 监控页面没有事件
**排查步骤**:
1. 检查 WebSocket 连接状态
2. 查看浏览器控制台是否有错误
3. 检查后端日志是否有事件发送记录

### 问题: 插件工具不生效
**排查步骤**:
1. 检查 Agent 是否正确加载插件
2. 查看工具调用日志
3. 检查工具参数是否正确

### 问题: 后台任务无监控
**排查步骤**:
1. 确认 BackgroundTaskBridge 已集成
2. 检查任务是否在后台运行
3. 查看事件总线是否正常工作
