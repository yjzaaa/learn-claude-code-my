# 前端中心化消息同步 - 实现任务

## Phase 1: 基础设施 (4 tasks)

### 1.1 IndexedDB Schema 与封装
- [x] 创建 `web/src/lib/db/schema.ts`
  - 定义 LocalMessage, Dialog, SyncCheckpoint 接口
  - 配置 Dexie 数据库和索引
- [x] 创建 `web/src/lib/db/index.ts`
  - 导出 db 实例
  - 添加类型安全的 CRUD 辅助函数

### 1.2 写批处理 (WriteBatcher)
- [x] 创建 `web/src/lib/sync/WriteBatcher.ts`
  - 实现缓冲、定时刷新、批量写入
  - 实现 emergencyFlush
- [x] 创建单元测试 `web/src/lib/sync/__tests__/WriteBatcher.test.ts`

### 1.3 CUID 生成器
- [x] 创建 `web/src/lib/utils/cuid.ts`
  - 时间排序 + 随机后缀
  - 确保唯一性

---

## Phase 2: 同步核心 (5 tasks)

### 2.1 SyncCoordinator
- [x] 创建 `web/src/lib/sync/SyncCoordinator.ts`
  - onStreamDelta (检查点逻辑)
  - onStreamComplete (最终持久化)
  - getLastCheckpoint

### 2.2 DisconnectRecovery
- [x] 创建 `web/src/lib/sync/DisconnectRecovery.ts`
  - handleReconnect (恢复流/重发pending)
  - markTruncated (截断处理)

### 2.3 EventBus (同步事件)
- [x] 创建 `web/src/lib/sync/EventBus.ts`
  - 发布订阅模式
  - 类型安全的事件定义

### 2.4 SyncQueue (发送队列)
- [x] 创建 `web/src/lib/sync/SyncQueue.ts`
  - 消息发送队列
  - 指数退避重试
  - 优先级支持

### 2.5 存储归档 (OPFS)
- [x] 创建 `web/src/lib/sync/Archiver.ts`
  - 7天+消息自动归档
  - OPFS读写
  - 空间不足处理

---

## Phase 3: WebSocket 协议 (4 tasks)

### 3.1 类型定义
- [x] 更新 `web/src/types/sync.ts`
  - ClientMessage 类型
  - ServerMessage 类型
  - 与后端对齐

### 3.2 useWebSocket Hook 增强
- [x] 修改 `web/src/hooks/useWebSocket.ts`
  - 添加重连检测
  - 暴露 reconnect 事件

### 3.3 后端 WebSocket Handler
- [x] 修改 `interfaces/websocket/manager.py`
  - handle_send: 使用 client_id
  - handle_resume: 流恢复支持（可选）
- [x] 修改 `interfaces/agent_bridge.py`
  - 支持检查点（chunk索引）

### 3.4 消息ID对齐
- [x] 后端移除 message_id 生成，使用前端传入
- [x] 更新 `core/engine.py` 支持外部ID

---

## Phase 4: Hooks 与 UI (4 tasks)

### 4.1 useMessageSync Hook
- [x] 创建 `web/src/hooks/useMessageSync.ts`
  - 初始化加载 (IndexedDB → Zustand)
  - 发送消息 (乐观更新)
  - 监听WebSocket事件
  - 页面关闭保护

### 4.2 Zustand Store 调整
- [x] 修改 `web/src/stores/messageStore.ts`
  - 移除与后端的复杂合并逻辑
  - 简化状态结构

### 4.3 加载状态处理
- [x] 创建 `web/src/components/chat/ChatInitializer.tsx`
  - 从IndexedDB加载历史
  - 显示加载状态
  - 错误处理

### 4.4 截断提示
- [x] 创建 `web/src/components/chat/TruncatedNotice.tsx`
  - 截断消息提示
  - 一键恢复按钮

---

## Phase 5: 边界情况 (3 tasks)

### 5.1 页面关闭保护
- [x] beforeunload handler
- [x] Beacon API 最后状态通知

### 5.2 存储空间管理
- [x] IndexedDB 空间检测
- [x] 自动触发归档
- [x] 归档失败降级处理

### 5.3 快速连续发送
- [x] 乐观序号保证
- [x] 发送队列串行化
- [x] 测试: 100条/秒发送

---

## Phase 6: 测试与优化 (4 tasks)

### 6.1 单元测试
- [x] WriteBatcher 测试
- [x] SyncCoordinator 测试
- [x] DisconnectRecovery 测试

### 6.2 集成测试
- [x] 刷新页面恢复测试
- [x] 断线重连测试
- [x] 流截断恢复测试

### 6.3 性能测试
- [x] 大数据流 (10MB+)
- [x] 快速发送压力测试
- [x] 内存泄漏检测

### 6.4 E2E 测试
- [x] 完整对话流程
- [x] 多标签页同步（相同dialog）
- [x] 离线后恢复

### 6.5 压力测试
- [x] 100条/秒发送测试

---

## Phase 7: 清理与文档 (2 tasks)

### 7.1 移除旧代码
- [x] 移除后端不必要的持久化代码（已确认：后端仅使用内存存储，无持久化代码）
- [x] 清理前端旧的同步逻辑（已确认：前端逻辑已在前序阶段简化）
- [x] 更新 API 类型（sync.ts 类型已完整）

### 7.2 文档
- [x] 更新 CLAUDE.md 架构说明
- [x] 添加开发者文档
- [x] 添加故障排查指南

---

## 依赖关系

```
Phase 1 (基础)
    │
    ▼
Phase 2 (同步核心)
    │
    ├──► Phase 3 (WebSocket) ──► Phase 4 (Hooks/UI)
    │
    ▼
Phase 5 (边界) ──► Phase 6 (测试) ──► Phase 7 (清理)
```

---

## 验收检查清单

- [x] 刷新页面后对话完整恢复
- [x] 网络中断后自动恢复或截断提示
- [x] 连续快速发送100条消息顺序正确
- [x] IndexedDB满时自动归档
- [x] 页面关闭后重新打开无数据丢失
- [x] 流式消息可中断后恢复（或截断）
- [x] 所有单元测试通过
- [x] 集成测试通过
