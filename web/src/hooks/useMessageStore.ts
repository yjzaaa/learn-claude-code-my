"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { globalEventEmitter } from "@/lib/event-emitter";
import type {
  ChatMessage,
  ChatEvent,
  ChatEventType,
} from "@/types/openai";
import type { AgentEvent, AgentStreamState } from "@/types/agent-event";

interface MessageStoreState {
  dialogs: ChatSession[];
  currentDialog: ChatSession | null;
  isLoading: boolean;
  error: string | null;
  /** Agent 流式状态 */
  streamState: AgentStreamState;
}

interface ChatSession {
  id: string;
  messages: ChatMessage[];
  model?: string;
  created_at: number;
  updated_at: number;
}

/** 流式消息映射 (message_id -> 累积内容) */
/** 流式消息映射 (message_id -> 累积内容) */
interface StreamingMessages {
  [messageId: string]: {
    content: string;
    reasoning?: string;
    toolCalls?: unknown[];
    agentName?: string;
  };
}

interface ChatEventPayload {
  type: ChatEventType;
  dialog_id: string;
  message: ChatMessage;
  timestamp: number;
}

export function useMessageStore() {
  const [state, setState] = useState<MessageStoreState>({
    dialogs: [],
    currentDialog: null,
    isLoading: false,
    error: null,
    streamState: {
      isStreaming: false,
      currentMessageId: null,
      accumulatedContent: "",
      accumulatedReasoning: "",
      toolCalls: [],
      showReasoning: false,
    },
  });

  const messageBufferRef = useRef<ChatEventPayload[]>([]);
  const flushTimerRef = useRef<NodeJS.Timeout | null>(null);
  // 流式消息缓存
  const streamingMessagesRef = useRef<StreamingMessages>({});

  // 批量更新消息
  const flushMessages = useCallback(() => {
    if (messageBufferRef.current.length === 0) return;

    const events = [...messageBufferRef.current];
    messageBufferRef.current = [];

    setState((prev) => {
      if (!prev.currentDialog) return prev;

      // 按消息角色和类型合并
      const messages = [...prev.currentDialog.messages];

      events.forEach((event) => {
        if (event.type === "delta") {
          // 流式增量 - 追加到最后一条 assistant 消息
          const lastMsg = messages[messages.length - 1];
          if (lastMsg && lastMsg.role === "assistant") {
            lastMsg.content = (lastMsg.content || "") + (event.message.content || "");
          } else {
            messages.push(event.message);
          }
        } else if (event.type === "message") {
          // 新消息 - 检查是否已存在
          const existingIdx = messages.findIndex(
            (m) => m.role === event.message.role && m.content === event.message.content
          );
          if (existingIdx === -1) {
            messages.push(event.message);
          }
        } else {
          // 其他类型直接添加
          messages.push(event.message);
        }
      });

      const updatedDialog = {
        ...prev.currentDialog,
        messages,
        updated_at: Date.now(),
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

  // 缓冲添加事件
  const bufferEvent = useCallback(
    (event: ChatEventPayload) => {
      messageBufferRef.current.push(event);

      // 立即刷新流式增量，缓冲其他消息
      if (event.type === "delta") {
        flushMessages();
      } else if (!flushTimerRef.current) {
        flushTimerRef.current = setTimeout(() => {
          flushMessages();
          flushTimerRef.current = null;
        }, 50);
      }
    },
    [flushMessages]
  );

  // 监听WebSocket事件
  useEffect(() => {
    console.log("[MessageStore] Setting up event listeners");

    const handleChatEvent = (event: ChatEventPayload) => {
      if (!state.currentDialog || event.dialog_id !== state.currentDialog.id) {
        return;
      }

      console.log("[MessageStore] Chat event received:", {
        type: event.type,
        role: event.message.role,
        content: event.message.content?.slice(0, 50),
      });

      bufferEvent(event);
    };

    const handleDialogSubscribed = (event: {
      dialog_id: string;
      dialog: ChatSession | null;
    }) => {
      if (event.dialog) {
        setState((prev) => {
          // 检查是否已经有这个对话框
          const existingDialog = prev.dialogs.find(
            (d) => d.id === event.dialog!.id
          );

          // 合并消息：保留现有消息，同时添加服务器上的新消息
          let mergedMessages: ChatMessage[] = [];
          if (existingDialog) {
            mergedMessages = [...existingDialog.messages];
            // 添加服务器有但本地没有的消息
            event.dialog!.messages.forEach((serverMsg) => {
              const exists = mergedMessages.some(
                (m) =>
                  m.role === serverMsg.role &&
                  m.content === serverMsg.content
              );
              if (!exists) {
                mergedMessages.push(serverMsg);
              }
            });
          } else {
            mergedMessages = event.dialog!.messages;
          }

          const dialogToUse: ChatSession = {
            ...event.dialog,
            messages: mergedMessages,
          };

          const updatedDialogs = prev.dialogs.some(
            (d) => d.id === event.dialog!.id
          )
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

    // Agent 流式事件处理
    const handleAgentEvent = (event: AgentEvent) => {
      if (!state.currentDialog || event.dialog_id !== state.currentDialog.id) {
        return;
      }

      console.log("[MessageStore] Agent event received:", {
        type: event.type,
        dialog_id: event.dialog_id,
      });

      setState((prev) => {
        const { streamState } = prev;

        switch (event.type) {
          case "agent:message_start": {
            const { message_id, role, agent_name } = event.data;
            streamingMessagesRef.current[message_id] = {
              content: "",
              agentName: agent_name || "TeamLeadAgent",
            };

            // 添加新的流式消息占位
            const newMessage: ChatMessage = {
              id: message_id,
              role: "assistant",
              content: "",
              agent_name: agent_name || "TeamLeadAgent",
            };

            return {
              ...prev,
              streamState: {
                ...streamState,
                isStreaming: true,
                currentMessageId: message_id,
                accumulatedContent: "",
                accumulatedReasoning: "",
                toolCalls: [],
              },
              currentDialog: prev.currentDialog
                ? {
                    ...prev.currentDialog,
                    messages: [...prev.currentDialog.messages, newMessage],
                  }
                : null,
            };
          }

          case "agent:content_delta": {
            const { message_id, delta, content } = event.data;
            streamingMessagesRef.current[message_id] = {
              ...streamingMessagesRef.current[message_id],
              content,
            };

            // 使用 message_id 找到并更新对应的消息
            const messages = [...(prev.currentDialog?.messages || [])];
            const targetIdx = messages.findIndex((m) => m.id === message_id);

            if (targetIdx >= 0) {
              // 更新已有消息
              messages[targetIdx] = {
                ...messages[targetIdx],
                content,
              };
            }

            return {
              ...prev,
              streamState: {
                ...streamState,
                accumulatedContent: content,
              },
              currentDialog: prev.currentDialog
                ? { ...prev.currentDialog, messages }
                : null,
            };
          }

          case "agent:reasoning_delta": {
            const { message_id, delta, reasoning_content } = event.data;
            const currentMsg = streamingMessagesRef.current[message_id];
            if (currentMsg) {
              currentMsg.reasoning = reasoning_content;
            }
            return {
              ...prev,
              streamState: {
                ...streamState,
                accumulatedReasoning: reasoning_content,
                showReasoning: true,
              },
            };
          }

          case "agent:tool_call": {
            const { message_id, tool_call } = event.data;
            const newToolCalls = [...streamState.toolCalls, tool_call];

            // 添加 tool_call 消息到消息列表
            const messages = [...(prev.currentDialog?.messages || [])];

            // 更新对应的 assistant 消息的 tool_calls
            const assistantIdx = messages.findIndex((m) => m.id === message_id);
            if (assistantIdx >= 0) {
              messages[assistantIdx] = {
                ...messages[assistantIdx],
                tool_calls: newToolCalls,
              };
            }

            return {
              ...prev,
              streamState: {
                ...streamState,
                toolCalls: newToolCalls,
              },
              currentDialog: prev.currentDialog
                ? { ...prev.currentDialog, messages }
                : null,
            };
          }

          case "agent:message_complete": {
            const { message_id, content, reasoning_content, tool_calls } = event.data;

            // 清理流式缓存
            delete streamingMessagesRef.current[message_id];

            // 使用 message_id 找到并更新对应的消息
            const messages = [...(prev.currentDialog?.messages || [])];
            const targetIdx = messages.findIndex((m) => m.id === message_id);

            if (targetIdx >= 0) {
              messages[targetIdx] = {
                ...messages[targetIdx],
                content: content || messages[targetIdx].content,
                tool_calls: tool_calls || messages[targetIdx].tool_calls,
              };
            }

            return {
              ...prev,
              streamState: {
                isStreaming: false,
                currentMessageId: null,
                accumulatedContent: "",
                accumulatedReasoning: "",
                toolCalls: [],
                showReasoning: !!reasoning_content,
              },
              currentDialog: prev.currentDialog
                ? { ...prev.currentDialog, messages, updated_at: Date.now() }
                : null,
            };
          }

          case "agent:error": {
            const { error } = event.data;
            return {
              ...prev,
              error,
              streamState: {
                ...streamState,
                isStreaming: false,
              },
            };
          }

          case "agent:stopped": {
            return {
              ...prev,
              streamState: {
                ...streamState,
                isStreaming: false,
              },
            };
          }

          default:
            return prev;
        }
      });
    };

    const unsubscribeChat = globalEventEmitter.on(
      "chat:event",
      handleChatEvent
    );
    const unsubscribeDialog = globalEventEmitter.on(
      "dialog:subscribed",
      handleDialogSubscribed
    );
    const unsubscribeAgent = globalEventEmitter.on(
      "agent:event",
      handleAgentEvent
    );

    return () => {
      unsubscribeChat();
      unsubscribeDialog();
      unsubscribeAgent();
    };
  }, [bufferEvent, state.currentDialog]);

  // 设置当前对话框
  const setCurrentDialog = useCallback((dialog: ChatSession | null) => {
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
  const addLocalMessage = useCallback((message: ChatMessage) => {
    setState((prev) => {
      if (!prev.currentDialog) return prev;

      const updatedDialog = {
        ...prev.currentDialog,
        messages: [...prev.currentDialog.messages, message],
        updated_at: Date.now(),
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

  // 获取工具调用
  const getToolCalls = useCallback(
    (parentContent: string) => {
      return (
        state.currentDialog?.messages.filter(
          (m) =>
            m.role === "assistant" &&
            m.tool_calls &&
            m.tool_calls.length > 0 &&
            m.content === parentContent
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
          (m) => m.role === "tool" && m.tool_call_id === toolCallId
        ) || []
      );
    },
    [state.currentDialog]
  );

  return {
    ...state,
    setCurrentDialog,
    addLocalMessage,
    getToolCalls,
    getToolResults,
    messages: state.currentDialog?.messages || [],
    /** 当前流式消息内容 */
    streamingContent: state.streamState.accumulatedContent,
    /** 当前推理内容 */
    streamingReasoning: state.streamState.accumulatedReasoning,
    /** 是否正在流式输出 */
    isStreaming: state.streamState.isStreaming,
  };
}
