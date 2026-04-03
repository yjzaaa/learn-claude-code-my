/**
 * Dialog Store - 对话领域状态管理
 *
 * 按领域划分状态，管理对话列表和当前对话
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export interface Dialog {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  metadata?: {
    model?: string;
    agentName?: string;
    thinkingLevel?: 'none' | 'brief' | 'full';
  };
}

export interface DialogSummary {
  id: string;
  title: string;
  messageCount: number;
  updatedAt: string;
}

export interface DialogState {
  // 状态
  dialogs: Dialog[];
  currentDialogId: string | null;
  isLoading: boolean;
  error: Error | null;

  // Actions
  setCurrentDialog: (id: string | null) => void;
  setDialogs: (dialogs: Dialog[]) => void;
  addDialog: (dialog: Dialog) => void;
  updateDialog: (id: string, updates: Partial<Dialog>) => void;
  removeDialog: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
}

export const useDialogStore = create<DialogState>()(
  immer((set) => ({
    // 初始状态
    dialogs: [],
    currentDialogId: null,
    isLoading: false,
    error: null,

    // Actions
    setCurrentDialog: (id) =>
      set((state) => {
        state.currentDialogId = id;
      }),

    setDialogs: (dialogs) =>
      set((state) => {
        state.dialogs = dialogs;
      }),

    addDialog: (dialog) =>
      set((state) => {
        state.dialogs.unshift(dialog);
        state.currentDialogId = dialog.id;
      }),

    updateDialog: (id, updates) =>
      set((state) => {
        const dialog = state.dialogs.find((d: Dialog) => d.id === id);
        if (dialog) {
          Object.assign(dialog, updates);
        }
      }),

    removeDialog: (id) =>
      set((state) => {
        state.dialogs = state.dialogs.filter((d: Dialog) => d.id !== id);
        if (state.currentDialogId === id) {
          state.currentDialogId = state.dialogs[0]?.id ?? null;
        }
      }),

    setLoading: (loading) =>
      set((state) => {
        state.isLoading = loading;
      }),

    setError: (error) =>
      set((state) => {
        state.error = error;
      }),
  }))
);

// 选择器
export const selectCurrentDialog = (state: DialogState): Dialog | null => {
  if (!state.currentDialogId) return null;
  return state.dialogs.find((d) => d.id === state.currentDialogId) ?? null;
};

export const selectDialogList = (state: DialogState): DialogSummary[] => {
  return state.dialogs.map((d) => ({
    id: d.id,
    title: d.title,
    messageCount: 0, // 由 message-store 提供
    updatedAt: d.updatedAt,
  }));
};
