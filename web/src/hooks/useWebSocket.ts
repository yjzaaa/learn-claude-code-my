"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { DialogSession, DialogSummary, SkillEditApproval } from "@/types/dialog";
import type { ServerPushEvent } from "@/types/agent-events";
import { agentEventBus } from "@/agent/agent-event-bus";
import { useAgentStore } from "@/agent/agent-store";

// WebSocket URL - 优先使用环境变量，否则使用默认值
const WS_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws/client-1"
    : "ws://localhost:8001/ws/client-1";

console.log("[WebSocket] Initializing with URL:", WS_URL);

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
 * WebSocket Hook - 纯连接层，不做任何状态合并
 *
 * 所有收到的事件直接转发给 AgentEventBus，状态从 useAgentStore 读取。
 */
export function useWebSocket(): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [pendingSkillEdits, setPendingSkillEdits] = useState<SkillEditApproval[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const activeConnIdRef = useRef<number>(0);

  // 从统一 store 读取状态
  const currentSnapshot = useAgentStore((s) => s.currentSnapshot);
  const dialogList = useAgentStore((s) => s.dialogList);
  const setConnectedDialogs = useAgentStore((s) => s.setConnectedDialogs);

  // 使用 ref 存储连接函数，避免 useCallback 依赖问题
  const connectRef = useRef<() => void>(() => {});

  // 定义连接函数
  connectRef.current = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      console.log("[WebSocket] Connecting to:", WS_URL);
      const connId = ++activeConnIdRef.current;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WebSocket] Connected");
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        // Drop events from stale connections
        if (connId !== activeConnIdRef.current) return;
        try {
          const msg: ServerPushEvent = JSON.parse(event.data);
          console.log("[WebSocket] Received:", msg.type, msg);

          //  skill edit / todo 事件目前由本地 handler 处理
          if (msg.type === "skill_edit:pending") {
            setPendingSkillEdits((prev) => {
              const exists = prev.find(
                (item) => item.approval_id === msg.data.approval.approval_id,
              );
              if (exists) {
                return prev.map((item) =>
                  item.approval_id === msg.data.approval.approval_id
                    ? msg.data.approval
                    : item,
                );
              }
              return [msg.data.approval, ...prev];
            });
            return;
          }

          if (msg.type === "skill_edit:resolved") {
            setPendingSkillEdits((prev) =>
              prev.filter((item) => item.approval_id !== msg.data.approval_id),
            );
            return;
          }

          if (msg.type === "skill_edit:error") {
            console.error("[WebSocket] skill_edit:error", msg.data.error);
            return;
          }

          // 其余所有事件统一交给 AgentEventBus
          agentEventBus.handleEvent(msg);
        } catch (e) {
          console.error("[WebSocket] Failed to parse message:", e);
        }
      };

      ws.onclose = () => {
        console.log("[WebSocket] Disconnected");
        setIsConnected(false);
        if (wsRef.current === ws) {
          wsRef.current = null;
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log("[WebSocket] Reconnecting...");
            connectRef.current();
          }, 3000);
        }
      };

      ws.onerror = (error) => {
        console.error(
          "[WebSocket] Connection error. URL:",
          WS_URL,
          "Error:",
          error,
        );
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
  }, []);

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
      if (result.success && Array.isArray(result.data)) {
        const summaries: DialogSummary[] = result.data.map((d: DialogSession) => ({
          id: d.id,
          title: d.title,
          message_count: d.messages?.length || 0,
          updated_at: d.updated_at,
        }));
        setConnectedDialogs(summaries);
      }
    } catch (e) {
      console.error("[WebSocket] Failed to fetch dialogs:", e);
    }
  }, [setConnectedDialogs]);

  // 创建新对话框
  const createDialog = useCallback(async (title: string) => {
    try {
      const response = await fetch("http://localhost:8001/api/dialogs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      const result = await response.json();

      if (result.success && result.data) {
        const data: DialogSession = result.data;
        // 注入到 store
        agentEventBus.handleEvent({
          type: "dialog:snapshot",
          dialog_id: data.id,
          data,
          timestamp: Date.now(),
        });
        return { success: true, data };
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
