/**
 * Agent 流式事件类型定义
 *
 * 后端通过 WebSocket 发送的 Agent 流式输出事件
 * 对应: agents/api/agent_bridge.py 中的事件类型
 */

import type { ChatCompletionMessageToolCall } from "./openai";

/** Agent 事件类型 */
export type AgentEventType =
  | "agent:message_start"    // 助手消息开始
  | "agent:content_delta"    // 内容增量
  | "agent:reasoning_delta"  // 推理内容增量 (DeepSeek-R1等)
  | "agent:tool_call"        // 工具调用
  | "agent:message_complete" // 消息完成
  | "agent:error"            // 错误
  | "agent:stopped";         // 停止

/** Agent 流式消息 */
export interface StreamingMessage {
  id: string;
  role: "assistant";
  content: string;
  reasoning_content?: string;
  tool_calls?: ChatCompletionMessageToolCall[];
  is_complete: boolean;
}

/** Agent 事件基础接口 */
export interface AgentEventBase {
  type: AgentEventType;
  dialog_id: string;
  timestamp?: number;
}

/** 消息开始事件 */
export interface AgentMessageStartEvent extends AgentEventBase {
  type: "agent:message_start";
  data: {
    message_id: string;
    role: "assistant";
    agent_name?: string;
  };
}

/** 内容增量事件 */
export interface AgentContentDeltaEvent extends AgentEventBase {
  type: "agent:content_delta";
  data: {
    message_id: string;
    delta: string;
    content: string;
    agent_name?: string;
  };
}

/** 推理内容增量事件 */
export interface AgentReasoningDeltaEvent extends AgentEventBase {
  type: "agent:reasoning_delta";
  data: {
    message_id: string;
    message_id: string;
    delta: string;
    reasoning_content: string;
  };
}

/** 工具调用事件 */
export interface AgentToolCallEvent extends AgentEventBase {
  type: "agent:tool_call";
  data: {
    message_id: string | null;
    tool_call: ChatCompletionMessageToolCall;
  };
}

/** 消息完成事件 */
export interface AgentMessageCompleteEvent extends AgentEventBase {
  type: "agent:message_complete";
  data: {
    message_id: string;
    content: string;
    reasoning_content?: string;
    tool_calls?: ChatCompletionMessageToolCall[];
  };
}

/** 错误事件 */
export interface AgentErrorEvent extends AgentEventBase {
  type: "agent:error";
  data: {
    message_id: string | null;
    error: string;
  };
}

/** 停止事件 */
export interface AgentStoppedEvent extends AgentEventBase {
  type: "agent:stopped";
  data: {
    message_id: string | null;
  };
}

/** 联合类型: 所有 Agent 事件 */
export type AgentEvent =
  | AgentMessageStartEvent
  | AgentContentDeltaEvent
  | AgentReasoningDeltaEvent
  | AgentToolCallEvent
  | AgentMessageCompleteEvent
  | AgentErrorEvent
  | AgentStoppedEvent;

/** 检查是否为 Agent 事件 */
export function isAgentEvent(data: unknown): data is AgentEvent {
  if (typeof data !== "object" || data === null) return false;
  const evt = data as AgentEvent;
  return (
    typeof evt.type === "string" &&
    evt.type.startsWith("agent:") &&
    typeof evt.dialog_id === "string"
  );
}

/** Agent 流式状态 */
export interface AgentStreamState {
  /** 是否正在流式输出 */
  isStreaming: boolean;
  /** 当前消息 ID */
  currentMessageId: string | null;
  /** 累积的内容 */
  accumulatedContent: string;
  /** 累积的推理内容 */
  accumulatedReasoning: string;
  /** 工具调用列表 */
  toolCalls: ChatCompletionMessageToolCall[];
  /** 是否显示推理内容 */
  showReasoning: boolean;
}

/** 初始流式状态 */
export function createInitialStreamState(): AgentStreamState {
  return {
    isStreaming: false,
    currentMessageId: null,
    accumulatedContent: "",
    accumulatedReasoning: "",
    toolCalls: [],
    showReasoning: false,
  };
}
