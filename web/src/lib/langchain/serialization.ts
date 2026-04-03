/**
 * 消息序列化层 - 支持 LangChain 格式转换
 *
 * 提供自定义消息类与 LangChain 标准 JSON 格式之间的转换。
 */

import {
  HumanMessage,
  AIMessage,
  SystemMessage,
  ToolMessage,
  type BaseMessage,
  messagesToDict,
  mapStoredMessagesToChatMessages,
} from "@langchain/core/messages";
import {
  CustomHumanMessage,
  CustomAIMessage,
  CustomSystemMessage,
  CustomToolMessage,
  type CustomMessage,
} from "./messages";

/**
 * LangChain 标准消息格式 (序列化后)
 */
export interface LangChainMessageDict {
  type: string;
  data: {
    content: string;
    additional_kwargs?: Record<string, any>;
    tool_calls?: Array<{
      id: string;
      type: string;
      function: { name: string; arguments: string };
    }>;
    tool_call_id?: string;
  };
}

/**
 * 序列化单个消息为 LangChain 标准格式
 */
export function serializeMessage(message: BaseMessage): LangChainMessageDict {
  const dict = messagesToDict([message])[0];
  return dict as LangChainMessageDict;
}

/**
 * 序列化消息列表为 LangChain 标准格式
 */
export function serializeMessageList(
  messages: BaseMessage[]
): LangChainMessageDict[] {
  return messagesToDict(messages) as LangChainMessageDict[];
}

/**
 * 反序列化消息（LangChain 格式 -> 自定义消息类）
 */
export function deserializeMessage(
  data: LangChainMessageDict
): CustomMessage {
  const type = data.type;
  const content = data.data.content || "";
  const additionalKwargs = data.data.additional_kwargs || {};

  const baseOptions = {
    msgId: additionalKwargs.id,
    createdAt: additionalKwargs.created_at,
    metadata: additionalKwargs.metadata,
  };

  switch (type) {
    case "human":
      return new CustomHumanMessage(content, baseOptions);

    case "ai":
      return new CustomAIMessage(content, {
        ...baseOptions,
        agentName: additionalKwargs.agent_name,
        status: additionalKwargs.status,
        toolCalls: data.data.tool_calls,
      });

    case "system":
      return new CustomSystemMessage(content, baseOptions);

    case "tool":
      return new CustomToolMessage(
        content,
        data.data.tool_call_id || "",
        {
          ...baseOptions,
          toolName: additionalKwargs.tool_name,
          durationMs: additionalKwargs.duration_ms,
        }
      );

    default:
      throw new Error(`Unknown message type: ${type}`);
  }
}

/**
 * 反序列化消息列表
 */
export function deserializeMessageList(
  dataList: LangChainMessageDict[]
): CustomMessage[] {
  return dataList.map(deserializeMessage);
}

/**
 * 旧格式消息检测
 */
export function isLegacyFormat(data: any): boolean {
  if (typeof data !== "object" || data === null) {
    return false;
  }
  // 旧格式: { role: "user", content: "..." }
  // 新格式: { type: "human", data: { content: "..." } }
  return "role" in data && !("type" in data && "data" in data);
}

/**
 * 将旧格式消息转换为 LangChain 格式
 */
export function convertLegacyToLangChain(data: any): LangChainMessageDict {
  const role = data.role || "";
  const content = data.content || "";

  // 角色映射
  const roleMap: Record<string, string> = {
    user: "human",
    assistant: "ai",
    system: "system",
    tool: "tool",
  };

  const msgType = roleMap[role] || "human";

  const result: LangChainMessageDict = {
    type: msgType,
    data: { content },
  };

  // 收集业务字段
  const additionalKwargs: Record<string, any> = {};

  if (data.id) additionalKwargs.id = data.id;
  if (data.created_at) additionalKwargs.created_at = data.created_at;
  if (data.metadata) additionalKwargs.metadata = data.metadata;
  if (data.agent_name) additionalKwargs.agent_name = data.agent_name;
  if (data.status) additionalKwargs.status = data.status;

  // 工具调用特殊处理
  if (msgType === "tool") {
    result.data.tool_call_id = data.tool_call_id || "";
    if (data.name) additionalKwargs.tool_name = data.name;
  }

  // 工具调用列表
  if (data.tool_calls && Array.isArray(data.tool_calls)) {
    result.data.tool_calls = data.tool_calls;
  }

  // 添加 additional_kwargs 如果非空
  if (Object.keys(additionalKwargs).length > 0) {
    result.data.additional_kwargs = additionalKwargs;
  }

  return result;
}

/**
 * 批量转换旧格式消息列表
 */
export function convertLegacyListToLangChain(
  dataList: any[]
): LangChainMessageDict[] {
  return dataList.map((d) =>
    isLegacyFormat(d) ? convertLegacyToLangChain(d) : d
  );
}

/**
 * 从存储数据恢复消息列表（支持旧格式自动转换）
 */
export function restoreMessagesFromStorage(
  dataList: any[]
): CustomMessage[] {
  if (!Array.isArray(dataList) || dataList.length === 0) {
    return [];
  }

  // 检测并转换旧格式
  const normalizedData = dataList.map((d) =>
    isLegacyFormat(d) ? convertLegacyToLangChain(d) : d
  );

  return deserializeMessageList(normalizedData);
}
