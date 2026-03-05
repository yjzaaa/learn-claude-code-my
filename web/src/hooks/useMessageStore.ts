"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { globalEventEmitter } from "@/lib/event-emitter";
import type {
  RealtimeMessage,
  DialogSession,
  StreamTokenMessage,
  MessageAddedEvent,
  MessageUpdatedEvent,
  MessageStatus,
} from "@/types/realtime-message";

interface MessageStoreState {
  dialogs: DialogSession[];
  currentDialog: DialogSession | null;
  isLoading: boolean;
  error: string | null;
}

export function useMessageStore() {
  const [state, setState] = useState<MessageStoreState>({
    dialogs: [],
    currentDialog: null,
    isLoading: false,
    error: null,
  });

  const messageBufferRef = useRef<RealtimeMessage[]>([]);
  const flushTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 批量更新消息
  const flushMessages = useCallback(() => {
    if (messageBufferRef.current.length === 0) return;

    const messages = [...messageBufferRef.current];
    messageBufferRef.current = [];

    setState((prev) => {
      if (!prev.currentDialog) return prev;

      const updatedMessages = [...prev.currentDialog.messages, ...messages];
      const updatedDialog = {
        ...prev.currentDialog,
        messages: updatedMessages,
        updated_at: new Date().toISOString(),
      };

      return {
        ...prev,
        currentDialog: updatedDialog,
        dialogs: prev.dialogs.map((d) =>
          d.id === updatedDialog.id ? updatedDialog : d
        ),
      };
    });
  }, []);

  // 缓冲添加消息
  const bufferMessage = useCallback((message: RealtimeMessage) => {
    messageBufferRef.current.push(message);

    // 立即刷新流式token，缓冲其他消息
    if (message.type === "stream_token") {
      flushMessages();
    } else if (!flushTimerRef.current) {
      flushTimerRef.current = setTimeout(() => {
        flushMessages();
        flushTimerRef.current = null;
      }, 50);
    }
  }, [flushMessages]);

  // 监听WebSocket事件
  useEffect(() => {
    console.log("[MessageStore] Setting up event listeners");

    const handleMessageAdded = (event: MessageAddedEvent) => {
      console.log("[MessageStore] Message added:", {
        id: event.message.id,
        type: event.message.type,
        parent_id: event.message.parent_id,
        content: event.message.content?.slice(0, 50)
      });
      bufferMessage(event.message);
    };

    const handleMessageUpdated = (event: MessageUpdatedEvent) => {
      setState((prev) => {
        if (!prev.currentDialog || prev.currentDialog.id !== event.dialog_id) {
          return prev;
        }

        const updatedMessages = prev.currentDialog.messages.map((msg) =>
          msg.id === event.message.id ? event.message : msg
        );

        const updatedDialog = {
          ...prev.currentDialog,
          messages: updatedMessages,
          updated_at: new Date().toISOString(),
        };

        return {
          ...prev,
          currentDialog: updatedDialog,
          dialogs: prev.dialogs.map((d) =>
            d.id === updatedDialog.id ? updatedDialog : d
          ),
        };
      });
    };

    const handleStreamToken = (event: StreamTokenMessage) => {
      setState((prev) => {
        if (!prev.currentDialog || prev.currentDialog.id !== event.dialog_id) {
          return prev;
        }

        const updatedMessages = prev.currentDialog.messages.map((msg) => {
          if (msg.id === event.message_id) {
            return {
              ...msg,
              content: event.current_content,
              stream_tokens: [...(msg.stream_tokens || []), event.token],
              status: "streaming" as MessageStatus,
            };
          }
          return msg;
        });

        const updatedDialog = {
          ...prev.currentDialog,
          messages: updatedMessages,
          updated_at: new Date().toISOString(),
        };

        return {
          ...prev,
          currentDialog: updatedDialog,
        };
      });
    };

    const handleDialogSubscribed = (event: { dialog: DialogSession | null }) => {
      if (event.dialog) {
        setState((prev) => {
          // 检查是否已经有这个对话框
          const existingDialog = prev.dialogs.find((d) => d.id === event.dialog!.id);
          
          // 合并消息：保留现有消息，同时添加服务器上的新消息
          let mergedMessages: RealtimeMessage[] = [];
          if (existingDialog) {
            // 创建现有消息的映射
            const existingMsgMap = new Map(existingDialog.messages.map(m => [m.id, m]));
            // 遍历服务器消息，保留前端有stream_tokens的版本
            mergedMessages = event.dialog!.messages.map(serverMsg => {
              const existingMsg = existingMsgMap.get(serverMsg.id);
              if (existingMsg && existingMsg.stream_tokens && existingMsg.stream_tokens.length > 0) {
                // 前端有更完整的流式数据，保留前端版本
                return existingMsg;
              }
              return serverMsg;
            });
            // 添加前端有但服务器没有的消息（本地乐观更新）
            const serverMsgIds = new Set(event.dialog!.messages.map(m => m.id));
            existingDialog.messages.forEach(localMsg => {
              if (!serverMsgIds.has(localMsg.id)) {
                mergedMessages.push(localMsg);
              }
            });
          } else {
            mergedMessages = event.dialog!.messages;
          }

          const dialogToUse: DialogSession = {
            ...event.dialog,
            messages: mergedMessages,
          } as DialogSession;

          const updatedDialogs = prev.dialogs.some((d) => d.id === event.dialog!.id)
            ? prev.dialogs.map((d) =>
                d.id === event.dialog!.id ? dialogToUse : d
              )
            : [...prev.dialogs, dialogToUse];

          return {
            ...prev,
            currentDialog: dialogToUse,
            dialogs: updatedDialogs,
          };
        });
      }
    };

    const unsubscribeAdded = globalEventEmitter.on(
      "message:added",
      handleMessageAdded
    );
    const unsubscribeUpdated = globalEventEmitter.on(
      "message:updated",
      handleMessageUpdated
    );
    const unsubscribeStream = globalEventEmitter.on(
      "stream:token",
      handleStreamToken
    );
    const unsubscribeDialog = globalEventEmitter.on(
      "dialog:subscribed",
      handleDialogSubscribed
    );

    return () => {
      unsubscribeAdded();
      unsubscribeUpdated();
      unsubscribeStream();
      unsubscribeDialog();
    };
  }, [bufferMessage]);

  // 设置当前对话框
  const setCurrentDialog = useCallback((dialog: DialogSession | null) => {
    setState((prev) => {
      if (!dialog) {
        return {
          ...prev,
          currentDialog: null,
        };
      }

      // 检查是否已存在此对话框
      const existingDialog = prev.dialogs.find((d) => d.id === dialog.id);
      
      // 如果已存在，合并消息；否则使用新对话框
      const dialogToSet = existingDialog
        ? { ...dialog, messages: existingDialog.messages }
        : dialog;

      // 如果对话框不在列表中，添加它
      const updatedDialogs = prev.dialogs.some((d) => d.id === dialog.id)
        ? prev.dialogs.map((d) => (d.id === dialog.id ? dialogToSet : d))
        : [...prev.dialogs, dialogToSet];

      return {
        ...prev,
        currentDialog: dialogToSet,
        dialogs: updatedDialogs,
      };
    });
  }, []);

  // 添加本地消息
  const addLocalMessage = useCallback((message: RealtimeMessage) => {
    setState((prev) => {
      if (!prev.currentDialog) return prev;

      const updatedDialog = {
        ...prev.currentDialog,
        messages: [...prev.currentDialog.messages, message],
        updated_at: new Date().toISOString(),
      };

      return {
        ...prev,
        currentDialog: updatedDialog,
        dialogs: prev.dialogs.map((d) =>
          d.id === updatedDialog.id ? updatedDialog : d
        ),
      };
    });
  }, []);

  // 更新消息状态
  const updateMessageStatus = useCallback(
    (messageId: string, status: MessageStatus) => {
      setState((prev) => {
        if (!prev.currentDialog) return prev;

        const updatedMessages = prev.currentDialog.messages.map((msg) =>
          msg.id === messageId ? { ...msg, status } : msg
        );

        const updatedDialog = {
          ...prev.currentDialog,
          messages: updatedMessages,
        };

        return {
          ...prev,
          currentDialog: updatedDialog,
        };
      });
    },
    []
  );

  // 获取流式消息的内容
  const getStreamingContent = useCallback(
    (messageId: string) => {
      const message = state.currentDialog?.messages.find(
        (m) => m.id === messageId
      );
      return message?.content || "";
    },
    [state.currentDialog]
  );

  // 获取思考消息
  const getThinkingMessages = useCallback(
    (parentId: string) => {
      return (
        state.currentDialog?.messages.filter(
          (m) => m.type === "assistant_thinking" && m.parent_id === parentId
        ) || []
      );
    },
    [state.currentDialog]
  );

  // 获取工具调用
  const getToolCalls = useCallback(
    (parentId: string) => {
      return (
        state.currentDialog?.messages.filter(
          (m) => m.type === "tool_call" && m.parent_id === parentId
        ) || []
      );
    },
    [state.currentDialog]
  );

  // 获取工具结果
  const getToolResults = useCallback(
    (toolCallId: string) => {
      return (
        state.currentDialog?.messages.filter(
          (m) => m.type === "tool_result" && m.parent_id === toolCallId
        ) || []
      );
    },
    [state.currentDialog]
  );

  return {
    ...state,
    setCurrentDialog,
    addLocalMessage,
    updateMessageStatus,
    getStreamingContent,
    getThinkingMessages,
    getToolCalls,
    getToolResults,
    messages: state.currentDialog?.messages || [],
  };
}
