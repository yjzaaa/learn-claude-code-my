/**
 * Agent Events - 统一事件模型
 *
 * 前后端共享的事件 schema TypeScript 定义
 */

import type { DialogSession, DialogStatus, ToolCall } from "./dialog";

// ═══════════════════════════════════════════════════════════
// Runtime 内部事件 (AgentEvent)
// ═══════════════════════════════════════════════════════════

export type AgentEventType =
  | "text_delta"
  | "reasoning_delta"
  | "message_complete"
  | "tool_call"
  | "tool_result"
  | "snapshot"
  | "status_change"
  | "error";

export interface AgentEvent {
  type: AgentEventType;
  dialog_id: string;
  data: Record<string, unknown>;
  timestamp?: number;
}

// ═══════════════════════════════════════════════════════════
// Server Push Events (WebSocket -> frontend)
// ═══════════════════════════════════════════════════════════

export interface DialogSnapshotEvent {
  type: "dialog:snapshot";
  dialog_id: string;
  data: DialogSession;
  timestamp: number;
}

export interface StreamDeltaEvent {
  type: "stream:delta";
  dialog_id: string;
  message_id: string;
  delta: {
    content?: string;
    reasoning?: string;
  };
  timestamp: number;
}

export interface StatusChangeEvent {
  type: "status:change";
  dialog_id: string;
  data: {
    from: DialogStatus;
    to: DialogStatus;
  };
  timestamp: number;
}

export interface ToolCallEvent {
  type: "agent:tool_call";
  dialog_id: string;
  data: {
    message_id: string;
    tool_call: ToolCall;
  };
  timestamp: number;
}

export interface ToolResultEvent {
  type: "agent:tool_result";
  dialog_id: string;
  data: {
    message_id?: string | null;
    tool_call_id: string;
    tool_name: string;
    arguments?: Record<string, unknown>;
    result?: string;
  };
  timestamp: number;
}

export interface ErrorEvent {
  type: "error";
  dialog_id: string;
  data: {
    code: string;
    message: string;
  };
  timestamp: number;
}

export interface TodoUpdatedEvent {
  type: "todo:updated";
  dialog_id: string;
  data: {
    todos: Array<{ id: string; text: string; status: string }>;
    rounds_since_todo: number;
  };
  timestamp: number;
}

export interface TodoReminderEvent {
  type: "todo:reminder";
  dialog_id: string;
  data: {
    message: string;
    rounds_since_todo: number;
  };
  timestamp: number;
}

export interface RoundsLimitEvent {
  type: "agent:rounds_limit_reached";
  dialog_id: string;
  data: {
    rounds: number;
  };
  timestamp: number;
}

export interface SkillEditPendingEvent {
  type: "skill_edit:pending";
  dialog_id: string;
  data: {
    approval: {
      approval_id: string;
      dialog_id: string;
      path: string;
      old_content: string;
      new_content: string;
      unified_diff: string;
      reason: string;
      trigger_mode: string;
      status: string;
      created_at: number;
      resolved_at?: number;
    };
  };
  timestamp: number;
}

export interface SkillEditResolvedEvent {
  type: "skill_edit:resolved";
  dialog_id: string;
  data: {
    approval_id: string;
    result: string;
  };
  timestamp: number;
}

export interface SkillEditErrorEvent {
  type: "skill_edit:error";
  dialog_id?: string;
  data: {
    error: {
      code?: string;
      message: string;
    };
  };
  timestamp?: number;
}

export type ServerPushEvent =
  | DialogSnapshotEvent
  | StreamDeltaEvent
  | StatusChangeEvent
  | ToolCallEvent
  | ToolResultEvent
  | ErrorEvent
  | TodoUpdatedEvent
  | TodoReminderEvent
  | RoundsLimitEvent
  | SkillEditPendingEvent
  | SkillEditResolvedEvent
  | SkillEditErrorEvent;
