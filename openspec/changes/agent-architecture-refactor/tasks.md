# Agent 架构重构任务清单

## 阶段 1：合并事件系统（hooks + monitoring）

### 目标
将分散在 `hooks/` 和 `monitoring/` 的事件系统合并为统一的 `runtime/events.py`。

### 任务

- [x] 1.1 创建 `runtime/` 目录结构
  - 创建 `agents/runtime/__init__.py`
  - 创建 `agents/runtime/events.py`（新的事件系统）

- [x] 1.2 设计 EventSystem 类
  - 支持同步事件处理器（原 hooks）
  - 支持异步外部广播（原 monitoring -> WebSocket）
  - 统一事件类型定义

- [ ] 1.3 迁移 hooks 功能
  - 将 `hooks/composite/composite_hooks.py` 功能整合进 EventSystem
  - 保留 `on_tool_call`, `on_tool_result`, `on_complete` 等方法
  - 确保现有 hook 处理器可以继续工作

- [ ] 1.4 迁移 monitoring 功能
  - 将 `monitoring/services/event_bus.py` 功能整合进 EventSystem
  - 保留外部广播能力（WebSocket 适配器）
  - 保留事件类型定义（EventType 枚举）

- [ ] 1.5 更新现有代码使用新事件系统
  - 更新 `hooks/state_managed_agent_bridge.py`
  - 更新 `monitoring/bridge/composite.py`
  - 确保 backward compatibility

- [ ] 1.6 测试验证
  - 运行现有测试确保功能正常
  - 验证事件正确触发和广播
  - 验证 WebSocket 事件推送正常

### 验证标准
- [ ] 所有现有测试通过
- [ ] WebSocket 事件推送正常
- [ ] 代码可以成功运行一次完整对话

---

## 阶段 2：集中状态管理

### 目标
创建统一的 `runtime/state.py`，合并所有状态管理。

### 任务

- [x] 2.1 创建 StateManager 类
  - 统一管理 DialogSession
  - 支持插件隔离的状态存储
  - 线程/协程安全

- [ ] 2.2 迁移 `hooks/state_managed_agent_bridge.py` 状态管理
  - 提取 DialogSession 管理逻辑
  - 提取消息历史管理
  - 提取快照生成逻辑

- [ ] 2.3 迁移 `monitoring/` 中的状态跟踪
  - 合并 monitoring 的状态机
  - 统一状态快照格式

- [ ] 2.4 更新 EventSystem 与 StateManager 集成
  - 状态变更自动触发事件
  - 支持状态快照广播

- [ ] 2.5 更新现有代码使用新状态管理
  - 更新 `api/main_new.py`
  - 更新所有使用旧状态管理的代码

- [ ] 2.6 测试验证
  - 验证对话状态正确保存
  - 验证插件状态隔离
  - 验证状态快照正确生成

### 验证标准
- [ ] 对话状态在重启后恢复（如需要）
- [ ] 插件间状态不互相干扰
- [ ] WebSocket 广播的状态快照完整

---

## 阶段 3：提取 Kernel Agent

### 目标
创建最小 Agent 核心，位于 `kernel/agent.py`。

### 任务

- [ ] 3.1 创建 `kernel/` 目录结构
  - 创建 `agents/kernel/__init__.py`
  - 创建 `agents/kernel/agent.py`
  - 创建 `agents/kernel/loop.py`（执行循环）
  - 创建 `agents/kernel/registry.py`（插件注册表）

- [ ] 3.2 提取核心循环逻辑
  - 从 `base/base_agent_loop.py` 提取最小循环
  - 移除所有非核心功能（移到插件）
  - 保留工具调用机制

- [ ] 3.3 实现 KernelAgent 类
  - 构造函数接受 StateManager, EventSystem
  - 实现 `run()` 方法
  - 实现 `use_plugin()` 方法

- [ ] 3.4 实现 PluginRegistry
  - 插件注册和管理
  - 工具收集
  - 插件生命周期管理

- [ ] 3.5 创建 Plugin 基类
  - 定义 `on_load()`, `get_tools()`, `on_unload()` 接口
  - 与现有 `plugins/base.py` 兼容或替换

- [ ] 3.6 测试验证
  - KernelAgent 可以独立运行
  - 支持基础工具调用
  - 支持插件加载

### 验证标准
- [ ] KernelAgent 可以完成简单对话
- [ ] 插件可以正确注册和卸载
- [ ] 工具调用正常工作

---

## 阶段 4：插件化现有功能

### 目标
将现有功能迁移到 `plugins/builtin/` 目录，每个功能一个插件。

### 4.1 Todo 插件

- [ ] 创建 `plugins/builtin/todo/` 目录
- [ ] 迁移 `plugins/todo.py` 到 `plugins/builtin/todo/plugin.py`
- [ ] 提取工具到 `plugins/builtin/todo/tools.py`
- [ ] 实现 TodoPlugin 类
- [ ] 更新状态管理使用 StateManager
- [ ] 测试验证

### 4.2 Task 插件

- [ ] 创建 `plugins/builtin/task/` 目录
- [ ] 迁移 `plugins/task.py` 到 `plugins/builtin/task/plugin.py`
- [ ] 迁移持久化存储逻辑
- [ ] 实现 TaskPlugin 类
- [ ] 测试验证

### 4.3 Background 插件

- [ ] 创建 `plugins/builtin/background/` 目录
- [ ] 迁移 `plugins/background.py` 到 `plugins/builtin/background/plugin.py`
- [ ] 迁移 BackgroundManager 到 `plugins/builtin/background/manager.py`
- [ ] 迁移 BackgroundTaskBridge 到 `plugins/builtin/background/bridge.py`
- [ ] 实现 BackgroundPlugin 类
- [ ] 测试验证

### 4.4 Subagent 插件

- [ ] 创建 `plugins/builtin/subagent/` 目录
- [ ] 迁移 `plugins/subagent.py` 到 `plugins/builtin/subagent/plugin.py`
- [ ] 迁移子代理监控桥接
- [ ] 实现 SubagentPlugin 类
- [ ] 测试验证

### 4.5 Team 插件

- [ ] 创建 `plugins/builtin/team/` 目录
- [ ] 迁移 `plugins/team.py` 到 `plugins/builtin/team/plugin.py`
- [ ] 实现 TeamPlugin 类
- [ ] 测试验证

### 4.6 Plan 插件

- [ ] 创建 `plugins/builtin/plan/` 目录
- [ ] 迁移 `plugins/plan.py` 到 `plugins/builtin/plan/plugin.py`
- [ ] 实现 PlanPlugin 类
- [ ] 测试验证

### 4.7 Skill 插件

- [ ] 创建 `plugins/builtin/skill/` 目录
- [ ] 迁移 `plugins/skill_plugin.py` 到 `plugins/builtin/skill/plugin.py`
- [ ] 迁移 `core/s05_skill_loading.py` 到 `plugins/builtin/skill/loader.py`
- [ ] 实现 SkillPlugin 类
- [ ] 测试验证

### 阶段 4 验证标准
- [ ] 所有插件可以独立加载
- [ ] 每个插件提供正确的工具
- [ ] 插件间不互相干扰
- [ ] 所有功能测试通过

---

## 阶段 5：重构接口层

### 目标
重构 `api/` 和 `websocket/` 到 `interfaces/` 目录。

### 任务

- [ ] 5.1 创建 `interfaces/` 目录结构
  - 创建 `agents/interfaces/__init__.py`
  - 创建 `agents/interfaces/http/` 目录
  - 创建 `agents/interfaces/websocket/` 目录

- [ ] 5.2 迁移 HTTP API
  - 迁移 `api/main_new.py` 路由到 `interfaces/http/routes/`
  - 创建 `interfaces/http/server.py`（FastAPI 应用）
  - 保持 API 兼容

- [ ] 5.3 迁移 WebSocket
  - 迁移 `websocket/server.py` 到 `interfaces/websocket/`
  - 创建 `interfaces/websocket/connection.py`
  - 集成新的 EventSystem

- [ ] 5.4 更新入口文件
  - 更新 `start_server.py` 使用新接口层
  - 创建新的 `main.py` 统一入口

- [ ] 5.5 测试验证
  - HTTP API 正常工作
  - WebSocket 连接正常
  - 前后端通信正常

### 验证标准
- [ ] 前端可以正常连接
- [ ] 所有 API 端点工作
- [ ] WebSocket 事件推送正常

---

## 阶段 6：清理旧代码

### 目标
删除旧的目录和文件，更新导入路径。

### 任务

- [ ] 6.1 删除旧目录
  - [ ] 删除 `agents/agent/`（确认内容已迁移）
  - [ ] 删除 `agents/agents/`（确认内容已迁移）
  - [ ] 删除 `agents/hooks/`（确认功能已合并到 runtime）
  - [ ] 删除 `agents/monitoring/`（确认功能已合并到 runtime）
  - [ ] 删除 `agents/api/`（确认已迁移到 interfaces）
  - [ ] 删除 `agents/websocket/`（确认已迁移到 interfaces）

- [ ] 6.2 重构 `agents/base/`
  - [ ] 保留必要的基类（如 BaseAgentLoop 如果还在用）
  - [ ] 删除已迁移到 kernel 的内容
  - [ ] 或删除整个目录（如果全部迁移完成）

- [ ] 6.3 重构 `agents/core/`
  - [ ] 迁移/删除 `builder.py`（已迁移到 runtime）
  - [ ] 迁移/删除 `s05_skill_loading.py`（已迁移到 plugins）
  - [ ] 保留或迁移 `messages.py`

- [ ] 6.4 更新所有导入路径
  - [ ] 批量更新相对导入
  - [ ] 修复导入错误

- [ ] 6.5 最终测试
  - [ ] 运行所有测试
  - [ ] 进行完整功能测试
  - [ ] 验证无遗留引用

### 验证标准
- [ ] 无遗留的旧目录
- [ ] 所有导入路径正确
- [ ] 功能完整无缺失

---

## 最终验证

### 整体架构检查
- [ ] 目录结构符合设计
- [ ] 依赖关系正确（上层依赖下层）
- [ ] 无循环依赖

### 功能验证
- [ ] 完整对话流程正常
- [ ] 所有插件功能正常
- [ ] WebSocket 监控正常
- [ ] 状态持久化正常

### 代码质量
- [ ] 所有测试通过
- [ ] 代码覆盖率不低于重构前
- [ ] 文档更新完成

---

## 时间估计

| 阶段 | 预计时间 | 依赖 |
|------|----------|------|
| 阶段 1 | 1-2 天 | 无 |
| 阶段 2 | 2-3 天 | 阶段 1 |
| 阶段 3 | 2-3 天 | 阶段 2 |
| 阶段 4 | 3-5 天 | 阶段 3 |
| 阶段 5 | 2-3 天 | 阶段 4 |
| 阶段 6 | 1-2 天 | 阶段 5 |
| **总计** | **11-18 天** | - |

---

## 风险缓解

1. **每个阶段独立提交**
   - 每个任务完成后提交
   - 可独立回滚任何阶段

2. **阶段间兼容性层**
   - 每个阶段结束前保留兼容性代码
   - 下一阶段开始前才删除

3. **并行测试**
   - 每个阶段完成后对比功能
   - 确保无功能丢失

4. **回滚策略**
   - 如果某阶段失败，回滚到上一阶段提交
   - 不一次性回滚所有阶段
