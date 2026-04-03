/**
 * Message Store - 消息领域状态管理
 *
 * 按 dialogId 分组存储消息，支持乐观更新
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';
export type MessageStatus = 'pending' | 'sending' | 'streaming' | 'completed' | 'failed' | 'truncated';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  status: MessageStatus;
  optimisticOrder?: number;
  metadata?: {
    toolName?: string;
    toolResult?: unknown;
    isError?: boolean;
    thinkingLevel?: 'none' | 'brief' | 'full';
    agentName?: string;
  };
}

export interface PendingMessage {
  clientId: string;
  dialogId: string;
  content: string;
  optimisticOrder: number;
  status: 'pending' | 'sending' | 'confirmed' | 'failed';
  createdAt: number;
}

export interface MessageState {
  // 状态 - 按 dialogId 分组存储
  messagesByDialog: Map<string, Message[]>;
  streamingMessageId: string | null;
  pendingMessages: Map<string, PendingMessage>;

  // Actions
  getMessages: (dialogId: string) => Message[];
  getStreamingMessage: (dialogId: string) => Message | null;
  addMessage: (dialogId: string, message: Message) => void;
  updateMessage: (dialogId: string, messageId: string, updates: Partial<Message>) => void;
  removeMessage: (dialogId: string, messageId: string) => void;
  clearMessages: (dialogId: string) => void;
  setStreamingMessage: (messageId: string | null) => void;
  appendContent: (dialogId: string, messageId: string, delta: string) => void;

  // 乐观更新
  addOptimisticMessage: (dialogId: string, content: string, clientId: string, order: number) => PendingMessage;
  confirmMessage: (clientId: string, serverMessage: Message) => void;
  rollbackMessage: (clientId: string) => void;
  updatePendingStatus: (clientId: string, status: PendingMessage['status']) => void;
}

export const useMessageStore = create<MessageState>()(
  immer((set, get) => ({
    // 初始状态
    messagesByDialog: new Map(),
    streamingMessageId: null,
    pendingMessages: new Map(),

    // 查询方法
    getMessages: (dialogId) => {
      return get().messagesByDialog.get(dialogId) ?? [];
    },

    getStreamingMessage: (dialogId) => {
      const state = get();
      if (!state.streamingMessageId) return null;
      const messages = state.messagesByDialog.get(dialogId) ?? [];
      return messages.find((m) => m.id === state.streamingMessageId) ?? null;
    },

    // Actions
    addMessage: (dialogId, message) =>
      set((state) => {
        if (!state.messagesByDialog.has(dialogId)) {
          state.messagesByDialog.set(dialogId, []);
        }
        const messages = state.messagesByDialog.get(dialogId)!;
        // 避免重复添加
        const exists = messages.some((m: Message) => m.id === message.id);
        if (!exists) {
          messages.push(message);
        }
      }),

    updateMessage: (dialogId, messageId, updates) =>
      set((state) => {
        const messages = state.messagesByDialog.get(dialogId);
        if (messages) {
          const message = messages.find((m: Message) => m.id === messageId);
          if (message) {
            Object.assign(message, updates);
          }
        }
      }),

    removeMessage: (dialogId, messageId) =>
      set((state) => {
        const messages = state.messagesByDialog.get(dialogId);
        if (messages) {
          state.messagesByDialog.set(
            dialogId,
            messages.filter((m: Message) => m.id !== messageId)
          );
        }
      }),

    clearMessages: (dialogId) =>
      set((state) => {
        state.messagesByDialog.set(dialogId, []);
      }),

    setStreamingMessage: (messageId) =>
      set((state) => {
        state.streamingMessageId = messageId;
      }),

    appendContent: (dialogId, messageId, delta) =>
      set((state) => {
        const messages = state.messagesByDialog.get(dialogId);
        if (messages) {
          const message = messages.find((m: Message) => m.id === messageId);
          if (message) {
            message.content += delta;
          }
        }
      }),

    // 乐观更新
    addOptimisticMessage: (dialogId, content, clientId, order) => {
      const pendingMessage: PendingMessage = {
        clientId,
        dialogId,
        content,
        optimisticOrder: order,
        status: 'pending',
        createdAt: Date.now(),
      };

      set((state) => {
        state.pendingMessages.set(clientId, pendingMessage);

        // 立即添加到消息列表
        if (!state.messagesByDialog.has(dialogId)) {
          state.messagesByDialog.set(dialogId, []);
        }
        const messages = state.messagesByDialog.get(dialogId)!;
        messages.push({
          id: clientId,
          role: 'user',
          content,
          timestamp: new Date().toISOString(),
          status: 'pending',
          optimisticOrder: order,
        });
      });

      return pendingMessage;
    },

    confirmMessage: (clientId, serverMessage) =>
      set((state) => {
        // 更新 pending 状态
        const pending = state.pendingMessages.get(clientId);
        if (pending) {
          pending.status = 'confirmed';
        }

        // 替换乐观消息为服务端消息
        const messages = state.messagesByDialog.get(serverMessage.id);
        if (messages) {
          const index = messages.findIndex((m: Message) => m.id === clientId);
          if (index !== -1) {
            messages[index] = serverMessage;
          }
        }

        // 清理 pending
        state.pendingMessages.delete(clientId);
      }),

    rollbackMessage: (clientId) =>
      set((state) => {
        const pending = state.pendingMessages.get(clientId);
        if (pending) {
          // 从消息列表中移除
          const messages = state.messagesByDialog.get(pending.dialogId);
          if (messages) {
            state.messagesByDialog.set(
              pending.dialogId,
              messages.filter((m: Message) => m.id !== clientId)
            );
          }
          state.pendingMessages.delete(clientId);
        }
      }),

    updatePendingStatus: (clientId, status) =>
      set((state) => {
        const pending = state.pendingMessages.get(clientId);
        if (pending) {
          pending.status = status;
        }

        // 同步更新消息列表中的状态
        for (const [dialogId, messages] of state.messagesByDialog) {
          const message = messages.find((m: Message) => m.id === clientId);
          if (message) {
            message.status = status;
            break;
          }
        }
      }),
  }))
);
