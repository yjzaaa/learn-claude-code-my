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
  | "agent:tool_result"      // 工具执行结果
  | "agent:message_complete" // 消息完成
  | "agent:run_summary" // 运行摘要/钩子统计
  | "agent:error" // 错误
  | "agent:stopped" // 停止
  | "todo:updated"   // Todo 列表更新
  | "todo:reminder"; // Todo 提醒

export interface HookToolCallSummary {
  name: string;
  arguments: Record<string, unknown>;
}

export interface HookStats {
  stream_total: number;
  content_chunks: number;
  reasoning_chunks: number;
  tool_chunks: number;
  done_chunks: number;
  error_chunks: number;
  tool_calls: HookToolCallSummary[];
  complete_payload: string;
  errors: string[];
  after_run_rounds: number;
}

export interface AgentRunReportMessage {
  role: string;
  content: unknown;
  tool_call_id?: string;
  reasoning_content?: unknown;
  tool_calls?: unknown;
}

export interface AgentRunReport {
  result: string;
  hook_stats: HookStats;
  messages: AgentRunReportMessage[];
}

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

/** 工具执行结果事件 */
export interface AgentToolResultEvent extends AgentEventBase {
  type: "agent:tool_result";
  data: {
    message_id: string | null;
    tool_call_id: string;
    tool_name: string;
    arguments: Record<string, unknown>;
    result: unknown;
    timestamp?: number;
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

/** 运行摘要事件 */
export interface AgentRunSummaryEvent extends AgentEventBase {
  type: "agent:run_summary";
  data: {
    result: string;
    hook_stats: HookStats;
    messages: AgentRunReportMessage[];
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

/** Todo 项目 */
export interface TodoItem {
  id: string;
  text: string;
  status: "pending" | "in_progress" | "completed";
}

/** Todo 更新事件 */
export interface TodoUpdateEvent extends AgentEventBase {
  type: "todo:updated";
  data: {
    todos: TodoItem[];
    rounds_since_todo: number;
  };
}

/** Todo 提醒事件 */
export interface TodoReminderEvent extends AgentEventBase {
  type: "todo:reminder";
  data: {
    message: string;
    rounds_since_todo: number;
  };
}

/** 联合类型: 所有 Agent 事件 */
export type AgentEvent =
  | AgentMessageStartEvent
  | AgentContentDeltaEvent
  | AgentReasoningDeltaEvent
  | AgentToolCallEvent
  | AgentToolResultEvent
  | AgentMessageCompleteEvent
  | AgentRunSummaryEvent
  | AgentErrorEvent
  | AgentStoppedEvent
  | TodoUpdateEvent
  | TodoReminderEvent;

/** 检查是否为 Agent 事件 */
export function isAgentEvent(data: unknown): data is AgentEvent {
  if (typeof data !== "object" || data === null) return false;
  const evt = data as AgentEvent;
  return (
    typeof evt.type === "string" &&
    (evt.type.startsWith("agent:") || evt.type.startsWith("todo:")) &&
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
  /** 最近一次运行的 hook 统计 */
  hookStats: HookStats | null;
  /** 最近一次运行的完整报告（result/hook_stats/messages） */
  runReport: AgentRunReport | null;
  /** Todo 列表 */
  todos: TodoItem[] | null;
  /** 距离上次更新 todo 的轮次数 */
  roundsSinceTodo: number;
  /** 是否显示 todo 提醒 */
  showTodoReminder: boolean;
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
    hookStats: null,
    runReport: null,
    todos: null,
    roundsSinceTodo: 0,
    showTodoReminder: false,
  };
}
