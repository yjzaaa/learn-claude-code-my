# 前端中心化消息同步 - 技术设计

## 1. 系统架构

### 1.1 职责划分

```
┌────────────────────────────────────────────────────────────────────┐
│                         职责划分矩阵                                │
├─────────────────────┬─────────────────────┬────────────────────────┤
│       职责          │         后端         │         前端           │
├─────────────────────┼─────────────────────┼────────────────────────┤
│ Agent Loop          │ ✓                   │                        │
│ Tool Execution      │ ✓                   │                        │
│ LLM Streaming       │ ✓                   │                        │
│ Runtime Context     │ ✓ (内存，临时)       │                        │
│ Message History     │                     │ ✓ (IndexedDB)          │
│ Dialog CRUD         │                     │ ✓                      │
│ Optimistic UI       │                     │ ✓                      │
│ Conflict Resolution │                     │ ✓                      │
└─────────────────────┴─────────────────────┴────────────────────────┘
```

### 1.2 数据流

```
发送消息:
┌────────┐    ┌──────────┐    ┌──────────────┐    ┌────────────┐
│  User  │───▶│ Frontend │───▶│  WebSocket   │───▶│  Backend   │
└────────┘    └──────────┘    └──────────────┘    └────────────┘
                  │                                   │
                  ▼                                   ▼
            ┌──────────┐                        ┌──────────┐
            │IndexedDB │                        │Agent Loop│
            │(pending) │                        │(stream)  │
            └──────────┘                        └────┬─────┘
                                                     │
接收流式:                                           ▼
┌────────┐    ┌──────────┐    ┌──────────────┐    ┌────────────┐
│  UI    │◀───│ Frontend │◀───│  WebSocket   │◀───│  Backend   │
└────────┘    └──────────┘    └──────────────┘    └────────────┘
                  │
                  ▼
            ┌──────────┬──────────────────────────┐
            │ Zustand  │  WriteBatcher (500ms)    │
            │ (State)  │  ──────────────────────▶ │
            └──────────┘                          ▼
                                            ┌──────────┐
                                            │IndexedDB │
                                            │(persist) │
                                            └──────────┘
```

## 2. IndexedDB Schema

### 2.1 数据库结构 (Dexie.js)

```typescript
// lib/db/schema.ts
import Dexie, { Table } from 'dexie';

export interface LocalMessage {
  // 主键 - 客户端生成CUID
  clientId: string;

  // 对话关联
  dialogId: string;

  // 乐观序号，用于严格排序
  optimisticOrder: number;

  // 消息内容
  role: 'user' | 'assistant' | 'system';
  content: string;

  // 状态
  status: 'pending' | 'sending' | 'streaming' | 'completed' | 'failed' | 'truncated';

  // 时间戳
  clientTimestamp: number;
  serverTimestamp?: number;

  // 流式相关
  chunks?: string[];           // 原始chunks（用于恢复）
  lastPersistedChunk?: number; // 最后检查点位置

  // 元数据
  metadata?: {
    model?: string;
    agentName?: string;
    toolCalls?: ToolCall[];
  };
}

export interface Dialog {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messageCount: number;
  lastMessageAt?: number;
  archived?: boolean;
}

export interface SyncCheckpoint {
  dialogId: string;
  messageId: string;
  chunkIndex: number;
  contentSnapshot: string;
  timestamp: number;
}

export class AgentDB extends Dexie {
  messages!: Table<LocalMessage>;
  dialogs!: Table<Dialog>;
  checkpoints!: Table<SyncCheckpoint>;

  constructor() {
    super('AgentDB');
    this.version(1).stores({
      messages: 'clientId, [dialogId+optimisticOrder], status, clientTimestamp',
      dialogs: 'id, updatedAt, archived',
      checkpoints: '[dialogId+messageId], timestamp',
    });
  }
}

export const db = new AgentDB();
```

### 2.2 索引设计说明

| 索引 | 用途 |
|------|------|
| `clientId` (PK) | 主键，唯一标识 |
| `[dialogId+optimisticOrder]` | 复合索引，按对话排序 |
| `status` | 查询待同步/失败的记录 |
| `clientTimestamp` | 归档旧消息查询 |

## 3. 消息同步协议

### 3.1 WebSocket 消息类型

```typescript
// Client → Server
interface ClientMessage {
  type: 'send' | 'subscribe' | 'stream:resume' | 'sync:request';
}

interface SendMessage extends ClientMessage {
  type: 'send';
  dialogId: string;
  clientId: string;      // 预生成ID
  content: string;
  optimisticOrder: number;
  parentMessageId?: string; // 用于回复
}

interface SubscribeMessage extends ClientMessage {
  type: 'subscribe';
  dialogId: string;
  lastKnownMessageId?: string; // 用于增量同步
}

interface StreamResumeMessage extends ClientMessage {
  type: 'stream:resume';
  dialogId: string;
  messageId: string;
  fromChunk: number;
}

// Server → Client
interface ServerMessage {
  type: 'ack' | 'stream:start' | 'stream:delta' | 'stream:end' |
        'stream:truncated' | 'error' | 'status:change';
  timestamp: number;
}

interface AckMessage extends ServerMessage {
  type: 'ack';
  clientId: string;      // 确认收到
  serverId?: string;     // 可选服务端ID
}

interface StreamDeltaMessage extends ServerMessage {
  type: 'stream:delta';
  dialogId: string;
  messageId: string;
  chunkIndex: number;    // 严格递增序号
  delta: string;
}

interface StreamEndMessage extends ServerMessage {
  type: 'stream:end';
  dialogId: string;
  messageId: string;
  finalContent: string;
  usage?: TokenUsage;
}

interface StreamTruncatedMessage extends ServerMessage {
  type: 'stream:truncated';
  dialogId: string;
  messageId: string;
  reason: 'interrupted' | 'timeout' | 'error';
  lastChunkIndex: number;
}
```

### 3.2 状态机

```
┌─────────────────────────────────────────────────────────────────────┐
│                         消息生命周期状态机                           │
└─────────────────────────────────────────────────────────────────────┘

创建 → pending ─────────────────────────────────────────────────────┐
         │                                                          │
         │ send()                                                   │
         ▼                                                          │
      sending ◄──────────────────────┐                              │
         │                           │                              │
         │ WS ack                    │ retry()                     │
         ▼                           │ (max 3)                      │
      streaming ◄────────────┐       │                              │
         │    │              │       │                              │
         │    │ delta        │       │                              │
         │    │              │       │                              │
         │    ▼              │       │                              │
         │ checkpoint        │       │                              │
         │ (每10 chunk)      │       │                              │
         │                   │       │                              │
         │ complete          │       │                              │
         │    │              │       │                              │
         │    ▼              │       │                              │
         └──► completed ─────┴───────┴──────────────────────────────┤
              │                                                     │
              │ error                                               │
              ▼                                                     │
           failed ──────────────────────────────────────────────────┘
              │
              │ interrupted
              ▼
           truncated
```

## 4. 核心组件设计

### 4.1 WriteBatcher (写入批处理)

```typescript
// lib/sync/WriteBatcher.ts
export class WriteBatcher {
  private buffer = new Map<string, LocalMessage>();
  private timer: number | null = null;
  private readonly BATCH_INTERVAL = 500;
  private readonly BATCH_SIZE = 50;

  add(message: LocalMessage) {
    this.buffer.set(message.clientId, message);

    if (this.buffer.size >= this.BATCH_SIZE) {
      this.flush();
    } else {
      this.scheduleFlush();
    }
  }

  private scheduleFlush() {
    if (this.timer) return;
    this.timer = window.setTimeout(() => this.flush(), this.BATCH_INTERVAL);
  }

  async flush(): Promise<void> {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.buffer.size === 0) return;

    const batch = Array.from(this.buffer.values());
    this.buffer.clear();

    try {
      await db.messages.bulkPut(batch);
      eventBus.emit('persisted', batch.map(m => m.clientId));
    } catch (err) {
      // 失败时放回缓冲区
      batch.forEach(m => this.buffer.set(m.clientId, m));
      throw err;
    }
  }

  // 页面关闭前紧急刷新
  async emergencyFlush(): Promise<void> {
    if (this.buffer.size === 0) return;
    const batch = Array.from(this.buffer.values());
    await db.messages.bulkPut(batch);
  }
}
```

### 4.2 SyncCoordinator (同步协调器)

```typescript
// lib/sync/SyncCoordinator.ts
export class SyncCoordinator {
  private batcher = new WriteBatcher();
  private checkpoints = new Map<string, number>();
  private readonly CHECKPOINT_INTERVAL = 10;

  // 流式更新
  onStreamDelta(
    dialogId: string,
    messageId: string,
    chunk: string,
    chunkIndex: number
  ) {
    const store = useMessageStore.getState();
    const msg = store.getMessage(messageId);
    if (!msg) return;

    // 更新内存状态
    const newContent = msg.content + chunk;
    store.updateMessage(messageId, { content: newContent });

    // 检查点持久化
    if (chunkIndex % this.CHECKPOINT_INTERVAL === 0) {
      this.batcher.add({
        ...msg,
        content: newContent,
        lastPersistedChunk: chunkIndex,
      });
      this.checkpoints.set(messageId, chunkIndex);

      // 保存检查点元数据
      db.checkpoints.put({
        dialogId,
        messageId,
        chunkIndex,
        contentSnapshot: newContent,
        timestamp: Date.now(),
      });
    }
  }

  // 流完成
  async onStreamComplete(messageId: string, finalContent: string) {
    const store = useMessageStore.getState();
    const msg = store.getMessage(messageId);

    const finalMsg: LocalMessage = {
      ...msg,
      content: finalContent,
      status: 'completed',
    };

    // 立即持久化
    await db.messages.put(finalMsg);
    this.checkpoints.delete(messageId);

    // 清理检查点
    await db.checkpoints.delete([msg.dialogId, messageId]);
  }

  // 获取最后检查点
  async getLastCheckpoint(messageId: string): Promise<SyncCheckpoint | null> {
    const cp = await db.checkpoints.get({ messageId } as any);
    return cp || null;
  }
}
```

### 4.3 DisconnectRecovery (断线恢复)

```typescript
// lib/sync/DisconnectRecovery.ts
export class DisconnectRecovery {
  async handleReconnect(dialogId: string, ws: WebSocket) {
    // 1. 获取当前对话的所有streaming状态消息
    const streamingMsgs = await db.messages
      .where({ dialogId, status: 'streaming' })
      .toArray();

    for (const msg of streamingMsgs) {
      const checkpoint = await db.checkpoints
        .get([dialogId, msg.clientId]);

      if (checkpoint && checkpoint.chunkIndex > 0) {
        // 尝试恢复流
        ws.send(JSON.stringify({
          type: 'stream:resume',
          dialogId,
          messageId: msg.clientId,
          fromChunk: checkpoint.chunkIndex,
        }));

        // 设置超时降级
        setTimeout(() => {
          this.markTruncated(msg.clientId);
        }, 5000);
      } else {
        // 无检查点，直接标记截断
        await this.markTruncated(msg.clientId);
      }
    }

    // 2. 重发pending/failed消息
    const pendingMsgs = await db.messages
      .where({ dialogId })
      .filter(m => m.status === 'pending' || m.status === 'failed')
      .toArray();

    for (const msg of pendingMsgs) {
      // 重新入队发送
      syncQueue.add({
        type: 'send',
        clientId: msg.clientId,
        content: msg.content,
        dialogId,
      });
    }
  }

  private async markTruncated(messageId: string) {
    const msg = await db.messages.get(messageId);
    if (!msg) return;

    await db.messages.update(messageId, {
      status: 'truncated',
      content: msg.content + '\n\n[消息因网络中断被截断]',
    });

    // 触发AI自修复
    syncQueue.add({
      type: 'send',
      content: '请继续刚才的回答',
      context: { truncatedMessageId: messageId },
      priority: 0,
    });
  }
}
```

## 5. Hook API

### 5.1 useMessageSync

```typescript
// hooks/useMessageSync.ts
export function useMessageSync(dialogId: string) {
  const coordinator = useRef(new SyncCoordinator());
  const recovery = useRef(new DisconnectRecovery());
  const ws = useWebSocket();

  // 初始化：从IndexedDB加载
  useEffect(() => {
    const init = async () => {
      const messages = await db.messages
        .where({ dialogId })
        .sortBy('optimisticOrder');

      useMessageStore.getState().initMessages(messages);
    };

    init();

    return () => {
      coordinator.current.emergencyFlush();
    };
  }, [dialogId]);

  // WebSocket事件监听
  useEffect(() => {
    if (!ws) return;

    const handlers = {
      'stream:delta': (data: StreamDeltaMessage) => {
        coordinator.current.onStreamDelta(
          data.dialogId,
          data.messageId,
          data.delta,
          data.chunkIndex
        );
      },

      'stream:end': (data: StreamEndMessage) => {
        coordinator.current.onStreamComplete(
          data.messageId,
          data.finalContent
        );
      },

      'stream:truncated': (data: StreamTruncatedMessage) => {
        recovery.current.markTruncated(data.messageId);
      },

      'reconnect': () => {
        recovery.current.handleReconnect(dialogId, ws);
      },
    };

    // 订阅事件...

    return () => {
      // 取消订阅...
    };
  }, [ws, dialogId]);

  const sendMessage = useCallback(async (content: string) => {
    const clientId = generateCUID();
    const optimisticOrder = Date.now();

    // 乐观更新
    const optimisticMsg: LocalMessage = {
      clientId,
      dialogId,
      optimisticOrder,
      role: 'user',
      content,
      status: 'pending',
      clientTimestamp: Date.now(),
    };

    useMessageStore.getState().addMessage(optimisticMsg);
    await db.messages.put(optimisticMsg);

    // 发送
    ws?.send(JSON.stringify({
      type: 'send',
      dialogId,
      clientId,
      content,
      optimisticOrder,
    }));

    // 更新状态
    useMessageStore.getState().updateMessage(clientId, {
      status: 'sending',
    });

  }, [ws, dialogId]);

  return { sendMessage };
}
```

## 6. 后端适配

### 6.1 WebSocket Handler 调整

```python
# 后端伪代码
async def handle_send(ws, data: SendMessage):
    # 1. 认可客户端ID
    await ws.send_json(AckMessage(
        client_id=data.client_id,
        server_id=None,  # 使用client_id
    ))

    # 2. 启动Agent Loop（临时状态）
    stream = await agent_engine.send_message(
        dialog_id=data.dialog_id,
        content=data.content,
        message_id=data.client_id,  # 使用客户端ID
    )

    # 3. 流式返回，带序号
    chunk_index = 0
    async for chunk in stream:
        await ws.send_json(StreamDeltaMessage(
            message_id=data.client_id,
            chunk_index=chunk_index,
            delta=chunk,
        ))
        chunk_index += 1

    # 4. 完成
    await ws.send_json(StreamEndMessage(
        message_id=data.client_id,
        final_content=stream.final_content,
    ))

async def handle_resume(ws, data: StreamResumeMessage):
    """尝试恢复流 - 可选实现"""
    # 检查是否有活跃stream
    if data.message_id in active_streams:
        stream = active_streams[data.message_id]
        # 从检查点继续...
    else:
        # 无法恢复，通知前端
        await ws.send_json(StreamTruncatedMessage(
            message_id=data.message_id,
            reason='interrupted',
        ))
```

### 6.2 后端状态边界

| 数据 | 存储位置 | 生命周期 |
|------|---------|---------|
| Active Streams | 内存 | 流结束/30分钟超时 |
| Tool Context | 内存 | 单次调用 |
| LLM Context | 内存 | 单次请求 |
| Checkpoints | 内存 | 流结束 |
| Message History | **不存储** | - |
| Dialog Metadata | **不存储** | - |

## 7. 性能考量

### 7.1 写入性能

| 场景 | 频率 | 优化 |
|------|------|------|
| 流式chunk | 高 | 内存缓冲，500ms批量写入 |
| 检查点 | 中 | 每10chunk持久化 |
| 流完成 | 低 | 立即同步写入 |
| 页面关闭 | 极低 | emergencyFlush |

### 7.2 查询性能

```typescript
// 使用复合索引优化对话消息查询
const messages = await db.messages
  .where('[dialogId+optimisticOrder]')
  .between([dialogId, Dexie.minKey], [dialogId, Dexie.maxKey])
  .toArray();
```

## 8. 测试策略

1. **单元测试**: WriteBatcher, SyncCoordinator
2. **集成测试**: 断线重连、页面刷新恢复
3. **压力测试**: 快速连续发送、大数据流
4. **边界测试**: IndexedDB满、浏览器崩溃
