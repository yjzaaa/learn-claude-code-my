/**
 * API 契约 - TypeScript 类型定义
 *
 * 前后端共享的类型定义，与 OpenAPI 规范保持一致
 * @version 1.0.0
 */

// ═════════════════════════════════════════════════════════════════════════════
// 基础枚举类型
// ═════════════════════════════════════════════════════════════════════════════

/** 对话状态 */
export type DialogStatus =
  | "idle"
  | "thinking"
  | "tool_calling"
  | "completed"
  | "error";

/** 消息角色 */
export type MessageRole = "user" | "assistant" | "tool" | "system";

/** 消息状态 */
export type MessageStatus = "pending" | "streaming" | "completed" | "error";

/** 内容类型 */
export type ContentType = "text" | "markdown" | "json";

/** 工具调用状态 */
export type ToolCallStatus = "pending" | "running" | "completed" | "error";

/** 流截断原因 */
export type TruncatedReason =
  | "interrupted"
  | "timeout"
  | "error"
  | "not_supported";

/** WebSocket 连接状态 */
export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

// ═════════════════════════════════════════════════════════════════════════════
// 实体类型
// ═════════════════════════════════════════════════════════════════════════════

/** 工具调用 */
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: ToolCallStatus;
  result?: string;
  started_at?: string;
  completed_at?: string;
}

/** 消息 */
export interface Message {
  id: string;
  role: MessageRole;
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

/** 流式消息 (streaming_message) */
export interface StreamingMessage {
  id: string;
  role: MessageRole;
  content: string;
  content_type: ContentType;
  status: "streaming";
  timestamp: string;
  agent_name: string;
  reasoning_content?: string;
  tool_calls?: ToolCall[];
}

/** 对话元数据 */
export interface DialogMetadata {
  model: string;
  agent_name: string;
  tool_calls_count: number;
  total_tokens: number;
}

/** 对话会话 */
export interface DialogSession {
  id: string;
  title: string;
  status: DialogStatus;
  messages: Message[];
  streaming_message: StreamingMessage | null;
  metadata: DialogMetadata;
  created_at: string;
  updated_at: string;
}

/** 对话摘要 */
export interface DialogSummary {
  id: string;
  title: string;
  message_count: number;
  updated_at: string;
}

/** Todo 项目 */
export interface TodoItem {
  id: string;
  text: string;
  status: "pending" | "in_progress" | "completed";
}

/** 技能项 */
export interface SkillItem {
  name: string;
  description: string;
  tags: string;
  path: string;
}

// ═════════════════════════════════════════════════════════════════════════════
// REST API 请求类型
// ═════════════════════════════════════════════════════════════════════════════

/** 创建对话请求 */
export interface CreateDialogRequest {
  title?: string;
}

/** 发送消息请求 */
export interface SendMessageRequest {
  content: string;
}

// ═════════════════════════════════════════════════════════════════════════════
// REST API 响应类型
// ═════════════════════════════════════════════════════════════════════════════

/** 基础响应 */
export interface BaseResponse {
  success: boolean;
  message: string;
}

/** 健康检查响应 */
export interface HealthResponse extends BaseResponse {
  status: "ok";
  dialogs: number;
}

/** 对话列表响应 */
export interface ListDialogsResponse extends BaseResponse {
  data: DialogSession[];
}

/** 创建对话响应 */
export interface CreateDialogResponse extends BaseResponse {
  data: DialogSession;
}

/** 获取对话响应 */
export interface GetDialogResponse extends BaseResponse {
  data: DialogSession;
}

/** 删除对话响应 */
export interface DeleteDialogResponse extends BaseResponse {}

/** 获取消息响应 */
export interface GetMessagesResponse extends BaseResponse {
  data: {
    items: Message[];
  };
}

/** 发送消息数据 */
export interface SendMessageData {
  message_id: string;
  status: "queued";
}

/** 发送消息响应 */
export interface SendMessageResponse extends BaseResponse {
  data: SendMessageData;
}

/** 恢复对话数据 */
export interface ResumeData {
  dialog_id: string;
  status: "idle";
}

/** 恢复对话响应 */
export interface ResumeDialogResponse extends BaseResponse {
  data: ResumeData;
}

/** Agent 状态项 */
export interface AgentStatusItem {
  dialog_id: string;
  status: string;
}

/** Agent 状态数据 */
export interface AgentStatusData {
  active_dialogs: AgentStatusItem[];
  total_dialogs: number;
}

/** Agent 状态响应 */
export interface AgentStatusResponse extends BaseResponse {
  data: AgentStatusData;
}

/** 停止 Agent 数据 */
export interface StopAgentData {
  stopped_dialogs: string[];
  count: number;
}

/** 停止 Agent 响应 */
export interface StopAgentResponse extends BaseResponse {
  data: StopAgentData;
}

/** 技能列表响应 */
export interface SkillListResponse extends BaseResponse {
  data: SkillItem[];
}

/** 待处理技能编辑响应 */
export interface PendingSkillEditsResponse extends BaseResponse {
  data: {
    proposals: unknown[];
  };
}

// ═════════════════════════════════════════════════════════════════════════════
// WebSocket 客户端 → 服务端消息
// ═════════════════════════════════════════════════════════════════════════════

/** 基础客户端消息 */
export interface ClientMessage {
  type: string;
  timestamp?: number;
}

/** 订阅请求 */
export interface SubscribeRequest extends ClientMessage {
  type: "subscribe";
  dialog_id: string;
  last_known_message_id?: string;
}

/** 取消订阅请求 */
export interface UnsubscribeRequest extends ClientMessage {
  type: "unsubscribe";
  dialog_id: string;
}

/** 心跳请求 */
export interface PingRequest extends ClientMessage {
  type: "ping";
}

/** 流恢复请求 */
export interface StreamResumeRequest extends ClientMessage {
  type: "stream:resume";
  dialog_id: string;
  message_id: string;
  from_chunk: number;
}

/** 同步请求 */
export interface SyncRequest extends ClientMessage {
  type: "sync:request";
  dialog_id: string;
  last_sync_at?: number;
}

/** 客户端请求联合类型 */
export type ClientRequest =
  | SubscribeRequest
  | UnsubscribeRequest
  | PingRequest
  | StreamResumeRequest
  | SyncRequest;

// ═════════════════════════════════════════════════════════════════════════════
// WebSocket 服务端 → 客户端事件
// ═════════════════════════════════════════════════════════════════════════════

/** 基础服务端消息 */
export interface ServerMessage {
  type: string;
  timestamp: number;
}

/** 对话快照事件 */
export interface DialogSnapshotEvent extends ServerMessage {
  type: "dialog:snapshot";
  dialog_id: string;
  data: DialogSession;
}

/** 流开始事件 */
export interface StreamStartEvent extends ServerMessage {
  type: "stream:start";
  dialog_id: string;
  message_id: string;
  role: MessageRole;
  metadata?: {
    model?: string;
    agent_name?: string;
  };
}

/** 流增量事件 */
export interface StreamDeltaEvent extends ServerMessage {
  type: "stream:delta";
  dialog_id: string;
  message_id: string;
  chunk_index: number;
  delta: string;
  is_reasoning?: boolean;
}

/** 流结束事件 */
export interface StreamEndEvent extends ServerMessage {
  type: "stream:end";
  dialog_id: string;
  message_id: string;
  final_content: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

/** 流恢复确认事件 */
export interface StreamResumedEvent extends ServerMessage {
  type: "stream:resumed";
  dialog_id: string;
  message_id: string;
  from_chunk: number;
  current_chunk: number;
}

/** 流截断事件 */
export interface StreamTruncatedEvent extends ServerMessage {
  type: "stream:truncated";
  dialog_id: string;
  message_id: string;
  reason: TruncatedReason;
  last_chunk_index: number;
}

/** 状态变更事件 */
export interface StatusChangeEvent extends ServerMessage {
  type: "status:change";
  dialog_id: string;
  from: DialogStatus;
  to: DialogStatus;
}

/** 工具调用更新事件 */
export interface ToolCallUpdateEvent extends ServerMessage {
  type: "tool_call:update";
  dialog_id: string;
  tool_call: ToolCall;
}

/** Todo 更新事件 */
export interface TodoUpdatedEvent extends ServerMessage {
  type: "todo:updated";
  dialog_id: string;
  todos: TodoItem[];
  rounds_since_todo: number;
}

/** Todo 提醒事件 */
export interface TodoReminderEvent extends ServerMessage {
  type: "todo:reminder";
  dialog_id: string;
  message: string;
  rounds_since_todo: number;
}

/** 错误详情 */
export interface ErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

/** 错误事件 */
export interface ErrorEvent extends ServerMessage {
  type: "error";
  dialog_id?: string;
  message_id?: string;
  error: ErrorDetail;
}

/** 确认事件 */
export interface AckEvent extends ServerMessage {
  type: "ack";
  dialog_id: string;
  client_id: string;
  server_id?: string;
  message?: unknown;
}

/** 心跳响应 */
export interface PongEvent extends ServerMessage {
  type: "pong";
}

/** 服务端事件联合类型 */
export type ServerEvent =
  | DialogSnapshotEvent
  | StreamStartEvent
  | StreamDeltaEvent
  | StreamEndEvent
  | StreamResumedEvent
  | StreamTruncatedEvent
  | StatusChangeEvent
  | ToolCallUpdateEvent
  | TodoUpdatedEvent
  | TodoReminderEvent
  | ErrorEvent
  | AckEvent
  | PongEvent;

// ═════════════════════════════════════════════════════════════════════════════
// 错误码定义
// ═════════════════════════════════════════════════════════════════════════════

/** 错误码枚举 */
export type ErrorCode =
  // 验证错误 (400)
  | "VALIDATION_001"
  | "VALIDATION_002"
  // 未找到 (404)
  | "NOT_FOUND_100"
  | "NOT_FOUND_101"
  // 冲突 (409)
  | "CONFLICT_100"
  // 内部错误 (500)
  | "INTERNAL_001"
  // Agent 错误 (600)
  | "AGENT_300"
  | "AGENT_301"
  | "AGENT_302"
  // 工具错误 (700)
  | "TOOL_400"
  | "TOOL_401"
  | "TOOL_402"
  // Skill 错误 (800)
  | "SKILL_500"
  | "SKILL_501";

/** 错误码映射 */
export const ErrorMessages: Record<ErrorCode, string> = {
  VALIDATION_001: "请求参数无效",
  VALIDATION_002: "缺少必需参数",
  NOT_FOUND_100: "对话不存在",
  NOT_FOUND_101: "消息不存在",
  CONFLICT_100: "对话正在处理中",
  INTERNAL_001: "内部服务器错误",
  AGENT_300: "Agent 执行错误",
  AGENT_301: "Agent 超时",
  AGENT_302: "Agent 轮次限制达到",
  TOOL_400: "工具执行错误",
  TOOL_401: "工具未找到",
  TOOL_402: "工具参数无效",
  SKILL_500: "Skill 加载错误",
  SKILL_501: "Skill 未找到",
};

// ═════════════════════════════════════════════════════════════════════════════
// 类型守卫函数
// ═════════════════════════════════════════════════════════════════════════════

/** 检查是否为服务端消息 */
export function isServerMessage(data: unknown): data is ServerMessage {
  return (
    typeof data === "object" &&
    data !== null &&
    "type" in data &&
    typeof (data as ServerMessage).type === "string" &&
    "timestamp" in data &&
    typeof (data as ServerMessage).timestamp === "number"
  );
}

/** 检查是否为对话快照事件 */
export function isDialogSnapshotEvent(
  data: unknown
): data is DialogSnapshotEvent {
  return (
    isServerMessage(data) &&
    data.type === "dialog:snapshot" &&
    "data" in data
  );
}

/** 检查是否为流增量事件 */
export function isStreamDeltaEvent(data: unknown): data is StreamDeltaEvent {
  return (
    isServerMessage(data) &&
    data.type === "stream:delta" &&
    "message_id" in data &&
    "delta" in data
  );
}

/** 检查是否为流结束事件 */
export function isStreamEndEvent(data: unknown): data is StreamEndEvent {
  return (
    isServerMessage(data) &&
    data.type === "stream:end" &&
    "message_id" in data &&
    "final_content" in data
  );
}

/** 检查是否为状态变更事件 */
export function isStatusChangeEvent(data: unknown): data is StatusChangeEvent {
  return (
    isServerMessage(data) &&
    data.type === "status:change" &&
    "from" in data &&
    "to" in data
  );
}

/** 检查是否为错误事件 */
export function isErrorEvent(data: unknown): data is ErrorEvent {
  return (
    isServerMessage(data) &&
    data.type === "error" &&
    "error" in data &&
    typeof (data as ErrorEvent).error === "object"
  );
}

/** 检查是否为 Todo 更新事件 */
export function isTodoUpdatedEvent(data: unknown): data is TodoUpdatedEvent {
  return (
    isServerMessage(data) &&
    data.type === "todo:updated" &&
    "todos" in data
  );
}
