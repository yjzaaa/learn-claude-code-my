"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/openai";
<<<<<<< HEAD
import { ToolNameLabel } from "./tool-name-label";
import { RoleLabel } from "./agent-type-label";
import { ChevronDown, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
=======
import { parseToolCallArguments } from "@/types/openai";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Terminal,
  CheckCircle2,
  Wrench,
  Bot,
  User,
  MessageSquare,
  ChevronDown,
  Copy,
  Check,
} from "lucide-react";

// 动态导入 react-json-view（避免 SSR 问题）
const ReactJson = dynamic(() => import("@microlink/react-json-view"), {
  ssr: false,
  loading: () => (
    <div className="p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg text-sm">
      加载 JSON 查看器...
    </div>
  ),
});
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)

interface CollapsibleMessageProps {
  message: ChatMessage;
  toolResults?: ChatMessage[];
  attachedAssistant?: ChatMessage | null;
  isStreaming?: boolean;
  streamingContent?: string;
  streamingReasoning?: string;
  className?: string;
  defaultExpanded?: boolean;
}

<<<<<<< HEAD
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
=======
/** 消息类型配置 */
const messageTypeConfig = {
  user: {
    icon: User,
    label: "用户",
    bgColor: "bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/30 dark:to-blue-900/20",
    borderColor: "border-blue-200 dark:border-blue-800",
    headerBg: "bg-blue-500",
    textColor: "text-blue-900 dark:text-blue-100",
  },
  assistant: {
    icon: Bot,
    label: "助手",
    bgColor: "bg-white dark:bg-zinc-900",
    borderColor: "border-zinc-200 dark:border-zinc-700",
    headerBg: "bg-gradient-to-r from-zinc-700 to-zinc-600 dark:from-zinc-600 dark:to-zinc-500",
    textColor: "text-zinc-800 dark:text-zinc-100",
  },
  tool: {
    icon: Terminal,
    label: "工具结果",
    bgColor: "bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950/30 dark:to-emerald-900/20",
    borderColor: "border-emerald-200 dark:border-emerald-800",
    headerBg: "bg-emerald-500",
    textColor: "text-emerald-900 dark:text-emerald-100",
  },
  system: {
    icon: MessageSquare,
    label: "系统",
    bgColor: "bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950/30 dark:to-amber-900/20",
    borderColor: "border-amber-200 dark:border-amber-800",
    headerBg: "bg-amber-500",
    textColor: "text-amber-900 dark:text-amber-100",
  },
};

/** 代码复制按钮 */
function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded-md bg-zinc-700/80 hover:bg-zinc-600 text-zinc-300 transition-colors"
      title="复制代码"
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

/** 代码块组件 */
function CodeBlock({ code, language }: { code: string; language: string }) {
  return (
    <div className="relative my-3 rounded-lg overflow-hidden border border-zinc-700">
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-800 border-b border-zinc-700">
        <span className="text-xs text-zinc-400 font-mono">{language || "text"}</span>
        <CopyButton code={code} />
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: "1rem",
          fontSize: "0.8125rem",
          lineHeight: "1.6",
          backgroundColor: "#1e1e1e",
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)
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
<<<<<<< HEAD
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [expandedToolIds, setExpandedToolIds] = useState<
    Record<string, boolean>
  >({});

=======
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)
  const isToolCall =
    message.role === "assistant" &&
    message.tool_calls &&
    message.tool_calls.length > 0;
  const isToolResult = message.role === "tool";
<<<<<<< HEAD
  const displayContent = streamingContent ?? message.content ?? "";
  const attachedAssistantContent = attachedAssistant?.content ?? "";
  const hasContent = !!displayContent || isToolCall || !!streamingReasoning;
  const showExpandButton = hasContent || isStreaming;
=======

  const displayContent = streamingContent ?? message.content ?? "";

  const config = messageTypeConfig[message.role] || messageTypeConfig.assistant;
  const Icon = config.icon;

  // 决定是否使用 Accordion（有内容可展开时）
  const hasExpandableContent =
    isToolCall || isToolResult || displayContent.length > 100;
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)

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
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className={cn(
<<<<<<< HEAD
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
=======
        "rounded-2xl border shadow-sm overflow-hidden backdrop-blur-sm",
        config.bgColor,
        config.borderColor,
        className
      )}
    >
      {hasExpandableContent ? (
        <Accordion
          type="single"
          collapsible
          defaultValue={defaultExpanded ? "content" : undefined}
        >
          <AccordionItem value="content" className="border-0">
            <AccordionTrigger
              className={cn(
                "px-4 py-3 hover:no-underline [&[data-state=open]>div>div>svg]:rotate-180",
                "transition-all duration-200"
              )}
            >
              <MessageHeader
                message={message}
                config={config}
                Icon={Icon}
                isStreaming={isStreaming}
                isToolCall={!!isToolCall}
                isToolResult={!!isToolResult}
              />
            </AccordionTrigger>
            <AccordionContent className="px-4 pb-4">
              <MessageContent
                message={message}
                displayContent={displayContent}
                streamingReasoning={streamingReasoning}
                isStreaming={isStreaming}
                isToolCall={!!isToolCall}
                isToolResult={!!isToolResult}
              />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      ) : (
        <div>
          <div className="px-4 py-3">
            <MessageHeader
              message={message}
              config={config}
              Icon={Icon}
              isStreaming={isStreaming}
              isToolCall={!!isToolCall}
              isToolResult={!!isToolResult}
            />
          </div>
          <div className="px-4 pb-4">
            <MessageContent
              message={message}
              displayContent={displayContent}
              streamingReasoning={streamingReasoning}
              isStreaming={isStreaming}
              isToolCall={!!isToolCall}
              isToolResult={!!isToolResult}
            />
          </div>
        </div>
      )}
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)
    </motion.div>
  );
}

/** 消息头部组件 */
function MessageHeader({
  message,
  config,
  Icon,
  isStreaming,
  isToolCall,
  isToolResult,
}: {
  message: ChatMessage;
  config: (typeof messageTypeConfig)["user"];
  Icon: React.ElementType;
  isStreaming: boolean;
  isToolCall: boolean;
  isToolResult: boolean;
}) {
  return (
    <div className="flex items-center gap-3 w-full pr-4">
      {/* 图标 */}
      <div
        className={cn(
          "flex items-center justify-center w-8 h-8 rounded-xl shrink-0 shadow-sm",
          config.headerBg,
          "text-white"
        )}
      >
        <Icon className="h-4 w-4" />
      </div>

      {/* 角色和标签 */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className={cn("font-semibold text-sm", config.textColor)}>
          {message.role === "assistant" && message.agent_name
            ? message.agent_name
            : config.label}
        </span>

        {/* 工具调用标识 */}
        {isToolCall && message.tool_calls?.[0] && (
          <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 shrink-0 font-medium">
            <Wrench className="h-3 w-3" />
            {message.tool_calls[0].function.name}
          </span>
        )}

        {/* 工具结果标识 */}
        {isToolResult && message.name && (
          <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 shrink-0 font-medium">
            <CheckCircle2 className="h-3 w-3" />
            {message.name}
          </span>
        )}

        {/* 流式指示器 */}
        {isStreaming && (
          <span className="flex items-center gap-1.5 text-xs text-blue-500 ml-auto shrink-0 font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            生成中...
          </span>
        )}
      </div>

      {/* 展开箭头 */}
      <ChevronDown className="h-4 w-4 text-zinc-400 transition-transform duration-200 shrink-0" />
    </div>
  );
}

/** 消息内容组件 */
function MessageContent({
  message,
  displayContent,
  streamingReasoning,
  isStreaming,
  isToolCall,
  isToolResult,
}: {
  message: ChatMessage;
  displayContent: string;
  streamingReasoning?: string;
  isStreaming: boolean;
  isToolCall: boolean;
  isToolResult: boolean;
}) {
  // 工具调用：显示 JSON 参数 + 助手内容
  if (isToolCall) {
    return (
      <div className="space-y-4">
        {/* 先显示助手的内容（如果有） */}
        {displayContent && (
          <div className={cn("text-sm", !isToolResult && "pb-3 border-b border-zinc-200 dark:border-zinc-800")}>
            <MarkdownContent content={displayContent} isStreaming={isStreaming} />
          </div>
        )}
        {/* 显示工具调用 */}
        {message.tool_calls?.map((toolCall) => {
          const args = parseToolCallArguments(toolCall);
          return (
            <div
              key={toolCall.id}
              className="rounded-xl border border-purple-200 dark:border-purple-800 overflow-hidden shadow-sm"
            >
              <div className="bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-950/50 dark:to-purple-900/30 px-4 py-2.5 flex items-center gap-2">
                <Wrench className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                <span className="font-semibold text-sm text-purple-700 dark:text-purple-300">
                  {toolCall.function.name}
                </span>
              </div>
              <div className="p-4 bg-white dark:bg-zinc-950">
                <ReactJson
                  src={args}
                  collapsed={true}
                  collapseStringsAfterLength={50}
                  enableClipboard={true}
                  displayDataTypes={false}
                  displayObjectSize={false}
                  theme="rjv-default"
                  style={{
                    backgroundColor: "transparent",
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // 工具结果：显示代码块
  if (isToolResult) {
    const content = message.content || "";
    const formattedContent = useMemo(() => {
      try {
        const parsed = JSON.parse(content);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return content;
      }
    }, [content]);

    return (
      <div>
        <div className="flex items-center gap-2 mb-3">
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          <span className="font-semibold text-sm text-emerald-700 dark:text-emerald-300">
            执行结果
          </span>
        </div>
        <CodeBlock code={formattedContent} language="json" />
      </div>
    );
  }

  // 普通消息
  return (
    <div className="space-y-3">
      {/* 推理内容 */}
      {streamingReasoning && (
        <div className="rounded-lg bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/20 p-3 border border-amber-200 dark:border-amber-800/50">
          <p className="text-xs text-amber-600 dark:text-amber-400 mb-1 font-semibold uppercase tracking-wider">
            思考过程
          </p>
          <p className="text-sm text-amber-800 dark:text-amber-200 whitespace-pre-wrap leading-relaxed">
            {streamingReasoning}
          </p>
        </div>
      )}

      {/* 主内容 - Markdown 渲染 */}
      <MarkdownContent content={displayContent} isStreaming={isStreaming} />
    </div>
  );
}

/** Markdown 内容渲染组件 */
function MarkdownContent({
  content,
  isStreaming,
}: {
  content: string;
  isStreaming: boolean;
}) {
  if (!content || content.trim() === "") {
    return null;
  }

  return (
    <div className="markdown-body text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 标题样式
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 mt-4 mb-3 pb-2 border-b-2 border-zinc-200 dark:border-zinc-700">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-bold text-blue-700 dark:text-blue-400 mt-4 mb-2 flex items-center gap-2">
              <span className="w-1 h-5 bg-blue-500 rounded-full"></span>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold text-zinc-800 dark:text-zinc-200 mt-3 mb-2">
              {children}
            </h3>
          ),
          // 段落
          p: ({ children }) => (
            <p className="text-zinc-700 dark:text-zinc-300 mb-3 last:mb-0">
              {children}
            </p>
          ),
          // 列表
          ul: ({ children }) => (
            <ul className="list-disc list-inside my-2 space-y-1 text-zinc-700 dark:text-zinc-300">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside my-2 space-y-1 text-zinc-700 dark:text-zinc-300">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="marker:text-blue-500">{children}</li>
          ),
          // 加粗
          strong: ({ children }) => (
            <strong className="font-bold text-zinc-900 dark:text-zinc-100">
              {children}
            </strong>
          ),
          // 斜体
          em: ({ children }) => (
            <em className="italic text-zinc-600 dark:text-zinc-400">{children}</em>
          ),
          // 行内代码
          code: ({ node, inline, className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";
            const code = String(children).replace(/\n$/, "");

            if (inline || !language) {
              return (
                <code
                  className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 rounded-md text-xs font-mono text-pink-600 dark:text-pink-400 border border-zinc-200 dark:border-zinc-700"
                  {...props}
                >
                  {children}
                </code>
              );
            }

            return <CodeBlock code={code} language={language} />;
          },
          // 代码块容器
          pre: ({ children }) => <>{children}</>,
          // 引用
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-blue-400 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-600 pl-4 py-2 pr-3 my-3 rounded-r-lg italic text-zinc-600 dark:text-zinc-400">
              {children}
            </blockquote>
          ),
          // 链接
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline underline-offset-2 font-medium transition-colors"
            >
              {children}
            </a>
          ),
          // 表格
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-zinc-200 dark:border-zinc-700">
              <table className="w-full text-sm border-collapse">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-zinc-100 dark:bg-zinc-800">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="border-b border-zinc-200 dark:border-zinc-700 px-4 py-2.5 text-left font-semibold text-zinc-700 dark:text-zinc-300">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-zinc-100 dark:border-zinc-800 px-4 py-2.5 text-zinc-600 dark:text-zinc-400">
              {children}
            </td>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
              {children}
            </tr>
          ),
          // 分隔线
          hr: () => (
            <hr className="my-4 border-zinc-200 dark:border-zinc-700" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>

      {/* 流式指示器 */}
      {isStreaming && (
        <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse rounded-sm" />
      )}
    </div>
  );
}
