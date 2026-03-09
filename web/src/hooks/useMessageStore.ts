"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { globalEventEmitter } from "@/lib/event-emitter";
import type { ChatMessage, ChatEvent, ChatEventType } from "@/types/openai";
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
  title?: string;
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

function normalizeDialog(
  input: Partial<ChatSession> | null,
): ChatSession | null {
  if (!input || !input.id) return null;
  return {
    id: input.id,
    messages: Array.isArray(input.messages) ? input.messages : [],
    model: input.model,
    created_at:
      typeof input.created_at === "number" ? input.created_at : Date.now(),
    updated_at:
      typeof input.updated_at === "number" ? input.updated_at : Date.now(),
  };
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
      hookStats: null,
      runReport: null,
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
            lastMsg.content =
              (lastMsg.content || "") + (event.message.content || "");
          } else {
            messages.push(event.message);
          }
        } else if (event.type === "message") {
          // 新消息 - 检查是否已存在
          const existingIdx = messages.findIndex(
            (m) =>
              m.role === event.message.role &&
              m.content === event.message.content,
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
          d.id === updatedDialog.id ? updatedDialog : d,
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
    [flushMessages],
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
      dialog: Partial<ChatSession> | null;
    }) => {
      const normalizedDialog = normalizeDialog(event.dialog);
      if (normalizedDialog) {
        setState((prev) => {
          // 检查是否已经有这个对话框
          const existingDialog = prev.dialogs.find(
            (d) => d.id === normalizedDialog.id,
          );

          // 合并消息：保留现有消息，同时添加服务器上的新消息
          let mergedMessages: ChatMessage[] = [];
          if (existingDialog) {
            mergedMessages = [...existingDialog.messages];
            // 添加服务器有但本地没有的消息（通过ID判断）
            normalizedDialog.messages.forEach((serverMsg) => {
              const exists = mergedMessages.some(
                (m) => m.id === serverMsg.id,
              );
              if (!exists) {
                mergedMessages.push(serverMsg);
              }
            });
          } else {
            mergedMessages = normalizedDialog.messages;
          }

          const dialogToUse: ChatSession = {
            ...normalizedDialog,
            messages: mergedMessages,
          };

          const updatedDialogs = prev.dialogs.some(
            (d) => d.id === normalizedDialog.id,
          )
            ? prev.dialogs.map((d) =>
                d.id === normalizedDialog.id ? dialogToUse : d,
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
      // 对于 message_start 事件，如果没有 currentDialog，尝试从 event 创建
      if (!state.currentDialog) {
        if (event.type === "agent:message_start") {
          console.log("[MessageStore] No current dialog, buffering message_start event");
          // 延迟处理这个事件，等待 dialog:subscribed
          setTimeout(() => {
            globalEventEmitter.emit("agent:event", event);
          }, 100);
        } else {
          console.log("[MessageStore] Skipping agent event: no current dialog", event.type);
        }
        return;
      }
      if (event.dialog_id !== state.currentDialog.id) {
        console.log("[MessageStore] Skipping agent event: dialog_id mismatch", {
          event_dialog_id: event.dialog_id,
          current_dialog_id: state.currentDialog.id,
        });
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

            // 检查消息是否已存在，避免重复创建
            const existingMessage = prev.currentDialog?.messages.find(m => m.id === message_id);
            if (existingMessage) {
              console.log("[MessageStore] Message already exists, skipping:", message_id);
              return prev;
            }

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

            // 同时更新消息对象中的 reasoning_content
            const messages = [...(prev.currentDialog?.messages || [])];
            const targetIdx = messages.findIndex((m) => m.id === message_id);
            if (targetIdx >= 0) {
              messages[targetIdx] = {
                ...messages[targetIdx],
                reasoning_content: reasoning_content,
              };
            }

            return {
              ...prev,
              streamState: {
                ...streamState,
                accumulatedReasoning: reasoning_content,
                showReasoning: true,
              },
              currentDialog: prev.currentDialog
                ? { ...prev.currentDialog, messages }
                : null,
            };
          }

          case "agent:tool_call": {
            const { message_id, tool_call } = event.data;
            console.log("[MessageStore] agent:tool_call received:", { message_id, tool_call });
            const newToolCalls = [...streamState.toolCalls, tool_call];

            // 添加 tool_call 消息到消息列表
            const messages = [...(prev.currentDialog?.messages || [])];

            // 更新对应的 assistant 消息的 tool_calls
            const assistantIdx = messages.findIndex((m) => m.id === message_id);
            if (assistantIdx >= 0) {
              console.log("[MessageStore] Updating assistant message at index:", assistantIdx);
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

          case "agent:tool_result": {
            const { tool_call_id, tool_name, result } = event.data;
            console.log("[MessageStore] agent:tool_result received:", { tool_call_id, tool_name, result });

            // 创建工具结果消息
            const toolResultMessage: ChatMessage = {
              id: `tool_result_${Date.now()}`,
              role: "tool",
              content: typeof result === "string" ? result : JSON.stringify(result, null, 2),
              tool_call_id: tool_call_id,
              name: tool_name,
            };

            // 添加到消息列表
            const messages = [...(prev.currentDialog?.messages || []), toolResultMessage];

            return {
              ...prev,
              currentDialog: prev.currentDialog
                ? { ...prev.currentDialog, messages, updated_at: Date.now() }
                : null,
            };
          }

          case "agent:message_complete": {
            const { message_id, content, reasoning_content, tool_calls } =
              event.data;

            // 清理流式缓存
            delete streamingMessagesRef.current[message_id];

            // 使用 message_id 找到并更新对应的消息
            const messages = [...(prev.currentDialog?.messages || [])];
            const targetIdx = messages.findIndex((m) => m.id === message_id);

            if (targetIdx >= 0) {
              const nextContent = content || messages[targetIdx].content || "";
              const nextToolCalls =
                tool_calls || messages[targetIdx].tool_calls;
              const nextReasoningContent = reasoning_content || messages[targetIdx].reasoning_content;

              messages[targetIdx] = {
                ...messages[targetIdx],
                content: nextContent,
                tool_calls: nextToolCalls,
                reasoning_content: nextReasoningContent,
              };

              // 清理仅由 message_start 产生的空 assistant 占位，避免 UI 出现“(无内容)”噪音。
              const hasContent = (nextContent || "").trim().length > 0;
              const hasToolCalls =
                Array.isArray(nextToolCalls) && nextToolCalls.length > 0;
              if (!hasContent && !hasToolCalls) {
                messages.splice(targetIdx, 1);
              }
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
                hookStats: streamState.hookStats,
                runReport: streamState.runReport,
              },
              currentDialog: prev.currentDialog
                ? { ...prev.currentDialog, messages, updated_at: Date.now() }
                : null,
            };
          }

          case "agent:run_summary": {
            return {
              ...prev,
              streamState: {
                ...streamState,
                hookStats: event.data.hook_stats,
                runReport: {
                  result: event.data.result,
                  hook_stats: event.data.hook_stats,
                  messages: event.data.messages,
                },
              },
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
      handleChatEvent,
    );
    const unsubscribeDialog = globalEventEmitter.on(
      "dialog:subscribed",
      handleDialogSubscribed,
    );
    const unsubscribeAgent = globalEventEmitter.on(
      "agent:event",
      handleAgentEvent,
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

  // 重置并设置新对话框（用于新建对话）
  const resetAndSetDialog = useCallback((dialog: ChatSession | null) => {
    setState((prev) => {
      if (!dialog) {
        return {
          ...prev,
          currentDialog: null,
          streamState: {
            isStreaming: false,
            currentMessageId: null,
            accumulatedContent: "",
            accumulatedReasoning: "",
            toolCalls: [],
            showReasoning: false,
            hookStats: null,
            runReport: null,
          },
        };
      }

      // 先把当前对话框保存到历史列表（如果存在且不在列表中）
      let updatedDialogs = [...prev.dialogs];
      if (prev.currentDialog && !updatedDialogs.some((d) => d.id === prev.currentDialog!.id)) {
        updatedDialogs.push(prev.currentDialog);
      }

      // 确保新对话框在历史列表中
      if (!updatedDialogs.some((d) => d.id === dialog.id)) {
        updatedDialogs.push(dialog);
      } else {
        // 更新已存在的对话框
        updatedDialogs = updatedDialogs.map((d) => (d.id === dialog.id ? dialog : d));
      }

      return {
        ...prev,
        currentDialog: dialog,
        dialogs: updatedDialogs,
        streamState: {
          isStreaming: false,
          currentMessageId: null,
          accumulatedContent: "",
          accumulatedReasoning: "",
          toolCalls: [],
          showReasoning: false,
          hookStats: null,
          runReport: null,
        },
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
          d.id === updatedDialog.id ? updatedDialog : d,
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
            m.content === parentContent,
        ) || []
      );
    },
    [state.currentDialog],
  );

  // 获取工具结果
  const getToolResults = useCallback(
    (toolCallId: string) => {
      return (
        state.currentDialog?.messages.filter(
          (m) => m.role === "tool" && m.tool_call_id === toolCallId,
        ) || []
      );
    },
    [state.currentDialog],
  );

  return {
    ...state,
    setCurrentDialog,
    resetAndSetDialog,
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
