/**
 * Dialog Store - 对话状态管理
 * 管理对话列表、当前对话、消息等
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  metadata?: {
    toolName?: string;
    toolResult?: unknown;
    isError?: boolean;
    thinkingLevel?: 'none' | 'brief' | 'full';
  };
}

export interface Dialog {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
  metadata?: {
    model?: string;
    thinkingLevel?: 'none' | 'brief' | 'full';
  };
}

interface DialogState {
  // 对话列表
  dialogs: Dialog[];
  
  // 当前活跃对话
  currentDialogId: string | null;
  
  // 加载状态
  isLoading: boolean;
  isStreaming: boolean;
  
  // Actions
  setDialogs: (dialogs: Dialog[]) => void;
  addDialog: (dialog: Dialog) => void;
  removeDialog: (id: string) => void;
  setCurrentDialog: (id: string | null) => void;
  
  // 消息操作
  addMessage: (dialogId: string, message: Message) => void;
  updateMessage: (dialogId: string, messageId: string, updates: Partial<Message>) => void;
  removeMessage: (dialogId: string, messageId: string) => void;
  clearMessages: (dialogId: string) => void;
  
  // 流式消息处理
  appendStreamingContent: (dialogId: string, content: string) => void;
  setStreaming: (streaming: boolean) => void;
  
  // 更新对话标题
  updateDialogTitle: (id: string, title: string) => void;
}

export const useDialogStore = create<DialogState>()(
  immer((set) => ({
    dialogs: [],
    currentDialogId: null,
    isLoading: false,
    isStreaming: false,

    setDialogs: (dialogs) => set({ dialogs }),
    
    addDialog: (dialog) =>
      set((state) => {
        state.dialogs.unshift(dialog);
        state.currentDialogId = dialog.id;
      }),
    
    removeDialog: (id) =>
      set((state) => {
        state.dialogs = state.dialogs.filter((d: Dialog) => d.id !== id);
        if (state.currentDialogId === id) {
          state.currentDialogId = state.dialogs[0]?.id ?? null;
        }
      }),
    
    setCurrentDialog: (id) => set({ currentDialogId: id }),
    
    addMessage: (dialogId, message) =>
      set((state) => {
        const dialog = state.dialogs.find((d: Dialog) => d.id === dialogId);
        if (dialog) {
          dialog.messages.push(message);
          dialog.updatedAt = new Date().toISOString();
        }
      }),

    updateMessage: (dialogId, messageId, updates) =>
      set((state) => {
        const dialog = state.dialogs.find((d: Dialog) => d.id === dialogId);
        const message = dialog?.messages.find((m: Message) => m.id === messageId);
        if (message) {
          Object.assign(message, updates);
        }
      }),

    removeMessage: (dialogId, messageId) =>
      set((state) => {
        const dialog = state.dialogs.find((d: Dialog) => d.id === dialogId);
        if (dialog) {
          dialog.messages = dialog.messages.filter((m: Message) => m.id !== messageId);
        }
      }),

    clearMessages: (dialogId) =>
      set((state) => {
        const dialog = state.dialogs.find((d: Dialog) => d.id === dialogId);
        if (dialog) {
          dialog.messages = [];
        }
      }),

    appendStreamingContent: (dialogId, content) =>
      set((state) => {
        const dialog = state.dialogs.find((d: Dialog) => d.id === dialogId);
        if (dialog) {
          const lastMessage = dialog.messages[dialog.messages.length - 1];
          if (lastMessage?.role === 'assistant') {
            lastMessage.content += content;
          }
        }
      }),

    setStreaming: (streaming) => set({ isStreaming: streaming }),

    updateDialogTitle: (id, title) =>
      set((state) => {
        const dialog = state.dialogs.find((d: Dialog) => d.id === id);
        if (dialog) {
          dialog.title = title;
        }
      }),
  }))
);
