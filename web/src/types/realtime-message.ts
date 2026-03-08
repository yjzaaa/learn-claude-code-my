<<<<<<< HEAD
import type { ChatMessage } from "./openai";

export interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

export interface StreamTokenMessage extends WebSocketMessage {
  type: "stream_token";
  token?: string;
}

export interface MessageAddedEvent extends WebSocketMessage {
  type: "message_added";
  dialog_id?: string;
  message?: ChatMessage;
}

export interface MessageUpdatedEvent extends WebSocketMessage {
  type: "message_updated";
  dialog_id?: string;
  message?: ChatMessage;
}

export interface DialogSubscribedEvent extends WebSocketMessage {
  type: "dialog_subscribed";
  dialog_id: string;
  dialog: unknown;
=======
/**
 * WebSocket 实时消息类型定义
 *
 * 用于前后端 WebSocket 通信
 */

import type { ChatMessage, ChatSession } from "./openai";

/** 基础 WebSocket 消息 */
export interface WebSocketMessage {
  type: string;
  dialog_id?: string;
  timestamp?: number;
  [key: string]: unknown;
}

/** 流式 token 消息 */
export interface StreamTokenMessage extends WebSocketMessage {
  type: "stream_token";
  dialog_id: string;
  content?: string;
  is_complete?: boolean;
}

/** 消息添加事件 */
export interface MessageAddedEvent extends WebSocketMessage {
  type: "message_added";
  dialog_id: string;
  message: ChatMessage;
}

/** 消息更新事件 */
export interface MessageUpdatedEvent extends WebSocketMessage {
  type: "message_updated";
  dialog_id: string;
  message_id: string;
  updates: Partial<ChatMessage>;
}

/** 对话框订阅事件 */
export interface DialogSubscribedEvent extends WebSocketMessage {
  type: "dialog_subscribed";
  dialog_id: string;
  dialog: ChatSession | null;
}

/** Agent 流式事件 */
export interface AgentStreamMessage extends WebSocketMessage {
  type: "agent:message_start" | "agent:content_delta" | "agent:reasoning_delta" | "agent:tool_call" | "agent:message_complete" | "agent:error" | "agent:stopped";
  dialog_id: string;
  data: Record<string, unknown>;
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)
}
