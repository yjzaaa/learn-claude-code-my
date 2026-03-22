/**
 * useDialog Hook
 * 对话操作的封装 Hook
 */

import { useCallback, useState } from 'react';
import { useDialogStore, type Message } from '../stores/dialog';
import { api } from '../lib/api';
import { nanoid } from '../lib/utils';

export function useDialog() {
  const store = useDialogStore();
  const [error, setError] = useState<string | null>(null);

  const createDialog = useCallback(async (title?: string) => {
    try {
      setError(null);
      const dialog = await api.createDialog(title);
      store.addDialog(dialog);
      return dialog;
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建对话失败');
      throw err;
    }
  }, [store]);

  const loadDialogs = useCallback(async () => {
    try {
      setError(null);
      const dialogs = await api.listDialogs();
      store.setDialogs(dialogs);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载对话列表失败');
      throw err;
    }
  }, [store]);

  const loadDialog = useCallback(async (id: string) => {
    try {
      setError(null);
      const dialog = await api.getDialog(id);
      // 更新本地存储
      const exists = store.dialogs.find((d) => d.id === id);
      if (exists) {
        store.setDialogs(
          store.dialogs.map((d) => (d.id === id ? dialog : d))
        );
      } else {
        store.addDialog(dialog);
      }
      return dialog;
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载对话失败');
      throw err;
    }
  }, [store]);

  const sendMessage = useCallback(async (
    dialogId: string,
    content: string,
  ) => {
    try {
      setError(null);

      // 添加用户消息（乐观更新）
      const userMessage: Message = {
        id: nanoid(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      store.addMessage(dialogId, userMessage);

      // 触发后端 Agent 任务；流式内容由 WebSocket 推送
      await api.sendMessage(dialogId, content);
    } catch (err) {
      setError(err instanceof Error ? err.message : '发送消息失败');
      throw err;
    }
  }, [store]);

  const deleteDialog = useCallback(async (id: string) => {
    try {
      setError(null);
      await api.deleteDialog(id);
      store.removeDialog(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除对话失败');
      throw err;
    }
  }, [store]);

  return {
    // State
    dialogs: store.dialogs,
    currentDialogId: store.currentDialogId,
    currentDialog: store.dialogs.find((d) => d.id === store.currentDialogId),
    isLoading: store.isLoading,
    isStreaming: store.isStreaming,
    error,

    // Actions
    createDialog,
    loadDialogs,
    loadDialog,
    sendMessage,
    deleteDialog,
    setCurrentDialog: store.setCurrentDialog,
  };
}
