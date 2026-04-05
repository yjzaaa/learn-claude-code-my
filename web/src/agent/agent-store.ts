/**
 * Agent Store - 前端单一真相源（组合入口）
 *
 * 所有服务端事件经 AgentEventBus 路由后更新此 Zustand store。
 * 以完整 DialogSession snapshot 为真相源，delta 只做渲染级更新。
 *
 * 架构：组合式 Store 设计
 * - dialog-store: 管理对话列表
 * - message-store: 管理消息状态
 * - status-store: 管理应用状态和错误
 * - agent-store: 组合层，处理事件路由
 */

import { create } from "zustand";
import type {
  DialogSession,
  DialogSummary,
  DialogStatus,
  Message,
} from "@/types/dialog";
import type {
  ServerPushEvent,
  DialogSnapshotEvent,
  StreamDeltaEvent,
  StatusChangeEvent,
  ToolCallEvent,
  ToolResultEvent,
  ErrorEvent,
} from "@/types/agent-events";

// 导出子 store
export { useDialogStore } from "@/stores/dialog-store";
export { useMessageStore } from "@/stores/message-store";
export { useStatusStore } from "@/stores/status-store";

interface AgentStoreState {
  currentSnapshot: DialogSession | null;
  dialogList: DialogSummary[];
  error: string | null;

  // Actions
  handleEvent: (event: ServerPushEvent) => void;
  setConnectedDialogs: (dialogs: DialogSummary[]) => void;
  setCurrentSnapshot: (snapshot: DialogSession | null) => void;
  clearError: () => void;
}

const seenDeltas = new Set<string>();

function dedupeKey(messageId: string, timestamp: number): string {
  return `${messageId}::${timestamp}`;
}

function flushStreamingToMessages(snapshot: DialogSession): DialogSession {
  if (!snapshot.streaming_message) return snapshot;

  const streaming = snapshot.streaming_message;
  const exists = snapshot.messages.some((m) => m.id === streaming.id);

  const completedMessage: Message = {
    ...streaming,
    status: "completed",
  };

  return {
    ...snapshot,
    messages: exists
      ? snapshot.messages.map((m) =>
          m.id === streaming.id ? completedMessage : m,
        )
      : [...snapshot.messages, completedMessage],
    streaming_message: null,
  };
}

export const useAgentStore = create<AgentStoreState>((set, get) => ({
  currentSnapshot: null,
  dialogList: [],
  error: null,

  handleEvent: (event: ServerPushEvent) => {
    switch (event.type) {
      case "dialog:snapshot": {
        const e = event as DialogSnapshotEvent;
        set((state) => {
          const snap = e.data;
          const summary: DialogSummary = {
            id: snap.id,
            title: snap.title,
            message_count: snap.messages.length,
            updated_at: snap.updated_at,
          };
          const nextDialogList = state.dialogList.some((d) => d.id === snap.id)
            ? state.dialogList.map((d) => (d.id === snap.id ? summary : d))
            : [...state.dialogList, summary];

          return {
            currentSnapshot:
              !state.currentSnapshot || state.currentSnapshot.id === snap.id
                ? snap
                : state.currentSnapshot,
            dialogList: nextDialogList,
          };
        });
        return;
      }

      case "stream:delta": {
        const e = event as StreamDeltaEvent;
        // 使用序列号或内容+时间戳去重，避免同一毫秒内的消息被丢弃
        const key = e.sequence !== undefined
          ? `${e.message_id}::${e.sequence}`
          : `${e.message_id}::${e.timestamp}::${e.delta.content}`;
        if (seenDeltas.has(key)) return;
        seenDeltas.add(key);

        set((state) => {
          if (!state.currentSnapshot || state.currentSnapshot.id !== e.dialog_id) {
            return state;
          }
          const snapshot = state.currentSnapshot;
          if (!snapshot.streaming_message) return state;

          const streaming = snapshot.streaming_message;
          return {
            currentSnapshot: {
              ...snapshot,
              streaming_message: {
                ...streaming,
                content:
                  (streaming.content || "") + (e.delta.content || ""),
                reasoning_content:
                  (streaming.reasoning_content || "") +
                  (e.delta.reasoning || ""),
              },
            },
          };
        });
        return;
      }

      case "status:change": {
        const e = event as StatusChangeEvent;
        console.log("[AgentStore] status:change:", e.data);
        set((state) => {
          if (!state.currentSnapshot || state.currentSnapshot.id !== e.dialog_id) {
            return {
              ...state,
              dialogList: state.dialogList.map((d) =>
                d.id === e.dialog_id ? { ...d, updated_at: new Date().toISOString() } : d,
              ),
            };
          }

          let nextSnapshot = {
            ...state.currentSnapshot,
            status: e.data.to as DialogStatus,
          };

          if (e.data.to === "completed" || e.data.to === "idle") {
            nextSnapshot = flushStreamingToMessages(nextSnapshot);
          }

          return {
            currentSnapshot: nextSnapshot,
            dialogList: state.dialogList.map((d) =>
              d.id === e.dialog_id
                ? {
                    ...d,
                    message_count: nextSnapshot.messages.length,
                    updated_at: nextSnapshot.updated_at,
                  }
                : d,
            ),
          };
        });
        return;
      }

      case "agent:tool_call": {
        const e = event as ToolCallEvent;
        set((state) => {
          if (!state.currentSnapshot || state.currentSnapshot.id !== e.dialog_id) {
            return state;
          }
          const snapshot = state.currentSnapshot;
          const tc = e.data.tool_call;

          if (snapshot.streaming_message) {
            const existing = snapshot.streaming_message.tool_calls || [];
            if (!existing.some((t) => t.id === tc.id)) {
              return {
                currentSnapshot: {
                  ...snapshot,
                  streaming_message: {
                    ...snapshot.streaming_message,
                    tool_calls: [...existing, tc],
                  },
                },
              };
            }
          }
          return state;
        });
        return;
      }

      case "agent:tool_result": {
        const e = event as ToolResultEvent;
        set((state) => {
          if (!state.currentSnapshot || state.currentSnapshot.id !== e.dialog_id) {
            return state;
          }
          const snapshot = state.currentSnapshot;
          const toolMsg: Message = {
            id: `tool_${Date.now()}`,
            role: "tool",
            content: e.data.result || "",
            content_type: "text",
            status: "completed",
            timestamp: new Date().toISOString(),
            tool_call_id: e.data.tool_call_id,
            tool_name: e.data.tool_name,
          };
          return {
            currentSnapshot: {
              ...snapshot,
              messages: [...snapshot.messages, toolMsg],
            },
          };
        });
        return;
      }

      case "error": {
        const e = event as ErrorEvent;
        set((state) => ({
          error: e.data.message,
          currentSnapshot:
            state.currentSnapshot?.id === e.dialog_id
              ? { ...state.currentSnapshot, status: "error" as DialogStatus }
              : state.currentSnapshot,
        }));
        return;
      }

      case "todo:updated":
      case "todo:reminder":
      case "agent:rounds_limit_reached":
        // 这些事件目前不修改核心对话状态，如有需要可扩展
        return;

      default:
        return;
    }
  },

  setConnectedDialogs: (dialogs: DialogSummary[]) => {
    set({ dialogList: dialogs });
  },

  setCurrentSnapshot: (snapshot: DialogSession | null) => {
    set({ currentSnapshot: snapshot });
  },

  clearError: () => set({ error: null }),
}));
