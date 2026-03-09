import type { ChatMessage } from "@/types/openai";
import type {
  StudioConversationViewModel,
  StudioMessageRenderItem,
  StudioTimelineItem,
  ToolInvocationViewModel,
} from "@/types/realtime-ui";

function clip(value: string | null | undefined, size = 160): string {
  if (!value) return "";
  if (value.length <= size) return value;
  return `${value.slice(0, size)}...`;
}

function clockLabel(index: number): string {
  const minute = Math.floor(index / 2) + 1;
  const second = ((index * 13) % 60).toString().padStart(2, "0");
  return `00:${minute.toString().padStart(2, "0")}:${second}`;
}

function findToolResult(
  messages: ChatMessage[],
  fromIndex: number,
  toolCallId: string,
): { message: ChatMessage | null; index: number } {
  for (let idx = fromIndex; idx < messages.length; idx += 1) {
    const candidate = messages[idx];
    if (candidate.role === "tool" && candidate.tool_call_id === toolCallId) {
      return { message: candidate, index: idx };
    }

    if (candidate.role === "assistant" && candidate.tool_calls?.length) {
      return { message: null, index: -1 };
    }
  }

  return { message: null, index: -1 };
}

function buildToolCards(
  assistantMessage: ChatMessage,
  messages: ChatMessage[],
  cursor: number,
  consumed: Set<number>,
): ToolInvocationViewModel[] {
  const toolCalls = assistantMessage.tool_calls || [];

  return toolCalls.map((tool) => {
    const resultMatch = findToolResult(messages, cursor + 1, tool.id);
    if (resultMatch.index >= 0) {
      consumed.add(resultMatch.index);
    }

    return {
      id: tool.id,
      name: tool.function.name,
      argsPreview: clip(tool.function.arguments, 180) || "{}",
      resultPreview: clip(resultMatch.message?.content, 220) || "(pending)",
      hasResult: !!resultMatch.message,
    };
  });
}

function buildMetrics(
  items: StudioTimelineItem[],
): Array<{ label: string; value: string }> {
  const toolBundles = items.filter((item) => item.kind === "tool-bundle");
  const toolCount = toolBundles.reduce(
    (sum, item) => sum + (item.tools ? item.tools.length : 0),
    0,
  );
  const assistantCount = items.filter(
    (item) => item.role === "assistant",
  ).length;

  return [
    { label: "Timeline", value: String(items.length) },
    { label: "Assistant", value: String(assistantCount) },
    { label: "Tool Calls", value: String(toolCount) },
    {
      label: "Completion",
      value: `${Math.max(0, Math.min(100, Math.round((assistantCount / Math.max(1, items.length)) * 100)))}%`,
    },
  ];
}

export function buildStudioConversationViewModel(
  messages: ChatMessage[],
  options?: { title?: string; subtitle?: string },
): StudioConversationViewModel {
  const consumed = new Set<number>();
  const items: StudioTimelineItem[] = [];

  for (let i = 0; i < messages.length; i += 1) {
    if (consumed.has(i)) continue;

    const msg = messages[i];

    if (
      msg.role === "assistant" &&
      msg.tool_calls &&
      msg.tool_calls.length > 0
    ) {
      const tools = buildToolCards(msg, messages, i, consumed);

      let attachedAssistantNote = "";
      const next = messages[i + 1];
      if (
        next &&
        next.role === "assistant" &&
        (!next.tool_calls || next.tool_calls.length === 0)
      ) {
        // 对于推理模型，优先使用 content，如果为空则使用 reasoning_content
        const displayContent = next.content || next.reasoning_content || "";
        attachedAssistantNote = clip(displayContent, 260);
        consumed.add(i + 1);
      }

      items.push({
        id: msg.id || `assistant-tools-${i}`,
        kind: "tool-bundle",
        role: "assistant",
        title: "Tool Execution Group",
        body: "Assistant delegated one or multiple tools in this turn.",
        timestampLabel: clockLabel(i),
        tools,
        attachedAssistantNote,
      });
      continue;
    }

    if (msg.role === "assistant") {
      // 对于推理模型（如 DeepSeek-R1），content 可能为空，但 reasoning_content 有内容
      const displayContent = msg.content || msg.reasoning_content || "";
      items.push({
        id: msg.id || `assistant-${i}`,
        kind: "assistant",
        role: "assistant",
        title: msg.agent_name ? `Assistant (${msg.agent_name})` : "Assistant",
        body: clip(displayContent, 420),
        timestampLabel: clockLabel(i),
      });
      continue;
    }

    if (msg.role === "user") {
      items.push({
        id: msg.id || `user-${i}`,
        kind: "user",
        role: "user",
        title: "User Prompt",
        body: clip(msg.content, 360),
        timestampLabel: clockLabel(i),
      });
      continue;
    }

    if (msg.role === "tool") {
      items.push({
        id: msg.id || msg.tool_call_id || `tool-${i}`,
        kind: "tool-result",
        role: "tool",
        title: msg.name ? `Tool Result: ${msg.name}` : "Tool Result",
        body: clip(msg.content, 280),
        timestampLabel: clockLabel(i),
      });
      continue;
    }

    items.push({
      id: msg.id || `system-${i}`,
      kind: "system",
      role: "system",
      title: "System",
      body: clip(msg.content, 280),
      timestampLabel: clockLabel(i),
    });
  }

  return {
    title: options?.title || "Realtime Studio",
    subtitle:
      options?.subtitle ||
      "A structured timeline for prompts, tool orchestration, and assistant responses.",
    items,
    metrics: buildMetrics(items),
  };
}

export function buildMessageRenderItems(
  messages: ChatMessage[],
): StudioMessageRenderItem[] {
  console.log("[buildMessageRenderItems] Input messages:", messages.map(m => ({ role: m.role, id: m.id, tool_call_id: m.tool_call_id })));
  const consumedToolResultIds = new Set<string>();
  const consumedAssistantIndices = new Set<number>();
  const renderItems: StudioMessageRenderItem[] = [];

  for (let index = 0; index < messages.length; index += 1) {
    if (consumedAssistantIndices.has(index)) {
      continue;
    }

    const message = messages[index];
    if (
      message.role === "tool" &&
      message.tool_call_id &&
      consumedToolResultIds.has(message.tool_call_id)
    ) {
      continue;
    }

    let lastToolResultIndex = index;
    const toolResults =
      message.role === "assistant" && message.tool_calls?.length
        ? message.tool_calls
            .map((toolCall) => {
              for (
                let candidateIndex = index + 1;
                candidateIndex < messages.length;
                candidateIndex += 1
              ) {
                const candidate = messages[candidateIndex];
                if (
                  candidate.role === "tool" &&
                  candidate.tool_call_id === toolCall.id
                ) {
                  if (candidateIndex > lastToolResultIndex) {
                    lastToolResultIndex = candidateIndex;
                  }
                  if (candidate.tool_call_id) {
                    consumedToolResultIds.add(candidate.tool_call_id);
                  }
                  return candidate;
                }
              }

              return null;
            })
            .filter((item): item is ChatMessage => item !== null)
        : [];

    const attachedAssistant =
      message.role === "assistant" && message.tool_calls?.length
        ? (() => {
            for (
              let candidateIndex = lastToolResultIndex + 1;
              candidateIndex < messages.length;
              candidateIndex += 1
            ) {
              const candidate = messages[candidateIndex];

              if (candidate.role === "tool") {
                continue;
              }

              if (
                candidate.role === "assistant" &&
                !candidate.tool_calls?.length &&
                !!(candidate.content || candidate.reasoning_content || "").trim()
              ) {
                consumedAssistantIndices.add(candidateIndex);
                return candidate;
              }

              if (candidate.role === "user") {
                break;
              }

              if (
                candidate.role === "assistant" &&
                !!candidate.tool_calls?.length
              ) {
                break;
              }
            }

            return null;
          })()
        : null;

    renderItems.push({
      index,
      message,
      toolResults,
      attachedAssistant,
    });
  }

  console.log("[buildMessageRenderItems] Output renderItems:", renderItems.map(r => ({
    index: r.index,
    role: r.message.role,
    toolCallsCount: r.message.tool_calls?.length,
    toolResultsCount: r.toolResults?.length
  })));
  return renderItems;
}

export function buildDemoMessages(): ChatMessage[] {
  return [
    {
      id: "u-1",
      role: "user",
      content:
        "Please summarize this repository architecture and list quick wins.",
    },
    {
      id: "a-1",
      role: "assistant",
      content: "",
      tool_calls: [
        {
          id: "call-1",
          type: "function",
          function: {
            name: "search_subagent",
            arguments: '{"query":"repository architecture quick wins"}',
          },
        },
        {
          id: "call-2",
          type: "function",
          function: {
            name: "read_file",
            arguments: '{"filePath":"README.md","startLine":1,"endLine":200}',
          },
        },
      ],
    },
    {
      id: "t-1",
      role: "tool",
      tool_call_id: "call-1",
      name: "search_subagent",
      content: "Found 11 architecture documents and 4 migration guides.",
    },
    {
      id: "t-2",
      role: "tool",
      tool_call_id: "call-2",
      name: "read_file",
      content:
        "README documents the agent loop, hook lifecycle, and workspace tools.",
    },
    {
      id: "a-2",
      role: "assistant",
      content:
        "I found three quick wins: 1) remove duplicated message merge logic, 2) introduce typed timeline view model, and 3) centralize streaming placeholders.",
      agent_name: "TeamLeadAgent",
    },
  ];
}
