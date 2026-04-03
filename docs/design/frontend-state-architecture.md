# 前端状态管理架构重构方案

## 1. 当前架构分析

### 1.1 现有结构

```
web/src/
  stores/
    dialog.ts        - Zustand 对话状态（基础消息操作）
    websocket.ts     - WebSocket 连接状态
    ui.ts            - UI 状态（主题、布局等）
  hooks/
    useMessageSync.ts    - 消息同步核心 Hook
    useWebSocket.ts      - WebSocket 连接管理
    useOptimisticOrder.ts - 乐观序号管理
    useStorageMonitor.ts - 存储监控
  lib/
    db/              - IndexedDB 持久化层
    sync/            - 同步协调器、写批处理、事件总线
    types/sync.ts    - 同步协议类型定义
```

### 1.2 现存问题

| 问题 | 影响 | 位置 |
|------|------|------|
| 状态分散 | 多个 store 之间缺乏统一协调 | stores/*.ts |
| WebSocket 与状态更新耦合 | 难以测试和维护 | useWebSocket.ts, useMessageSync.ts |
| 乐观更新机制复杂 | 容易出错，回滚逻辑分散 | useMessageSync.ts |
| 类型定义重复 | TypeScript 类型不一致 | types/ vs stores/ |
| 缺乏统一错误处理 | 错误处理分散在各组件 | 多处 |

## 2. 新架构设计

### 2.1 核心原则

1. **按领域划分状态** - Dialog, Message, Sync, UI 四大领域
2. **单向数据流** - WebSocket → Sync Layer → Store → UI
3. **乐观更新 + 错误回滚** - 统一的事务性更新机制
4. **完整的 TypeScript 类型** - 从协议到 UI 的类型一致性

### 2.2 新目录结构

```
web/src/
  stores/
    index.ts              # Store 统一导出
    dialog-store.ts       # 对话领域状态
    message-store.ts      # 消息领域状态
    sync-store.ts         # 同步领域状态
    ui-store.ts           # UI 状态（现有）
  sync/
    index.ts              # 同步模块统一导出
    protocol.ts           # WebSocket 协议类型（从 types/sync.ts 迁移）
    connection.ts         # 连接管理器
    message-handler.ts    # 消息处理器
    optimistic-update.ts  # 乐观更新管理器
    state-reconciler.ts   # 状态协调器
  hooks/
    useDialog.ts          # 对话操作 Hook
    useMessages.ts        # 消息操作 Hook
    useSyncStatus.ts      # 同步状态 Hook
    useSendMessage.ts     # 发送消息 Hook（乐观更新）
  types/
    domain.ts             # 领域模型类型
    api.ts                # API 类型
```

## 3. 状态设计

### 3.1 Dialog Store

```typescript
// stores/dialog-store.ts
interface DialogState {
  // 状态
  dialogs: Dialog[];
  currentDialogId: string | null;
  isLoading: boolean;
  error: Error | null;

  // 计算属性
  currentDialog: Dialog | null;
  dialogList: DialogSummary[];

  // Actions
  setCurrentDialog(id: string | null): void;
  addDialog(dialog: Dialog): void;
  updateDialog(id: string, updates: Partial<Dialog>): void;
  removeDialog(id: string): void;
  setLoading(loading: boolean): void;
  setError(error: Error | null): void;
}
```

### 3.2 Message Store

```typescript
// stores/message-store.ts
interface MessageState {
  // 状态 - 按 dialogId 分组存储
  messagesByDialog: Map<string, Message[]>;
  streamingMessageId: string | null;
  pendingMessages: Map<string, PendingMessage>;

  // 计算属性
  getMessages(dialogId: string): Message[];
  getStreamingMessage(dialogId: string): Message | null;

  // Actions
  addMessage(dialogId: string, message: Message): void;
  updateMessage(dialogId: string, messageId: string, updates: Partial<Message>): void;
  removeMessage(dialogId: string, messageId: string): void;
  setStreamingMessage(dialogId: string, messageId: string | null): void;
  appendContent(dialogId: string, messageId: string, delta: string): void;

  // 乐观更新
  addOptimisticMessage(dialogId: string, content: string): PendingMessage;
  confirmMessage(clientId: string, serverMessage: Message): void;
  rollbackMessage(clientId: string): void;
}
```

### 3.3 Sync Store

```typescript
// stores/sync-store.ts
interface SyncState {
  // 连接状态
  connectionStatus: ConnectionStatus;
  reconnectAttempts: number;
  lastPingAt: number | null;

  // 同步状态
  pendingSyncs: number;
  isSyncing: boolean;
  lastSyncAt: number | null;

  // 错误状态
  syncErrors: SyncError[];

  // Actions
  setConnectionStatus(status: ConnectionStatus): void;
  incrementReconnectAttempt(): void;
  resetReconnectAttempt(): void;
  startSync(): void;
  endSync(): void;
  addSyncError(error: SyncError): void;
  clearSyncErrors(): void;
}
```

## 4. 数据流设计

### 4.1 状态更新流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户操作                                  │
│                   (发送消息、切换对话等)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Optimistic Update                           │
│              1. 生成乐观消息 (pending 状态)                       │
│              2. 更新 MessageStore (立即显示)                      │
│              3. 保存到 IndexedDB                                 │
│              4. 加入发送队列                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     WebSocket Layer                             │
│              1. 建立/维护连接                                    │
│              2. 发送消息到服务端                                  │
│              3. 接收服务端事件                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Message Handler                              │
│              根据事件类型路由到不同处理器：                        │
│              - ack → confirmMessage                             │
│              - stream:start → setStreamingMessage               │
│              - stream:delta → appendContent                     │
│              - stream:end → confirmMessage                      │
│              - error → rollbackMessage                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    State Reconciler                             │
│              1. 合并乐观状态和服务端状态                          │
│              2. 解决冲突（乐观序号优先）                          │
│              3. 更新 Store                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       UI 渲染                                    │
│              React 组件订阅 Store 变化自动更新                    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 乐观更新时序图

```
时间轴 ─────────────────────────────────────────────────────────────►

用户        UI              MessageStore        SyncQueue        WebSocket        Server
 │          │                    │                  │               │              │
 │──发送────►│                    │                  │               │              │
 │          │                    │                  │               │              │
 │          │──addOptimisticMsg──►│                  │               │              │
 │          │                    │                  │               │              │
 │          │◄─────pendingId─────│                  │               │              │
 │          │                    │                  │               │              │
 │          │───────────────enqueue───────────────►│               │              │
 │          │                    │                  │               │              │
 │          │◄────────────立即显示乐观消息───────────┘               │              │
 │          │                    │                  │               │              │
 │          │                    │                  │──send────────►│              │
 │          │                    │                  │               │              │
 │          │                    │                  │◄────────ack───┤              │
 │          │                    │                  │               │              │
 │          │                    │◄──────────confirmMessage─────────│              │
 │          │                    │                  │               │              │
 │          │◄────────────状态更新为 sending─────────────────────────┘              │
 │          │                    │                  │               │              │
 │          │                    │                  │◄────stream:start─────────────│
 │          │                    │                  │               │              │
 │          │                    │◄──────────setStreamingMsg────────────────────────│
 │          │                    │                  │               │              │
 │          │                    │                  │◄────stream:delta─────────────│
 │          │                    │                  │               │              │
 │          │                    │◄──────────appendContent──────────────────────────│
 │          │                    │                  │               │              │
 │          │◄────────────────流式更新UI───────────────────────────────────────────│
 │          │                    │                  │               │              │
 │          │                    │                  │◄────stream:end───────────────│
 │          │                    │                  │               │              │
 │          │                    │◄──────────confirmMessage─────────────────────────│
 │          │                    │                  │               │              │
 │          │◄────────────状态更新为 completed───────────────────────────────────────│
 │          │                    │                  │               │              │

失败场景：
 │          │                    │                  │               │              │
 │          │                    │                  │◄────error────────────────────│
 │          │                    │                  │               │              │
 │          │                    │◄──────────rollbackMessage────────────────────────│
 │          │                    │                  │               │              │
 │          │◄────────────显示错误，恢复之前状态──────────────────────────────────────│
 │          │                    │                  │               │              │
```

## 5. WebSocket 同步机制

### 5.1 协议类型（完整定义）

```typescript
// sync/protocol.ts

// ============================================================================
// Client → Server
// ============================================================================

export interface SendMessageRequest {
  type: 'send';
  dialogId: string;
  clientId: string;
  content: string;
  optimisticOrder: number;
  parentMessageId?: string;
}

export interface SubscribeRequest {
  type: 'subscribe';
  dialogId: string;
  lastKnownMessageId?: string;
}

export interface SyncRequest {
  type: 'sync:request';
  dialogId: string;
  lastSyncAt?: number;
}

export type ClientRequest =
  | SendMessageRequest
  | SubscribeRequest
  | SyncRequest
  | { type: 'ping' }
  | { type: 'unsubscribe'; dialogId: string };

// ============================================================================
// Server → Client
// ============================================================================

export interface AckMessage {
  type: 'ack';
  clientId: string;
  serverId: string;
  dialogId: string;
  timestamp: number;
}

export interface StreamStartMessage {
  type: 'stream:start';
  dialogId: string;
  messageId: string;
  role: MessageRole;
  metadata?: {
    model?: string;
    agentName?: string;
  };
}

export interface StreamDeltaMessage {
  type: 'stream:delta';
  dialogId: string;
  messageId: string;
  chunkIndex: number;
  delta: string;
  isReasoning?: boolean;
}

export interface StreamEndMessage {
  type: 'stream:end';
  dialogId: string;
  messageId: string;
  finalContent: string;
  usage?: TokenUsage;
}

export interface StreamTruncatedMessage {
  type: 'stream:truncated';
  dialogId: string;
  messageId: string;
  reason: 'interrupted' | 'timeout' | 'error';
  lastChunkIndex: number;
}

export interface DialogSnapshotMessage {
  type: 'dialog:snapshot';
  dialogId: string;
  data: DialogSnapshot;
}

export interface ErrorMessage {
  type: 'error';
  dialogId?: string;
  messageId?: string;
  error: {
    code: string;
    message: string;
  };
}

export type ServerResponse =
  | AckMessage
  | StreamStartMessage
  | StreamDeltaMessage
  | StreamEndMessage
  | StreamTruncatedMessage
  | DialogSnapshotMessage
  | ErrorMessage
  | { type: 'pong' };
```

### 5.2 连接管理器

```typescript
// sync/connection.ts
import { EventEmitter } from '@/lib/event-emitter';

interface ConnectionConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

interface ConnectionEvents {
  'state:change': { previous: ConnectionStatus; current: ConnectionStatus };
  'message': ServerResponse;
  'error': Error;
}

export class ConnectionManager extends EventEmitter<ConnectionEvents> {
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = 'disconnected';
  private reconnectAttempts = 0;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private config: Required<ConnectionConfig>;

  constructor(config: ConnectionConfig) {
    super();
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      ...config,
    };
  }

  connect(): void {
    if (this.status === 'connected' || this.status === 'connecting') return;

    this.setStatus('connecting');

    try {
      this.ws = new WebSocket(this.config.url);

      this.ws.onopen = () => {
        this.setStatus('connected');
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerResponse;
          this.emit('message', message);
        } catch (err) {
          this.emit('error', err as Error);
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.setStatus('disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = (err) => {
        this.emit('error', new Error('WebSocket error'));
      };
    } catch (err) {
      this.setStatus('error');
      this.emit('error', err as Error);
    }
  }

  send(message: ClientRequest): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  disconnect(): void {
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
  }

  private setStatus(status: ConnectionStatus): void {
    const previous = this.status;
    this.status = status;
    this.emit('state:change', { previous, current: status });
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.setStatus('error');
      return;
    }

    this.setStatus('reconnecting');
    this.reconnectAttempts++;

    setTimeout(() => {
      this.connect();
    }, this.config.reconnectInterval * this.reconnectAttempts);
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' });
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }
}
```

## 6. 关键代码实现

### 6.1 乐观更新管理器

```typescript
// sync/optimistic-update.ts
import { generateCUID } from '@/lib/utils/cuid';

interface OptimisticMessage {
  clientId: string;
  dialogId: string;
  content: string;
  optimisticOrder: number;
  status: 'pending' | 'sending' | 'confirmed' | 'failed';
  createdAt: number;
  rollback: () => void;
}

interface OptimisticUpdateConfig {
  onAdd: (msg: OptimisticMessage) => void;
  onConfirm: (clientId: string, serverMessage: Message) => void;
  onFail: (clientId: string, error: Error) => void;
  onRollback: (clientId: string) => void;
}

export class OptimisticUpdateManager {
  private pendingMessages = new Map<string, OptimisticMessage>();
  private config: OptimisticUpdateConfig;
  private orderGenerator = createOrderGenerator();

  constructor(config: OptimisticUpdateConfig) {
    this.config = config;
  }

  /**
   * 创建乐观消息
   */
  create(dialogId: string, content: string): OptimisticMessage {
    const clientId = generateCUID();
    const optimisticOrder = this.orderGenerator.next();

    const message: OptimisticMessage = {
      clientId,
      dialogId,
      content,
      optimisticOrder,
      status: 'pending',
      createdAt: Date.now(),
      rollback: () => this.rollback(clientId),
    };

    this.pendingMessages.set(clientId, message);
    this.config.onAdd(message);

    return message;
  }

  /**
   * 确认消息成功
   */
  confirm(clientId: string, serverMessage: Message): void {
    const pending = this.pendingMessages.get(clientId);
    if (!pending) return;

    pending.status = 'confirmed';
    this.config.onConfirm(clientId, serverMessage);
    this.pendingMessages.delete(clientId);
  }

  /**
   * 标记发送中
   */
  markSending(clientId: string): void {
    const pending = this.pendingMessages.get(clientId);
    if (pending) {
      pending.status = 'sending';
    }
  }

  /**
   * 标记失败
   */
  markFailed(clientId: string, error: Error): void {
    const pending = this.pendingMessages.get(clientId);
    if (!pending) return;

    pending.status = 'failed';
    this.config.onFail(clientId, error);
  }

  /**
   * 回滚乐观更新
   */
  rollback(clientId: string): void {
    const pending = this.pendingMessages.get(clientId);
    if (!pending) return;

    this.config.onRollback(clientId);
    this.pendingMessages.delete(clientId);
  }

  /**
   * 获取所有 pending 消息
   */
  getPending(): OptimisticMessage[] {
    return Array.from(this.pendingMessages.values());
  }

  /**
   * 清理已确认的消息
   */
  cleanup(): void {
    const now = Date.now();
    const timeout = 5 * 60 * 1000; // 5分钟

    for (const [clientId, message] of this.pendingMessages) {
      if (message.status === 'confirmed' && now - message.createdAt > timeout) {
        this.pendingMessages.delete(clientId);
      }
    }
  }
}
```

### 6.2 消息处理器

```typescript
// sync/message-handler.ts
import type { ConnectionManager } from './connection';
import type { OptimisticUpdateManager } from './optimistic-update';
import type { MessageStore } from '@/stores/message-store';
import type { SyncStore } from '@/stores/sync-store';

export class MessageHandler {
  constructor(
    private connection: ConnectionManager,
    private optimisticManager: OptimisticUpdateManager,
    private messageStore: MessageStore,
    private syncStore: SyncStore
  ) {
    this.setupListeners();
  }

  private setupListeners(): void {
    this.connection.on('message', (msg) => {
      switch (msg.type) {
        case 'ack':
          this.handleAck(msg);
          break;
        case 'stream:start':
          this.handleStreamStart(msg);
          break;
        case 'stream:delta':
          this.handleStreamDelta(msg);
          break;
        case 'stream:end':
          this.handleStreamEnd(msg);
          break;
        case 'stream:truncated':
          this.handleStreamTruncated(msg);
          break;
        case 'error':
          this.handleError(msg);
          break;
      }
    });
  }

  private handleAck(msg: AckMessage): void {
    this.optimisticManager.markSending(msg.clientId);
    this.messageStore.updateMessage(msg.dialogId, msg.clientId, {
      status: 'sending',
      serverId: msg.serverId,
    });
  }

  private handleStreamStart(msg: StreamStartMessage): void {
    this.messageStore.setStreamingMessage(msg.dialogId, msg.messageId);
    this.messageStore.addMessage(msg.dialogId, {
      id: msg.messageId,
      role: msg.role,
      content: '',
      status: 'streaming',
      metadata: msg.metadata,
    });
  }

  private handleStreamDelta(msg: StreamDeltaMessage): void {
    this.messageStore.appendContent(msg.dialogId, msg.messageId, msg.delta);
  }

  private handleStreamEnd(msg: StreamEndMessage): void {
    this.messageStore.updateMessage(msg.dialogId, msg.messageId, {
      content: msg.finalContent,
      status: 'completed',
    });
    this.messageStore.setStreamingMessage(msg.dialogId, null);
  }

  private handleStreamTruncated(msg: StreamTruncatedMessage): void {
    this.messageStore.updateMessage(msg.dialogId, msg.messageId, {
      status: 'truncated',
    });
    this.messageStore.setStreamingMessage(msg.dialogId, null);
  }

  private handleError(msg: ErrorMessage): void {
    if (msg.messageId) {
      this.optimisticManager.markFailed(msg.messageId, new Error(msg.error.message));
      this.messageStore.updateMessage(msg.dialogId!, msg.messageId, {
        status: 'failed',
        error: msg.error,
      });
    }
    this.syncStore.addSyncError({
      code: msg.error.code,
      message: msg.error.message,
      timestamp: Date.now(),
    });
  }
}
```

### 6.3 使用示例

```typescript
// hooks/useSendMessage.ts
import { useCallback } from 'react';
import { useMessageStore } from '@/stores/message-store';
import { useSyncStore } from '@/stores/sync-store';
import { connectionManager } from '@/sync/connection';
import { optimisticManager } from '@/sync/optimistic-update';

export function useSendMessage(dialogId: string) {
  const addMessage = useMessageStore((s) => s.addMessage);
  const connectionStatus = useSyncStore((s) => s.connectionStatus);

  const sendMessage = useCallback(
    async (content: string) => {
      if (connectionStatus !== 'connected') {
        throw new Error('WebSocket not connected');
      }

      // 1. 创建乐观消息
      const optimistic = optimisticManager.create(dialogId, content);

      // 2. 立即显示在 UI
      addMessage(dialogId, {
        id: optimistic.clientId,
        role: 'user',
        content,
        status: 'pending',
        optimisticOrder: optimistic.optimisticOrder,
      });

      // 3. 发送到服务端
      const sent = connectionManager.send({
        type: 'send',
        dialogId,
        clientId: optimistic.clientId,
        content,
        optimisticOrder: optimistic.optimisticOrder,
      });

      if (!sent) {
        optimistic.rollback();
        throw new Error('Failed to send message');
      }

      return optimistic.clientId;
    },
    [dialogId, connectionStatus, addMessage]
  );

  return { sendMessage };
}
```

```typescript
// hooks/useSyncStatus.ts
import { useSyncStore } from '@/stores/sync-store';

export function useSyncStatus() {
  const status = useSyncStore((s) => ({
    connection: s.connectionStatus,
    isSyncing: s.isSyncing,
    pendingCount: s.pendingSyncs,
    hasErrors: s.syncErrors.length > 0,
    errors: s.syncErrors,
  }));

  const actions = useSyncStore((s) => ({
    reconnect: s.reconnect,
    clearErrors: s.clearSyncErrors,
  }));

  return { status, actions };
}
```

## 7. 迁移计划

### 7.1 阶段一：类型统一（1-2 天）

1. 创建 `sync/protocol.ts` 统一协议类型
2. 更新 `types/sync.ts` 导出协议类型
3. 确保前后端类型一致性

### 7.2 阶段二：Store 重构（2-3 天）

1. 创建新的 `dialog-store.ts` 和 `message-store.ts`
2. 实现 `sync-store.ts`
3. 保持 `ui-store.ts` 不变
4. 编写 store 单元测试

### 7.3 阶段三：同步层实现（3-4 天）

1. 实现 `ConnectionManager`
2. 实现 `OptimisticUpdateManager`
3. 实现 `MessageHandler`
4. 集成 IndexedDB 持久化

### 7.4 阶段四：Hooks 重构（2-3 天）

1. 创建新的 `useSendMessage`, `useMessages`, `useSyncStatus`
2. 逐步替换旧 hooks
3. 更新组件使用新 hooks

### 7.5 阶段五：测试与优化（2-3 天）

1. 编写集成测试
2. 性能测试（大量消息场景）
3. 错误场景测试
4. 清理旧代码

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 重构期间功能回退 | 高 | 保持旧代码，逐步替换；每阶段充分测试 |
| 乐观更新冲突 | 中 | 使用乐观序号排序；服务端确认后更新 |
| WebSocket 重连状态丢失 | 高 | 实现完整的重连恢复机制；IndexedDB 持久化 |
| 性能下降 | 中 | 使用选择器避免不必要渲染；虚拟列表 |

## 9. 总结

新架构通过以下方式解决现有问题：

1. **领域划分清晰** - Dialog/Message/Sync/UI 各司其职
2. **单向数据流** - WebSocket → Handler → Store → UI
3. **乐观更新统一** - OptimisticUpdateManager 集中管理
4. **类型安全** - 从协议到 UI 的完整类型链
5. **可测试性** - 各层独立，便于单元测试
