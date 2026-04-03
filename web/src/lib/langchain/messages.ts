/**
 * 自定义消息模型 - 继承 LangChain.js 基础类
 *
 * 提供带有业务字段扩展的自定义消息类。
 * 业务字段（id, createdAt, metadata）通过 additional_kwargs 存储，
 * 确保与 LangChain 序列化机制兼容。
 */

import {
  HumanMessage,
  AIMessage,
  SystemMessage,
  ToolMessage,
  type BaseMessageFields,
  type ToolMessageFieldsWithToolCall,
} from "@langchain/core/messages";

/**
 * 生成唯一ID
 */
function generateId(prefix: string = "msg"): string {
  return `${prefix}_${Math.random().toString(36).substring(2, 15)}`;
}

/**
 * 自定义用户消息 - 继承 LangChain HumanMessage
 *
 * 业务字段:
 *   - id: 消息唯一标识
 *   - createdAt: 创建时间 ISO 格式
 *   - metadata: 自定义元数据字典
 */
export class CustomHumanMessage extends HumanMessage {
  constructor(
    content: string,
    options?: {
      msgId?: string;
      createdAt?: string;
      metadata?: Record<string, any>;
    }
  ) {
    super({ content });

    // 业务字段存储在 additional_kwargs 中
    this.additional_kwargs = {
      id: options?.msgId || generateId("msg"),
      created_at: options?.createdAt || new Date().toISOString(),
      ...(options?.metadata && { metadata: options.metadata }),
    };
  }

  /** 消息ID */
  get msgId(): string {
    return (this.additional_kwargs?.id as string) || "";
  }

  /** 创建时间 */
  get createdAt(): string {
    return (this.additional_kwargs?.created_at as string) || "";
  }

  /** 元数据 */
  get metadata(): Record<string, any> {
    return (this.additional_kwargs?.metadata as Record<string, any>) || {};
  }

  toString(): string {
    return `CustomHumanMessage(id=${this.msgId}, content=${this.content.substring(0, 50)}...)`;
  }
}

/**
 * 自定义助手消息 - 继承 LangChain AIMessage
 *
 * 业务字段:
 *   - id: 消息唯一标识
 *   - createdAt: 创建时间 ISO 格式
 *   - metadata: 自定义元数据字典
 *   - agentName: Agent 名称
 *   - status: 消息状态 (streaming, completed, error)
 */
export class CustomAIMessage extends AIMessage {
  constructor(
    content: string,
    options?: {
      msgId?: string;
      createdAt?: string;
      metadata?: Record<string, any>;
      agentName?: string;
      status?: string;
      toolCalls?: Array<{
        id: string;
        type: string;
        function: { name: string; arguments: string };
      }>;
    }
  ) {
    super({
      content,
      tool_calls: options?.toolCalls,
    });

    // 业务字段存储在 additional_kwargs 中
    this.additional_kwargs = {
      id: options?.msgId || generateId("msg"),
      created_at: options?.createdAt || new Date().toISOString(),
      ...(options?.metadata && { metadata: options.metadata }),
      ...(options?.agentName && { agent_name: options.agentName }),
      ...(options?.status && { status: options.status }),
    };
  }

  /** 消息ID */
  get msgId(): string {
    return (this.additional_kwargs?.id as string) || "";
  }

  /** 创建时间 */
  get createdAt(): string {
    return (this.additional_kwargs?.created_at as string) || "";
  }

  /** 元数据 */
  get metadata(): Record<string, any> {
    return (this.additional_kwargs?.metadata as Record<string, any>) || {};
  }

  /** Agent 名称 */
  get agentName(): string {
    return (this.additional_kwargs?.agent_name as string) || "";
  }

  /** 消息状态 */
  get status(): string {
    return (this.additional_kwargs?.status as string) || "completed";
  }

  toString(): string {
    const toolCount = this.tool_calls?.length || 0;
    return `CustomAIMessage(id=${this.msgId}, content=${this.content.substring(0, 50)}..., tool_calls=${toolCount})`;
  }
}

/**
 * 自定义系统消息 - 继承 LangChain SystemMessage
 *
 * 业务字段:
 *   - id: 消息唯一标识
 *   - createdAt: 创建时间 ISO 格式
 *   - metadata: 自定义元数据字典
 */
export class CustomSystemMessage extends SystemMessage {
  constructor(
    content: string,
    options?: {
      msgId?: string;
      createdAt?: string;
      metadata?: Record<string, any>;
    }
  ) {
    super({ content });

    // 业务字段存储在 additional_kwargs 中
    this.additional_kwargs = {
      id: options?.msgId || generateId("msg"),
      created_at: options?.createdAt || new Date().toISOString(),
      ...(options?.metadata && { metadata: options.metadata }),
    };
  }

  /** 消息ID */
  get msgId(): string {
    return (this.additional_kwargs?.id as string) || "";
  }

  /** 创建时间 */
  get createdAt(): string {
    return (this.additional_kwargs?.created_at as string) || "";
  }

  /** 元数据 */
  get metadata(): Record<string, any> {
    return (this.additional_kwargs?.metadata as Record<string, any>) || {};
  }

  toString(): string {
    return `CustomSystemMessage(id=${this.msgId}, content=${this.content.substring(0, 50)}...)`;
  }
}

/**
 * 自定义工具消息 - 继承 LangChain ToolMessage
 *
 * 业务字段:
 *   - id: 消息唯一标识
 *   - createdAt: 创建时间 ISO 格式
 *   - metadata: 自定义元数据字典
 *   - toolName: 工具名称（冗余存储便于访问）
 *   - durationMs: 工具执行耗时
 */
export class CustomToolMessage extends ToolMessage {
  constructor(
    content: string,
    toolCallId: string,
    options?: {
      msgId?: string;
      createdAt?: string;
      metadata?: Record<string, any>;
      toolName?: string;
      durationMs?: number;
    }
  ) {
    super({
      content,
      tool_call_id: toolCallId,
    });

    // 业务字段存储在 additional_kwargs 中
    this.additional_kwargs = {
      id: options?.msgId || generateId("msg"),
      created_at: options?.createdAt || new Date().toISOString(),
      ...(options?.metadata && { metadata: options.metadata }),
      ...(options?.toolName && { tool_name: options.toolName }),
      ...(options?.durationMs !== undefined && { duration_ms: options.durationMs }),
    };
  }

  /** 消息ID */
  get msgId(): string {
    return (this.additional_kwargs?.id as string) || "";
  }

  /** 创建时间 */
  get createdAt(): string {
    return (this.additional_kwargs?.created_at as string) || "";
  }

  /** 元数据 */
  get metadata(): Record<string, any> {
    return (this.additional_kwargs?.metadata as Record<string, any>) || {};
  }

  /** 工具名称 */
  get toolName(): string {
    return (this.additional_kwargs?.tool_name as string) || "";
  }

  /** 执行耗时（毫秒） */
  get durationMs(): number | undefined {
    return this.additional_kwargs?.duration_ms as number | undefined;
  }

  toString(): string {
    return `CustomToolMessage(id=${this.msgId}, tool_call_id=${this.tool_call_id}, tool_name=${this.toolName}, content=${this.content.substring(0, 50)}...)`;
  }
}

// ═══════════════════════════════════════════════════════════
// 工厂方法
// ═══════════════════════════════════════════════════════════

/**
 * 创建用户消息
 */
export function createHuman(
  content: string,
  options?: ConstructorParameters<typeof CustomHumanMessage>[1]
): CustomHumanMessage {
  return new CustomHumanMessage(content, options);
}

/**
 * 创建助手消息
 */
export function createAI(
  content: string,
  options?: ConstructorParameters<typeof CustomAIMessage>[1]
): CustomAIMessage {
  return new CustomAIMessage(content, options);
}

/**
 * 创建系统消息
 */
export function createSystem(
  content: string,
  options?: ConstructorParameters<typeof CustomSystemMessage>[1]
): CustomSystemMessage {
  return new CustomSystemMessage(content, options);
}

/**
 * 创建工具消息
 */
export function createTool(
  content: string,
  toolCallId: string,
  options?: Omit<ConstructorParameters<typeof CustomToolMessage>[2], "toolCallId">
): CustomToolMessage {
  return new CustomToolMessage(content, toolCallId, options);
}

// ═══════════════════════════════════════════════════════════
// 类型导出
// ═══════════════════════════════════════════════════════════

export type CustomMessage =
  | CustomHumanMessage
  | CustomAIMessage
  | CustomSystemMessage
  | CustomToolMessage;
