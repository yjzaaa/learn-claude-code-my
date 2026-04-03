/**
 * useDialog Hook
 * 对话操作的封装 Hook
 */

import { useCallback, useState } from 'react';
import { useDialogStore } from '../stores/dialog-store';
import { useMessageStore, type Message } from '../stores/message-store';
import { api } from '../lib/api';
import { nanoid } from '../lib/utils';

export function useDialog() {
  const dialogStore = useDialogStore();
  const messageStore = useMessageStore();
  const [error, setError] = useState<string | null>(null);

  const createDialog = useCallback(async (title?: string) => {
    try {
      setError(null);
      const dialog = await api.createDialog(title);
      dialogStore.addDialog(dialog);
      return dialog;
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建对话失败');
      throw err;
    }
  }, [dialogStore]);

  const loadDialogs = useCallback(async () => {
    try {
      setError(null);
      const dialogs = await api.listDialogs();
      dialogStore.setDialogs(dialogs);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载对话列表失败');
      throw err;
    }
  }, [dialogStore]);

  const loadDialog = useCallback(async (id: string) => {
    try {
      setError(null);
      const dialog = await api.getDialog(id);
      // 更新本地存储
      const exists = dialogStore.dialogs.find((d) => d.id === id);
      if (exists) {
        dialogStore.setDialogs(
          dialogStore.dialogs.map((d) => (d.id === id ? dialog : d))
        );
      } else {
        dialogStore.addDialog(dialog);
      }
      // 加载消息到 message-store
      if (dialog.messages) {
        messageStore.clearMessages(id);
        dialog.messages.forEach((msg) => {
          messageStore.addMessage(id, msg);
        });
      }
      return dialog;
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载对话失败');
      throw err;
    }
  }, [dialogStore, messageStore]);

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
        status: 'sending',
      };
      messageStore.addMessage(dialogId, userMessage);

      // 触发后端 Agent 任务；流式内容由 WebSocket 推送
      await api.sendMessage(dialogId, content);
    } catch (err) {
      setError(err instanceof Error ? err.message : '发送消息失败');
      throw err;
    }
  }, [messageStore]);

  const deleteDialog = useCallback(async (id: string) => {
    try {
      setError(null);
      await api.deleteDialog(id);
      dialogStore.removeDialog(id);
      messageStore.clearMessages(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除对话失败');
      throw err;
    }
  }, [dialogStore, messageStore]);

  // 获取当前对话的消息
  const currentMessages = dialogStore.currentDialogId
    ? messageStore.getMessages(dialogStore.currentDialogId)
    : [];

  return {
    // State
    dialogs: dialogStore.dialogs,
    currentDialogId: dialogStore.currentDialogId,
    currentDialog: dialogStore.dialogs.find((d) => d.id === dialogStore.currentDialogId),
    currentMessages,
    isLoading: dialogStore.isLoading,
    error,

    // Actions
    createDialog,
    loadDialogs,
    loadDialog,
    sendMessage,
    deleteDialog,
    setCurrentDialog: dialogStore.setCurrentDialog,
  };
}
