/**
 * Dialog 类型定义 - 后端状态管理架构
 *
 * 前端纯渲染设计，所有类型与后端保持一致
 */

export type DialogStatus =
  | "idle"
  | "thinking"
  | "tool_calling"
  | "completed"
  | "error";

export type Role = "user" | "assistant" | "tool" | "system";

export type ContentType = "text" | "markdown" | "json";

export type MessageStatus = "pending" | "streaming" | "completed" | "error";

export type ToolCallStatus = "pending" | "running" | "completed" | "error";

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: ToolCallStatus;
  result?: string;
  started_at?: string;
  completed_at?: string;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  content_type: ContentType;
  status: MessageStatus;
  timestamp: string;

  // Assistant only
  tool_calls?: ToolCall[];
  reasoning_content?: string;
  agent_name?: string;

  // Tool only
  tool_call_id?: string;
  tool_name?: string;
}

export interface DialogMetadata {
  model: string;
  agent_name: string;
  tool_calls_count: number;
  total_tokens: number;
}

export interface DialogSession {
  id: string;
  title: string;
  status: DialogStatus;
  messages: Message[];
  streaming_message: Message | null;
  metadata: DialogMetadata;
  created_at: string;
  updated_at: string;
}

export interface DialogSummary {
  id: string;
  title: string;
  message_count: number;
  updated_at: string;
}

// WebSocket 事件类型
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

export interface ToolCallUpdateEvent {
  type: "tool_call:update";
  dialog_id: string;
  tool_call: ToolCall;
  timestamp: number;
}

export interface StatusChangeEvent {
  type: "status:change";
  dialog_id: string;
  from: DialogStatus;
  to: DialogStatus;
  timestamp: number;
}

export interface ErrorEvent {
  type: "error";
  dialog_id?: string;
  error: {
    code: string;
    message: string;
  };
  timestamp: number;
}

export interface SkillEditApproval {
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
}

export interface SkillEditPendingEvent {
  type: "skill_edit:pending";
  dialog_id: string;
  approval: SkillEditApproval;
  timestamp: number;
}

export interface SkillEditResolvedEvent {
  type: "skill_edit:resolved";
  dialog_id: string;
  approval_id: string;
  result: string;
  timestamp: number;
}

export interface SkillEditErrorEvent {
  type: "skill_edit:error";
  dialog_id?: string;
  approval_id?: string;
  error: {
    code?: string;
    message: string;
  };
  timestamp?: number;
}

// Todo 类型
export interface TodoItem {
  id: string;
  text: string;
  status: "pending" | "in_progress" | "completed";
}

export interface TodoState {
  dialog_id: string;
  items: TodoItem[];
  rounds_since_todo: number;
  updated_at: number;
}

// Todo WebSocket 事件
export interface TodoUpdatedEvent {
  type: "todo:updated";
  dialog_id: string;
  todos: TodoItem[];
  rounds_since_todo: number;
  timestamp: number;
}

export interface TodoReminderEvent {
  type: "todo:reminder";
  dialog_id: string;
  message: string;
  rounds_since_todo: number;
  timestamp: number;
}

export type ServerPushEvent =
  | DialogSnapshotEvent
  | StreamDeltaEvent
  | ToolCallUpdateEvent
  | StatusChangeEvent
  | ErrorEvent
  | SkillEditPendingEvent
  | SkillEditResolvedEvent
  | SkillEditErrorEvent
  | TodoUpdatedEvent
  | TodoReminderEvent;

// 客户端发送的事件
export interface SubscribeEvent {
  type: "subscribe";
  dialog_id: string;
}

export interface UserInputEvent {
  type: "user:input";
  dialog_id: string;
  content: string;
}

export interface StopRequestEvent {
  type: "stop";
  dialog_id: string;
}

export type ClientEvent = SubscribeEvent | UserInputEvent | StopRequestEvent;
