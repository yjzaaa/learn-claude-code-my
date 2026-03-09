"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/openai";
import { ToolNameLabel } from "./tool-name-label";
import { RoleLabel } from "./agent-type-label";
import { ChevronDown, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface CollapsibleMessageProps {
  message: ChatMessage;
  toolResults?: ChatMessage[];
  attachedAssistant?: ChatMessage | null;
  isStreaming?: boolean;
  /** 流式内容（增量更新） */
  streamingContent?: string;
  /** 流式推理内容 */
  streamingReasoning?: string;
  className?: string;
  defaultExpanded?: boolean;
}

function BreathingEllipsis() {
  return (
    <span
      className="inline-flex items-center gap-0.5 text-zinc-500 dark:text-zinc-400"
      aria-label="empty content"
    >
      <span className="animate-pulse" style={{ animationDelay: "0ms" }}>
        .
      </span>
      <span className="animate-pulse" style={{ animationDelay: "180ms" }}>
        .
      </span>
      <span className="animate-pulse" style={{ animationDelay: "360ms" }}>
        .
      </span>
    </span>
  );
}

function normalizeMarkdownInput(raw: string): string {
  const text = (raw || "").trim();
  if (!text) return "";

  // If message already uses fenced code blocks, keep it untouched.
  if (text.includes("```")) {
    return raw;
  }

  // Promote JSON-looking payloads to fenced code blocks for stable rendering.
  const looksLikeJson =
    (text.startsWith("{") && text.endsWith("}")) ||
    (text.startsWith("[") && text.endsWith("]"));

  if (!looksLikeJson) {
    return raw;
  }

  try {
    const parsed = JSON.parse(text);
    return `\`\`\`json\n${JSON.stringify(parsed, null, 2)}\n\`\`\``;
  } catch {
    return raw;
  }
}

export function CollapsibleMessage({
  message,
  toolResults = [],
  attachedAssistant = null,
  isStreaming = false,
  streamingContent,
  streamingReasoning,
  className,
  defaultExpanded = false,
}: CollapsibleMessageProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [expandedToolIds, setExpandedToolIds] = useState<
    Record<string, boolean>
  >({});

  const isToolCall =
    message.role === "assistant" &&
    message.tool_calls &&
    message.tool_calls.length > 0;
  const isToolResult = message.role === "tool";
  const displayContent = streamingContent ?? message.content ?? "";
  const attachedAssistantContent = attachedAssistant?.content ?? "";
  const hasContent = !!displayContent || isToolCall || !!streamingReasoning;
  const showExpandButton = hasContent || isStreaming;

  const truncate = (value: string | null | undefined, limit = 120): string => {
    if (!value) return "...";
    return value.length > limit ? `${value.slice(0, limit)}...` : value;
  };

  const previewText = useMemo(() => {
    if (isToolCall) {
      const firstTool = message.tool_calls?.[0];
      const firstResult = firstTool
        ? toolResults.find((result) => result.tool_call_id === firstTool.id)
        : null;
      const toolName = firstTool?.function.name || "unknown_tool";
      const argsPreview = truncate(firstTool?.function.arguments, 70);
      const resultPreview = truncate(firstResult?.content, 70);
      const assistantPreview = truncate(
        displayContent || attachedAssistantContent,
        50,
      );
      return `${toolName} | 参数: ${argsPreview} | 结果: ${resultPreview} | 说明: ${assistantPreview}`;
    }
    if (isToolResult) {
      return "工具执行结果";
    }
    if (streamingReasoning) {
      return `思考中: ${streamingReasoning.slice(0, 72)}${streamingReasoning.length > 72 ? "..." : ""}`;
    }
    if (!displayContent) {
      return "...";
    }
    return (
      displayContent.slice(0, 120) + (displayContent.length > 120 ? "..." : "")
    );
  }, [
    displayContent,
    attachedAssistantContent,
    isToolCall,
    isToolResult,
    message.tool_calls,
    streamingReasoning,
    toolResults,
  ]);

  const normalizedDisplayContent = useMemo(
    () => normalizeMarkdownInput(displayContent),
    [displayContent],
  );

  const normalizedAttachedAssistantContent = useMemo(
    () => normalizeMarkdownInput(attachedAssistantContent),
    [attachedAssistantContent],
  );

  const toggleToolExpanded = (toolId: string) => {
    setExpandedToolIds((prev) => ({
      ...prev,
      [toolId]: !prev[toolId],
    }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "rounded-lg border bg-white shadow-sm",
        "dark:bg-zinc-900 dark:border-zinc-700",
        className,
      )}
    >
      <div
        className={cn(
          "flex items-center justify-between px-3 py-2.5",
          "border-b border-zinc-100 dark:border-zinc-800",
          showExpandButton &&
            "cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
          "transition-colors",
        )}
        onClick={() => showExpandButton && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2.5">
          <RoleLabel
            role={message.role}
            size="sm"
            agentName={message.agent_name}
          />

          {isToolCall && message.tool_calls?.[0] && (
            <ToolNameLabel
              toolName={message.tool_calls[0].function.name}
              size="sm"
            />
          )}

          {isToolResult && message.name && (
            <ToolNameLabel toolName={message.name} size="sm" />
          )}

          {isStreaming && (
            <span className="text-xs text-blue-500 animate-pulse">
              流式传输中...
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {showExpandButton && (
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDown className="h-4 w-4 text-zinc-400" />
            </motion.div>
          )}
        </div>
      </div>

      {!isExpanded && (
        <div className="px-3 py-2.5">
          <p className="line-clamp-2 text-sm leading-6 text-zinc-700 dark:text-zinc-300">
            {previewText}
          </p>
        </div>
      )}

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 py-3 border-b border-zinc-100 dark:border-zinc-800">
              {isToolCall ? (
                <div className="space-y-3">
                  {message.tool_calls?.map((toolCall) => (
                    <div
                      key={toolCall.id}
                      className="rounded-lg border border-zinc-300 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50"
                    >
                      <div
                        className="mb-2 flex cursor-pointer items-center justify-between gap-2 rounded px-1 py-1 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                        onClick={() => toggleToolExpanded(toolCall.id)}
                      >
                        <div className="flex items-center gap-2">
                          <ToolNameLabel
                            toolName={toolCall.function.name}
                            size="sm"
                          />
                          <span className="text-[11px] text-zinc-600 dark:text-zinc-300">
                            Tool Execution
                          </span>
                        </div>
                        {expandedToolIds[toolCall.id] ? (
                          <ChevronDown className="h-4 w-4 text-zinc-400" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-zinc-400" />
                        )}
                      </div>

                      {!expandedToolIds[toolCall.id] ? (
                        <div className="rounded-md border border-zinc-200 bg-white p-2 text-xs text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900/70 dark:text-zinc-300">
                          <p className="line-clamp-1">
                            参数: {truncate(toolCall.function.arguments, 120)}
                          </p>
                          <p className="line-clamp-1">
                            结果:{" "}
                            {truncate(
                              toolResults.find(
                                (result) => result.tool_call_id === toolCall.id,
                              )?.content,
                              120,
                            )}
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-2 rounded-md border border-zinc-200 bg-white p-2.5 dark:border-zinc-700 dark:bg-zinc-900/70">
                          <div>
                            <p className="mb-1 text-[11px] font-semibold text-zinc-500">
                              参数
                            </p>
                            <p className="whitespace-pre-wrap break-words rounded border border-zinc-200 bg-zinc-50 px-2 py-1.5 text-xs leading-6 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
                              {truncate(toolCall.function.arguments, 400)}
                            </p>
                          </div>

                          <div>
                            <p className="mb-1 text-[11px] font-semibold text-zinc-500">
                              执行结果
                            </p>
                            <p className="whitespace-pre-wrap break-words rounded border border-zinc-200 bg-zinc-50 px-2 py-1.5 text-xs leading-6 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
                              {truncate(
                                toolResults.find(
                                  (result) =>
                                    result.tool_call_id === toolCall.id,
                                )?.content,
                                500,
                              )}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}

                  {(displayContent || attachedAssistantContent) && (
                    <div className="rounded-lg border border-zinc-300 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50">
                      <p className="mb-1 text-[11px] font-semibold text-zinc-500">
                        Assistant 附加说明
                      </p>
                      <div className="chat-markdown rounded border border-zinc-200 bg-zinc-50 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-900">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {normalizedDisplayContent ||
                            normalizedAttachedAssistantContent}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}

                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                  )}
                </div>
              ) : isToolResult ? (
                <div className="rounded-lg border border-emerald-200/70 bg-emerald-50/70 p-3 dark:border-emerald-900/40 dark:bg-emerald-950/20">
                  <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-emerald-900 dark:text-emerald-200">
                    {truncate(message.content, 500)}
                  </pre>
                </div>
              ) : (
                <div className="space-y-3">
                  {streamingReasoning && (
                    <div className="rounded-md bg-amber-50 dark:bg-amber-950/20 p-3 border border-amber-200 dark:border-amber-900/30">
                      <p className="text-[10px] text-amber-600 dark:text-amber-400 mb-1 font-medium">
                        思考过程
                      </p>
                      <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-amber-800 dark:text-amber-300">
                        {streamingReasoning}
                      </pre>
                    </div>
                  )}
                  <div className="chat-markdown max-w-none rounded-lg border border-zinc-200 bg-zinc-50/70 p-3 dark:border-zinc-700 dark:bg-zinc-900/60">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {normalizedDisplayContent || ""}
                    </ReactMarkdown>
                    {!displayContent && !isStreaming && <BreathingEllipsis />}
                    {isStreaming && (
                      <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                    )}
                  </div>
                  {isStreaming && !displayContent && (
                    <p className="text-xs text-zinc-500">等待模型输出...</p>
                  )}
                  {isStreaming && displayContent && (
                    <p className="text-[11px] text-zinc-500">
                      持续生成中
                      {isStreaming && (
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 ml-1 animate-pulse" />
                      )}
                    </p>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
