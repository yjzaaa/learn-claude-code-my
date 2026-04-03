/**
 * WebSocket 同步协议类型定义
 *
 * 定义客户端-服务端通信的消息格式
 * 用于前端中心化消息同步架构
 */

// ============================================================================
// 基础类型
// ============================================================================

/** 消息角色 */
export type MessageRole = "user" | "assistant" | "system";

/** 消息状态 */
export type MessageStatus =
  | "pending"
  | "sending"
  | "streaming"
  | "completed"
  | "failed"
  | "truncated";

/** 流式块 */
export interface StreamChunk {
  /** 块序号（严格递增） */
  index: number;
  /** 内容 */
  content: string;
  /** 是否推理内容 */
  isReasoning?: boolean;
}

// ============================================================================
// Client → Server 消息
// ============================================================================

/** 客户端发送的基础消息 */
export interface ClientMessage {
  type: string;
  timestamp?: number;
}

/** 发送消息请求 */
export interface SendMessageRequest extends ClientMessage {
  type: "send";
  dialogId: string;
  /** 客户端预生成的消息ID */
  clientId: string;
  content: string;
  /** 乐观序号，用于排序 */
  optimisticOrder: number;
  /** 父消息ID（用于回复） */
  parentMessageId?: string;
  /** 是否为AI自修复 */
  isAutoHeal?: boolean;
}

/** 订阅对话 */
export interface SubscribeRequest extends ClientMessage {
  type: "subscribe";
  dialogId: string;
  /** 最后已知的消息ID（用于增量同步） */
  lastKnownMessageId?: string;
}

/** 取消订阅 */
export interface UnsubscribeRequest extends ClientMessage {
  type: "unsubscribe";
  dialogId: string;
}

/** 流恢复请求 */
export interface StreamResumeRequest extends ClientMessage {
  type: "stream:resume";
  dialogId: string;
  messageId: string;
  /** 从哪个块开始恢复 */
  fromChunk: number;
}

/** 同步请求（重连后） */
export interface SyncRequest extends ClientMessage {
  type: "sync:request";
  dialogId: string;
  /** 本地最后消息时间戳 */
  lastSyncAt?: number;
}

/** 心跳 */
export interface PingRequest extends ClientMessage {
  type: "ping";
}

/** 联合类型 */
export type ClientRequest =
  | SendMessageRequest
  | SubscribeRequest
  | UnsubscribeRequest
  | StreamResumeRequest
  | SyncRequest
  | PingRequest;

// ============================================================================
// Server → Client 消息
// ============================================================================

/** 服务端发送的基础消息 */
export interface ServerMessage {
  type: string;
  timestamp: number;
}

/** 发送确认 */
export interface AckMessage extends ServerMessage {
  type: "ack";
  clientId: string;
  serverId?: string;
  dialogId: string;
}

/** 流开始 */
export interface StreamStartMessage extends ServerMessage {
  type: "stream:start";
  dialogId: string;
  messageId: string;
  role: MessageRole;
  metadata?: {
    model?: string;
    agentName?: string;
  };
}

/** 流式增量 */
export interface StreamDeltaMessage extends ServerMessage {
  type: "stream:delta";
  dialogId: string;
  messageId: string;
  chunkIndex: number;
  delta: string;
  isReasoning?: boolean;
}

/** 流结束 */
export interface StreamEndMessage extends ServerMessage {
  type: "stream:end";
  dialogId: string;
  messageId: string;
  finalContent: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

/** 流恢复确认 */
export interface StreamResumedMessage extends ServerMessage {
  type: "stream:resumed";
  dialogId: string;
  messageId: string;
  fromChunk: number;
  currentChunk: number;
}

/** 流截断 */
export interface StreamTruncatedMessage extends ServerMessage {
  type: "stream:truncated";
  dialogId: string;
  messageId: string;
  reason: "interrupted" | "timeout" | "error" | "not_supported";
  lastChunkIndex: number;
}

/** 状态变更 */
export interface StatusChangeMessage extends ServerMessage {
  type: "status:change";
  dialogId: string;
  messageId?: string;
  previous: string;
  current: string;
}

/** 对话快照 */
export interface DialogSnapshotMessage extends ServerMessage {
  type: "dialog:snapshot";
  dialogId: string;
  data: {
    id: string;
    title: string;
    status: string;
    messages: ServerMessageItem[];
    streamingMessage?: StreamingMessageInfo;
    metadata: {
      model: string;
      agentName: string;
      toolCallsCount: number;
      totalTokens: number;
    };
    createdAt: string;
    updatedAt: string;
  };
}

/** 服务端消息项 */
export interface ServerMessageItem {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  agentName?: string;
  toolCalls?: ToolCallInfo[];
  toolCallId?: string;
  toolName?: string;
}

/** 流式消息信息 */
export interface StreamingMessageInfo {
  id: string;
  role: MessageRole;
  content: string;
  contentType: "markdown" | "text";
  status: "streaming";
  timestamp: string;
  agentName?: string;
  reasoningContent?: string;
  toolCalls?: ToolCallInfo[];
}

/** 工具调用信息 */
export interface ToolCallInfo {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
}

/** 错误 */
export interface ErrorMessage extends ServerMessage {
  type: "error";
  dialogId?: string;
  messageId?: string;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

/** 心跳响应 */
export interface PongMessage extends ServerMessage {
  type: "pong";
}

/** 联合类型 */
export type ServerResponse =
  | AckMessage
  | StreamStartMessage
  | StreamDeltaMessage
  | StreamEndMessage
  | StreamResumedMessage
  | StreamTruncatedMessage
  | StatusChangeMessage
  | DialogSnapshotMessage
  | ErrorMessage
  | PongMessage;

// ============================================================================
// 类型守卫
// ============================================================================

export function isSendMessageRequest(msg: unknown): msg is SendMessageRequest {
  return (
    typeof msg === "object" &&
    msg !== null &&
    (msg as ClientMessage).type === "send" &&
    typeof (msg as SendMessageRequest).dialogId === "string" &&
    typeof (msg as SendMessageRequest).clientId === "string" &&
    typeof (msg as SendMessageRequest).content === "string"
  );
}

export function isStreamDeltaMessage(msg: unknown): msg is StreamDeltaMessage {
  return (
    typeof msg === "object" &&
    msg !== null &&
    (msg as ServerMessage).type === "stream:delta" &&
    typeof (msg as StreamDeltaMessage).messageId === "string" &&
    typeof (msg as StreamDeltaMessage).chunkIndex === "number" &&
    typeof (msg as StreamDeltaMessage).delta === "string"
  );
}

export function isStreamEndMessage(msg: unknown): msg is StreamEndMessage {
  return (
    typeof msg === "object" &&
    msg !== null &&
    (msg as ServerMessage).type === "stream:end" &&
    typeof (msg as StreamEndMessage).messageId === "string" &&
    typeof (msg as StreamEndMessage).finalContent === "string"
  );
}

export function isErrorMessage(msg: unknown): msg is ErrorMessage {
  return (
    typeof msg === "object" &&
    msg !== null &&
    (msg as ServerMessage).type === "error" &&
    typeof (msg as ErrorMessage).error === "object"
  );
}

// ============================================================================
// 辅助类型
// ============================================================================

/** WebSocket 连接状态 */
export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

/** 同步状态 */
export interface SyncState {
  status: ConnectionStatus;
  lastSyncAt?: number;
  pendingMessages: number;
  isRecovering: boolean;
}
