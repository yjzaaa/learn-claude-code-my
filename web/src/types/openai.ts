/**
 * OpenAI 原生风格类型定义
 *
 * 与 OpenAI API 完全兼容的消息格式，用于前后端通信。
 * 参考: https://platform.openai.com/docs/api-reference/chat
 */

// ============================================================================
// 基础类型
// ============================================================================

export type ChatRole = "system" | "user" | "assistant" | "tool";

export interface ChatCompletionMessageToolCall {
  /** 工具调用ID */
  id: string;
  /** 调用类型 */
  type?: "function";
  /** 函数信息 */
  function: {
    /** 函数名 */
    name: string;
    /** 参数(JSON字符串) */
    arguments: string;
  };
}

export interface ChatMessage {
  /** 消息角色 */
  role: ChatRole;
  /** 消息内容 */
  content: string | null;
  /** 推理内容 (仅推理模型如 DeepSeek-R1) */
  reasoning_content?: string;
  /** 工具调用列表 (仅 assistant 角色) */
  tool_calls?: ChatCompletionMessageToolCall[];
  /** 工具调用ID (仅 tool 角色) */
  tool_call_id?: string;
  /** 工具名称 (仅 tool 角色) */
  name?: string;
  /** Agent 名称标识 (用于显示是哪个 Agent 回复的) */
  agent_name?: string;
  /** 消息ID (用于流式更新关联) */
  id?: string;
}

// ============================================================================
// 工厂函数
// ============================================================================

export function createUserMessage(content: string): ChatMessage {
  return { role: "user", content };
}

export function createAssistantMessage(content: string): ChatMessage {
  return { role: "assistant", content };
}

export function createSystemMessage(content: string): ChatMessage {
  return { role: "system", content };
}

export function createToolMessage(
  content: string,
  toolCallId: string,
  name?: string
): ChatMessage {
  return {
    role: "tool",
    content,
    tool_call_id: toolCallId,
    name
  };
}

export function createToolCallMessage(
  toolCalls: ChatCompletionMessageToolCall[]
): ChatMessage {
  return {
    role: "assistant",
    content: null,
    tool_calls: toolCalls
  };
}

// ============================================================================
// 工具定义
// ============================================================================

export interface ChatCompletionTool {
  type: "function";
  function: {
    name: string;
    description?: string;
    parameters?: Record<string, unknown>;
  };
}

// ============================================================================
// 流式响应
// ============================================================================

export interface ChatCompletionChunk {
  id: string;
  object: "chat.completion.chunk";
  created: number;
  model: string;
  choices: {
    index: number;
    delta: {
      role?: ChatRole;
      content?: string;
      tool_calls?: ChatCompletionMessageToolCall[];
    };
    finish_reason: "stop" | "length" | "tool_calls" | "content_filter" | null;
  }[];
}

// ============================================================================
// 对话会话
// ============================================================================

export interface ChatSession {
  id: string;
  messages: ChatMessage[];
  model?: string;
  created_at: number;
  updated_at: number;
}

// ============================================================================
// WebSocket 事件 (基于 OpenAI 格式)
// ============================================================================

export type ChatEventType =
  | "message"      // 新消息
  | "delta"        // 流式增量
  | "tool_call"    // 工具调用
  | "tool_result"  // 工具结果
  | "error"        // 错误
  | "system";      // 系统事件

export interface ChatEvent {
  type: ChatEventType;
  dialog_id: string;
  message: ChatMessage;
  timestamp: number;
}

// ============================================================================
// 辅助函数
// ============================================================================

/**
 * 生成唯一ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 解析工具调用参数
 */
export function parseToolCallArguments(
  toolCall: ChatCompletionMessageToolCall
): Record<string, unknown> {
  try {
    return JSON.parse(toolCall.function.arguments);
  } catch {
    return {};
  }
}

/**
 * 类型守卫: 检查是否为 ChatMessage
 */
export function isChatMessage(data: unknown): data is ChatMessage {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as ChatMessage;
  return (
    typeof msg.role === "string" &&
    ["system", "user", "assistant", "tool"].includes(msg.role)
  );
}

/**
 * 类型守卫: 检查是否为 ChatEvent
 */
export function isChatEvent(data: unknown): data is ChatEvent {
  if (typeof data !== "object" || data === null) return false;
  const evt = data as ChatEvent;
  return (
    typeof evt.type === "string" &&
    typeof evt.dialog_id === "string" &&
    isChatMessage(evt.message)
  );
}
