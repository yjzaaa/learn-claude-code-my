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
}
