"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type {
  DialogSession,
  DialogSummary,
  ServerPushEvent,
  StreamDeltaEvent,
  ToolCallUpdateEvent,
  Message,
  SkillEditApproval,
} from "@/types/dialog";
import type { ChatMessage } from "@/types/openai";
import { globalEventEmitter } from "@/lib/event-emitter";

// 将后端 Message 转换为前端 ChatMessage
function convertToChatMessage(msg: Message): ChatMessage {
  const base: ChatMessage = {
    id: msg.id,
    role: msg.role as any,
    content: msg.content,
    reasoning_content: msg.reasoning_content,
    agent_name: msg.agent_name,
  };

  if (msg.tool_calls && msg.tool_calls.length > 0) {
    base.tool_calls = msg.tool_calls.map((tc) => ({
      id: tc.id,
      type: "function",
      function: {
        name: tc.name,
        arguments: JSON.stringify(tc.arguments),
      },
    }));
  }

  if (msg.role === "tool") {
    base.tool_call_id = msg.tool_call_id;
    base.name = msg.tool_name;
  }

  return base;
}

// WebSocket URL - 优先使用环境变量，否则使用默认值
const WS_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws/client-1"
    : "ws://localhost:8001/ws/client-1";

console.log("[WebSocket] Initializing with URL:", WS_URL);

// 应用增量更新到快照 - 定义在 hook 外部避免重新创建
function applyDelta(
  snapshot: DialogSession | null,
  event: StreamDeltaEvent,
): DialogSession | null {
  if (!snapshot || !snapshot.streaming_message) return snapshot;

  const streaming = snapshot.streaming_message;
  return {
    ...snapshot,
    streaming_message: {
      ...streaming,
      content: streaming.content + (event.delta.content || ""),
      reasoning_content:
        (streaming.reasoning_content || "") + (event.delta.reasoning || ""),
    },
  };
}

// 更新工具调用状态 - 定义在 hook 外部避免重新创建
function updateToolCall(
  snapshot: DialogSession | null,
  event: ToolCallUpdateEvent,
): DialogSession | null {
  if (!snapshot || !snapshot.streaming_message?.tool_calls) return snapshot;

  const streaming = snapshot.streaming_message;
  return {
    ...snapshot,
    streaming_message: {
      ...streaming,
      tool_calls: streaming.tool_calls!.map((t) =>
        t.id === event.tool_call.id ? event.tool_call : t,
      ),
    },
  };
}

interface UseWebSocketReturn {
  /** 当前对话框完整状态快照 */
  currentSnapshot: DialogSession | null;
  /** 历史对话框列表 */
  dialogList: DialogSummary[];
  /** WebSocket 连接状态 */
  isConnected: boolean;
  /** 订阅对话框 */
  subscribeToDialog: (dialogId: string) => void;
  /** 发送用户输入 */
  sendUserInput: (dialogId: string, content: string) => void;
  /** 停止 Agent */
  stopAgent: (dialogId: string) => void;
  /** 获取对话框列表 */
  fetchDialogList: () => Promise<void>;
  /** 创建新对话框 */
  createDialog: (
    title: string,
  ) => Promise<{ success: boolean; data?: DialogSession }>;
  /** skills 修改待审批列表 */
  pendingSkillEdits: SkillEditApproval[];
}

/**
 * WebSocket Hook - 纯状态接收，不管理状态
 *
 * 只接收后端推送的状态快照，通过 setState 更新
 */
export function useWebSocket(): UseWebSocketReturn {
  const [currentSnapshot, setCurrentSnapshot] = useState<DialogSession | null>(
    null,
  );
  const [dialogList, setDialogList] = useState<DialogSummary[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [pendingSkillEdits, setPendingSkillEdits] = useState<
    SkillEditApproval[]
  >([]);
  const currentSnapshotRef = useRef<DialogSession | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  // 跟踪流式消息的累积内容
  const streamingContentRef = useRef<
    Map<string, { content: string; reasoning: string }>
  >(new Map());
  // 跟踪已发送 message_start 的消息 ID，避免重复创建
  const messageStartSentRef = useRef<Set<string>>(new Set());

  // RAF 批处理相关 refs
  const rafScheduledRef = useRef(false);
  const pendingDeltaRef = useRef<StreamDeltaEvent | null>(null);

  // 同步 currentSnapshot 到 ref
  useEffect(() => {
    currentSnapshotRef.current = currentSnapshot;
  }, [currentSnapshot]);

  // RAF 批处理增量更新
  const scheduleDeltaUpdate = useCallback((msg: StreamDeltaEvent) => {
    // 累积 delta 到 pending
    if (pendingDeltaRef.current) {
      // 合并到现有的 pending delta
      pendingDeltaRef.current.delta.content += msg.delta.content || "";
      pendingDeltaRef.current.delta.reasoning += msg.delta.reasoning || "";
    } else {
      // 创建新的 pending delta，确保 content 和 reasoning 不为 undefined
      pendingDeltaRef.current = {
        ...msg,
        delta: {
          content: msg.delta.content || "",
          reasoning: msg.delta.reasoning || "",
        },
      };
    }

    // 如果已经调度了 RAF，不再重复调度
    if (rafScheduledRef.current) return;

    rafScheduledRef.current = true;
    requestAnimationFrame(() => {
      rafScheduledRef.current = false;
      const delta = pendingDeltaRef.current;
      if (!delta) return;

      pendingDeltaRef.current = null;

      // 获取当前累积的内容（已经在 onmessage 中累积好了）
      const currentMsg = streamingContentRef.current.get(delta.message_id) || {
        content: "",
        reasoning: "",
      };

      // 批量更新状态
      setCurrentSnapshot((prev) => applyDelta(prev, delta));

      // 发射事件 - 使用累积后的完整内容，delta 只用于标记本次更新量
      if (delta.delta.content) {
        globalEventEmitter.emit("agent:event", {
          type: "agent:content_delta",
          dialog_id: delta.dialog_id,
          data: {
            message_id: delta.message_id,
            delta: delta.delta.content,
            content: currentMsg.content, // 使用 ref 中已累积的完整内容
          },
        });
      }
      if (delta.delta.reasoning) {
        globalEventEmitter.emit("agent:event", {
          type: "agent:reasoning_delta",
          dialog_id: delta.dialog_id,
          data: {
            message_id: delta.message_id,
            delta: delta.delta.reasoning,
            reasoning_content: currentMsg.reasoning, // 使用 ref 中已累积的完整内容
          },
        });
      }
    });
  }, []);

  // 使用 ref 存储连接函数，避免 useCallback 依赖问题
  const connectRef = useRef<() => void>(() => {});

  // 定义连接函数
  connectRef.current = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      console.log("[WebSocket] Connecting to:", WS_URL);
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WebSocket] Connected");
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg: ServerPushEvent = JSON.parse(event.data);
          console.log("[WebSocket] Received:", msg.type, msg);

          switch (msg.type) {
            case "dialog:snapshot": {
              // 直接替换整个快照
              setCurrentSnapshot(msg.data);
              // 更新历史列表
              setDialogList((prev) => {
                const exists = prev.find((d) => d.id === msg.data.id);
                const summary = {
                  id: msg.data.id,
                  title: msg.data.title,
                  message_count: msg.data.messages.length,
                  updated_at: msg.data.updated_at,
                };
                if (exists) {
                  return prev.map((d) => (d.id === msg.data.id ? summary : d));
                }
                return [...prev, summary];
              });

              // 发射 dialog:subscribed 事件给 useMessageStore
              // 包含 streaming_message（如果存在）
              const allMessages: ChatMessage[] =
                msg.data.messages.map(convertToChatMessage);
              if (msg.data.streaming_message) {
                allMessages.push(
                  convertToChatMessage(msg.data.streaming_message),
                );
              }
              globalEventEmitter.emit("dialog:subscribed", {
                dialog_id: msg.data.id,
                dialog: {
                  id: msg.data.id,
                  title: msg.data.title,
                  messages: allMessages,
                  created_at: Date.parse(msg.data.created_at) || Date.now(),
                  updated_at: Date.parse(msg.data.updated_at) || Date.now(),
                },
              });

              // 如果有流式消息，发射 message_start（只发送一次）
              if (msg.data.streaming_message) {
                const messageId = msg.data.streaming_message.id;
                // 初始化累积内容跟踪
                streamingContentRef.current.set(messageId, {
                  content: msg.data.streaming_message.content || "",
                  reasoning: msg.data.streaming_message.reasoning_content || "",
                });

                // 只在该消息还没有被创建时才发送 message_start
                if (!messageStartSentRef.current.has(messageId)) {
                  messageStartSentRef.current.add(messageId);
                  globalEventEmitter.emit("agent:event", {
                    type: "agent:message_start",
                    dialog_id: msg.data.id,
                    data: {
                      message_id: messageId,
                      role: msg.data.streaming_message.role,
                      agent_name:
                        msg.data.streaming_message.agent_name ||
                        "TeamLeadAgent",
                    },
                  });
                }
              }
              break;
            }

            case "stream:delta": {
              // 兜底：某些情况下 delta 可能早于包含 streaming_message 的 snapshot 到达。
              // 如果还没发过 message_start，这里先补发一次，避免 token 被消息存储层丢弃。
              if (!messageStartSentRef.current.has(msg.message_id)) {
                messageStartSentRef.current.add(msg.message_id);
                globalEventEmitter.emit("agent:event", {
                  type: "agent:message_start",
                  dialog_id: msg.dialog_id,
                  data: {
                    message_id: msg.message_id,
                    role: "assistant",
                    agent_name: "TeamLeadAgent",
                  },
                });
              }

              // 获取或创建当前消息的累积内容
              const currentMsg = streamingContentRef.current.get(
                msg.message_id,
              ) || { content: "", reasoning: "" };

              // 累积内容
              if (msg.delta.content) {
                currentMsg.content += msg.delta.content;
              }
              if (msg.delta.reasoning) {
                currentMsg.reasoning += msg.delta.reasoning;
              }
              streamingContentRef.current.set(msg.message_id, currentMsg);

              // 使用 RAF 批量处理更新
              scheduleDeltaUpdate(msg);
              break;
            }

            case "tool_call:update": {
              // 更新工具调用状态
              setCurrentSnapshot((prev) => updateToolCall(prev, msg));

              // 转换 ToolCall 为 ChatCompletionMessageToolCall 格式
              const toolCallForStore = {
                id: msg.tool_call.id,
                type: "function" as const,
                function: {
                  name: msg.tool_call.name,
                  arguments: JSON.stringify(msg.tool_call.arguments),
                },
              };

              // 发射 tool_call 事件
              globalEventEmitter.emit("agent:event", {
                type: "agent:tool_call",
                dialog_id: msg.dialog_id,
                data: {
                  message_id: msg.tool_call.id,
                  tool_call: toolCallForStore,
                },
              });

              // 如果工具已完成且有结果，发射 tool_result
              if (
                msg.tool_call.status === "completed" &&
                msg.tool_call.result
              ) {
                globalEventEmitter.emit("agent:event", {
                  type: "agent:tool_result",
                  dialog_id: msg.dialog_id,
                  data: {
                    message_id: null,
                    tool_call_id: msg.tool_call.id,
                    tool_name: msg.tool_call.name,
                    arguments: msg.tool_call.arguments,
                    result: msg.tool_call.result,
                  },
                });
              }
              break;
            }

            case "status:change": {
              // 状态变更：避免在 setState updater 内触发事件，防止 render 阶段副作用警告
              const prevSnapshot = currentSnapshotRef.current;
              if (!prevSnapshot || prevSnapshot.id !== msg.dialog_id) {
                break;
              }

              let messageCompleteEvent: {
                type: "agent:message_complete";
                dialog_id: string;
                data: {
                  message_id: string;
                  content: string;
                  reasoning_content?: string;
                };
              } | null = null;

              if (msg.to === "completed" && prevSnapshot.streaming_message) {
                const messageId = prevSnapshot.streaming_message.id;
                const accumulated = streamingContentRef.current.get(messageId);
                messageCompleteEvent = {
                  type: "agent:message_complete",
                  dialog_id: msg.dialog_id,
                  data: {
                    message_id: messageId,
                    content:
                      accumulated?.content ||
                      prevSnapshot.streaming_message.content ||
                      "",
                    reasoning_content:
                      accumulated?.reasoning ||
                      prevSnapshot.streaming_message.reasoning_content,
                  },
                };

                // 清理累积内容和 message_start 记录
                streamingContentRef.current.delete(messageId);
                messageStartSentRef.current.delete(messageId);
              }

              const nextSnapshot = { ...prevSnapshot, status: msg.to };
              currentSnapshotRef.current = nextSnapshot;
              setCurrentSnapshot(nextSnapshot);

              if (messageCompleteEvent) {
                globalEventEmitter.emit("agent:event", messageCompleteEvent);
              }
              break;
            }

            case "error":
              console.error("[WebSocket] Server error:", msg.error);
              globalEventEmitter.emit("agent:event", {
                type: "agent:error",
                dialog_id: msg.dialog_id,
                data: {
                  error: msg.error?.message || "Unknown error",
                },
              });
              break;

            case "skill_edit:pending": {
              setPendingSkillEdits((prev) => {
                const exists = prev.find(
                  (item) => item.approval_id === msg.approval.approval_id,
                );
                if (exists) {
                  return prev.map((item) =>
                    item.approval_id === msg.approval.approval_id
                      ? msg.approval
                      : item,
                  );
                }
                return [msg.approval, ...prev];
              });
              break;
            }

            case "skill_edit:resolved": {
              setPendingSkillEdits((prev) =>
                prev.filter((item) => item.approval_id !== msg.approval_id),
              );
              break;
            }

            case "skill_edit:error": {
              console.error("[WebSocket] skill_edit:error", msg.error);
              break;
            }

            case "todo:updated": {
              globalEventEmitter.emit("agent:event", {
                type: "todo:updated",
                dialog_id: msg.dialog_id,
                data: {
                  todos: msg.todos,
                  rounds_since_todo: msg.rounds_since_todo,
                },
              });
              break;
            }

            case "todo:reminder": {
              globalEventEmitter.emit("agent:event", {
                type: "todo:reminder",
                dialog_id: msg.dialog_id,
                data: {
                  message: msg.message,
                  rounds_since_todo: msg.rounds_since_todo,
                },
              });
              break;
            }

            case "session:hard_blocked": {
              globalEventEmitter.emit("agent:event", {
                type: "session:hard_blocked",
                dialog_id: msg.dialog_id,
                data: {
                  reasons: msg.reasons || [],
                  unfinished_todo_count: msg.unfinished_todo_count,
                },
              });
              break;
            }
          }
        } catch (e) {
          console.error("[WebSocket] Failed to parse message:", e);
        }
      };

      ws.onclose = () => {
        console.log("[WebSocket] Disconnected");
        setIsConnected(false);
        wsRef.current = null;

        // 自动重连
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("[WebSocket] Reconnecting...");
          connectRef.current();
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error(
          "[WebSocket] Connection error. URL:",
          WS_URL,
          "Error:",
          error,
        );
        // 检查常见错误原因
        if (ws.readyState === WebSocket.CONNECTING) {
          console.error(
            "[WebSocket] Failed to establish connection. Check if backend is running on port 8001",
          );
        }
      };
    } catch (e) {
      console.error("[WebSocket] Failed to connect:", e);
    }
  };

  // 初始连接
  useEffect(() => {
    connectRef.current();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // 空依赖数组，只在组件挂载时连接一次

  // 订阅对话框
  const subscribeToDialog = useCallback((dialogId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "subscribe",
          dialog_id: dialogId,
        }),
      );
    }
  }, []);

  // 发送用户输入
  const sendUserInput = useCallback((dialogId: string, content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "user:input",
          dialog_id: dialogId,
          content,
        }),
      );
    }
  }, []);

  // 停止 Agent
  const stopAgent = useCallback((dialogId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "stop",
          dialog_id: dialogId,
        }),
      );
    }
  }, []);

  // 获取对话框列表
  const fetchDialogList = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:8001/api/dialogs");
      const result = await response.json();
      if (result.success) {
        setDialogList(result.data);
      }
    } catch (e) {
      console.error("[WebSocket] Failed to fetch dialogs:", e);
    }
  }, []);

  // 创建新对话框
  const createDialog = useCallback(async (title: string) => {
    try {
      const response = await fetch("http://localhost:8001/api/dialogs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      const result = await response.json();

      if (result.success) {
        setCurrentSnapshot(result.data);
        setDialogList((prev) => {
          const summary = {
            id: result.data.id,
            title: result.data.title,
            message_count: 0,
            updated_at: result.data.updated_at,
          };
          if (prev.find((d) => d.id === summary.id)) {
            return prev.map((d) => (d.id === summary.id ? summary : d));
          }
          return [...prev, summary];
        });
        return { success: true, data: result.data };
      }
      return { success: false };
    } catch (e) {
      console.error("[WebSocket] Failed to create dialog:", e);
      return { success: false };
    }
  }, []);

  return {
    currentSnapshot,
    dialogList,
    isConnected,
    subscribeToDialog,
    sendUserInput,
    stopAgent,
    fetchDialogList,
    createDialog,
    pendingSkillEdits,
  };
}
