/**
 * 实时消息系统类型定义
 */

export type RealtimeMessageType =
  | "user_message"
  | "assistant_text"
  | "assistant_thinking"
  | "tool_call"
  | "tool_result"
  | "system_event"
  | "stream_token"
  | "dialog_start"
  | "dialog_end";

export type MessageStatus =
  | "pending"
  | "streaming"
  | "completed"
  | "error";

export interface RealtimeMessage {
  id: string;
  type: RealtimeMessageType;
  content: string;
  status: MessageStatus;
  tool_name?: string;
  tool_input?: Record<string, any>;
  timestamp: string;
  metadata?: Record<string, any>;
  parent_id?: string;
  stream_tokens?: string[];
}

export interface DialogSession {
  id: string;
  title: string;
  messages: RealtimeMessage[];
  status: MessageStatus;
  created_at: string;
  updated_at: string;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface StreamTokenMessage extends WebSocketMessage {
  type: "stream_token";
  dialog_id: string;
  message_id: string;
  token: string;
  current_content: string;
}

export interface MessageAddedEvent extends WebSocketMessage {
  type: "message_added";
  dialog_id: string;
  message: RealtimeMessage;
}

export interface MessageUpdatedEvent extends WebSocketMessage {
  type: "message_updated";
  dialog_id: string;
  message: RealtimeMessage;
}

export interface DialogSubscribedEvent extends WebSocketMessage {
  type: "dialog_subscribed";
  dialog_id: string;
  dialog: DialogSession | null;
}

// 消息类型配置
export const MESSAGE_TYPE_CONFIG: Record<
  RealtimeMessageType,
  {
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    icon: string;
  }
> = {
  user_message: {
    label: "用户",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    icon: "User",
  },
  assistant_text: {
    label: "助手",
    color: "text-zinc-700",
    bgColor: "bg-zinc-50",
    borderColor: "border-zinc-200",
    icon: "Bot",
  },
  assistant_thinking: {
    label: "思考中",
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
    icon: "Brain",
  },
  tool_call: {
    label: "工具调用",
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
    icon: "Wrench",
  },
  tool_result: {
    label: "工具结果",
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-200",
    icon: "CheckCircle",
  },
  system_event: {
    label: "系统",
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-200",
    icon: "AlertCircle",
  },
  stream_token: {
    label: "流式",
    color: "text-cyan-600",
    bgColor: "bg-cyan-50",
    borderColor: "border-cyan-200",
    icon: "Zap",
  },
  dialog_start: {
    label: "开始",
    color: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    icon: "Play",
  },
  dialog_end: {
    label: "结束",
    color: "text-red-600",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    icon: "Square",
  },
};

// 状态配置
export const MESSAGE_STATUS_CONFIG: Record<
  MessageStatus,
  {
    label: string;
    color: string;
    dotColor: string;
    animate: boolean;
  }
> = {
  pending: {
    label: "等待中",
    color: "text-yellow-600",
    dotColor: "bg-yellow-500",
    animate: false,
  },
  streaming: {
    label: "流式传输",
    color: "text-blue-600",
    dotColor: "bg-blue-500",
    animate: true,
  },
  completed: {
    label: "已完成",
    color: "text-green-600",
    dotColor: "bg-green-500",
    animate: false,
  },
  error: {
    label: "错误",
    color: "text-red-600",
    dotColor: "bg-red-500",
    animate: false,
  },
};
