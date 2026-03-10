/**
 * 统一类型导出 - OpenAI 原生风格
 *
 * 删除所有自定义类型，直接使用 OpenAI 标准格式
 */

export type {
  ChatRole,
  ChatMessage,
  ChatCompletionMessageToolCall,
  ChatCompletionTool,
  ChatCompletionChunk,
  ChatSession,
  ChatEvent,
  ChatEventType,
} from "./openai";

export {
  createUserMessage,
  createAssistantMessage,
  createSystemMessage,
  createToolMessage,
  createToolCallMessage,
  generateId,
  parseToolCallArguments,
  isChatMessage,
  isChatEvent,
} from "./openai";

// Agent 流式事件类型
export type {
  AgentEventType,
  StreamingMessage,
  AgentEvent,
  AgentMessageStartEvent,
  AgentContentDeltaEvent,
  AgentReasoningDeltaEvent,
  AgentToolCallEvent,
  AgentMessageCompleteEvent,
  AgentErrorEvent,
  AgentStoppedEvent,
  AgentStreamState,
  TodoItem,
  TodoUpdateEvent,
  TodoReminderEvent,
} from "./agent-event";

export { isAgentEvent, createInitialStreamState } from "./agent-event";

// Dialog 类型
export type {
  TodoItem as DialogTodoItem,
  TodoState,
  TodoUpdatedEvent as DialogTodoUpdatedEvent,
  TodoReminderEvent as DialogTodoReminderEvent,
} from "./dialog";
