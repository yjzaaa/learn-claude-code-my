/**
 * WebSocket Message Handler
 *
 * 处理服务端发送的消息，路由到对应的 store 更新
 */

import { useMessageStore } from '@/stores/message-store';
import { useSyncStore } from '@/stores/sync-store';
import { useDialogStore } from '@/stores/dialog-store';
import type {
  ServerResponse,
  AckMessage,
  StreamStartMessage,
  StreamDeltaMessage,
  StreamEndMessage,
  StreamTruncatedMessage,
  DialogSnapshotMessage,
  ErrorMessage,
  StatusChangeMessage,
} from '@/types/sync';
import type { ConnectionManager } from './connection';
import type { OptimisticUpdateManager } from './optimistic-update';

export class MessageHandler {
  constructor(
    private connection: ConnectionManager,
    private optimisticManager: OptimisticUpdateManager
  ) {
    this.setupListeners();
  }

  private setupListeners(): void {
    this.connection.onMessage((msg) => {
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
        case 'dialog:snapshot':
          this.handleDialogSnapshot(msg);
          break;
        case 'status:change':
          this.handleStatusChange(msg);
          break;
        case 'error':
          this.handleError(msg);
          break;
      }
    });
  }

  private handleAck(msg: AckMessage): void {
    this.optimisticManager.markSending(msg.clientId);
    useSyncStore.getState().startSync();
  }

  private handleStreamStart(msg: StreamStartMessage): void {
    useMessageStore.getState().addMessage(msg.dialogId, {
      id: msg.messageId,
      role: msg.role,
      content: '',
      timestamp: new Date().toISOString(),
      status: 'streaming',
      metadata: msg.metadata,
    });
    useMessageStore.getState().setStreamingMessage(msg.messageId);
  }

  private handleStreamDelta(msg: StreamDeltaMessage): void {
    useMessageStore.getState().appendContent(msg.dialogId, msg.messageId, msg.delta);
  }

  private handleStreamEnd(msg: StreamEndMessage): void {
    useMessageStore.getState().updateMessage(msg.dialogId, msg.messageId, {
      content: msg.finalContent,
      status: 'completed',
    });
    useMessageStore.getState().setStreamingMessage(null);
    useSyncStore.getState().endSync();
    useSyncStore.getState().setLastSyncAt(Date.now());
  }

  private handleStreamTruncated(msg: StreamTruncatedMessage): void {
    useMessageStore.getState().updateMessage(msg.dialogId, msg.messageId, {
      status: 'truncated',
    });
    useMessageStore.getState().setStreamingMessage(null);
    useSyncStore.getState().endSync();
  }

  private handleDialogSnapshot(msg: DialogSnapshotMessage): void {
    const { data } = msg;

    // 更新对话信息
    useDialogStore.getState().updateDialog(msg.dialogId, {
      title: data.title,
      metadata: {
        model: data.metadata.model,
        agentName: data.metadata.agentName,
      },
    });

    // 更新消息列表
    const messages = data.messages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
      status: 'completed' as const,
      metadata: {
        agentName: m.agentName,
      },
    }));

    // 清空旧消息并添加新消息
    useMessageStore.getState().clearMessages(msg.dialogId);
    messages.forEach((m) => {
      useMessageStore.getState().addMessage(msg.dialogId, m);
    });

    // 处理流式消息
    if (data.streamingMessage) {
      const streaming = data.streamingMessage;
      useMessageStore.getState().addMessage(msg.dialogId, {
        id: streaming.id,
        role: streaming.role,
        content: streaming.content,
        timestamp: streaming.timestamp,
        status: 'streaming',
        metadata: {
          agentName: streaming.agentName,
        },
      });
      useMessageStore.getState().setStreamingMessage(streaming.id);
    }
  }

  private handleStatusChange(msg: StatusChangeMessage): void {
    // 可以在这里处理状态变更事件
    console.log(`Dialog ${msg.dialogId} status: ${msg.previous} -> ${msg.current}`);
  }

  private handleError(msg: ErrorMessage): void {
    // 如果有 messageId，标记对应消息失败
    if (msg.messageId && msg.dialogId) {
      this.optimisticManager.markFailed(msg.messageId, new Error(msg.error.message));
      useMessageStore.getState().updateMessage(msg.dialogId, msg.messageId, {
        status: 'failed',
      });
    }

    // 添加同步错误
    useSyncStore.getState().addSyncError({
      code: msg.error.code,
      message: msg.error.message,
      timestamp: Date.now(),
      dialogId: msg.dialogId,
      messageId: msg.messageId,
    });

    useSyncStore.getState().endSync();
  }
}
