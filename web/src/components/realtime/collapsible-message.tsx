"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/openai";
import { parseToolCallArguments } from "@/types/openai";
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
  ChevronRight,
  Copy,
  Check,
  Loader2,
  Sparkles,
  Brain,
  Code2,
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

interface CollapsibleMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
  streamingContent?: string;
  streamingReasoning?: string;
  className?: string;
  defaultExpanded?: boolean;
  toolResults?: ChatMessage[];
  attachedAssistant?: ChatMessage | null;
}

/** 消息类型配置 */
const messageTypeConfig = {
  user: {
    icon: User,
    label: "用户",
    bgColor:
      "bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/30 dark:to-blue-900/20",
    borderColor: "border-blue-200 dark:border-blue-800",
    headerBg: "bg-blue-500",
    textColor: "text-blue-900 dark:text-blue-100",
  },
  assistant: {
    icon: Bot,
    label: "助手",
    bgColor: "bg-white dark:bg-zinc-900",
    borderColor: "border-zinc-200/60 dark:border-zinc-700/60",
    headerBg:
      "bg-gradient-to-r from-zinc-700 to-zinc-600 dark:from-zinc-600 dark:to-zinc-500",
    textColor: "text-zinc-800 dark:text-zinc-100",
  },
  tool: {
    icon: Terminal,
    label: "工具结果",
    bgColor:
      "bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950/30 dark:to-emerald-900/20",
    borderColor: "border-emerald-200 dark:border-emerald-800",
    headerBg: "bg-emerald-500",
    textColor: "text-emerald-900 dark:text-emerald-100",
  },
  system: {
    icon: MessageSquare,
    label: "系统",
    bgColor:
      "bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950/30 dark:to-amber-900/20",
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
      {copied ? (
        <Check className="h-3.5 w-3.5" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

/** 代码块组件 */
function CodeBlock({ code, language }: { code: string; language: string }) {
  return (
    <div className="relative my-3 rounded-lg overflow-hidden border border-zinc-700">
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-800 border-b border-zinc-700">
        <span className="text-xs text-zinc-400 font-mono">
          {language || "text"}
        </span>
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
}

function formatToolArguments(rawArgs: string): string {
  try {
    const parsed = JSON.parse(rawArgs);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return rawArgs;
  }
}

function hasVisibleText(value: string | null | undefined): boolean {
  // 处理 undefined、null、空字符串、以及字符串 "undefined" 的情况
  if (!value || value === "undefined") return false;
  return value.trim().length > 0;
}

/** 固定高度滚动区域组件 */
function FixedHeightSection({
  title,
  icon: Icon,
  iconColorClass,
  headerBgClass,
  borderColorClass,
  isExpanded,
  onToggle,
  children,
  isActive,
  isStreaming,
  streamLabel,
  contentClassName,
  collapsedHeight = 120,
  expandedHeight = 400,
  hasContent = true,
}: {
  title: string;
  icon: React.ElementType;
  iconColorClass: string;
  headerBgClass: string;
  borderColorClass: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  isActive?: boolean;
  isStreaming?: boolean;
  streamLabel?: string;
  contentClassName?: string;
  collapsedHeight?: number;
  expandedHeight?: number;
  hasContent?: boolean;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [children, isStreaming]);

  // 没有内容时完全隐藏
  if (!hasContent) return null;

  const currentHeight = isExpanded ? expandedHeight : collapsedHeight;

  return (
    <div
      className={cn(
        "rounded-xl border shadow-sm overflow-hidden transition-all duration-300",
        borderColorClass,
        isActive && "ring-2 ring-blue-500/20",
      )}
    >
      {/* 头部 - 始终可见，可点击展开/收起 */}
      <button
        onClick={onToggle}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 transition-colors",
          headerBgClass,
          "hover:opacity-90",
        )}
      >
        <div
          className={cn(
            "flex items-center justify-center w-5 h-5 rounded-lg",
            iconColorClass,
          )}
        >
          {isStreaming ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Icon className="h-3 w-3" />
          )}
        </div>
        <span className="text-xs font-semibold uppercase tracking-wider flex-1 text-left">
          {title}
        </span>
        {isStreaming && streamLabel && (
          <span className="flex items-center gap-1 text-[10px] opacity-70">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current"></span>
            </span>
            {streamLabel}
          </span>
        )}
        <span className="text-[10px] text-zinc-400 mr-1">
          {isExpanded ? "收起" : "展开"}
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 transition-transform duration-200",
            !isExpanded && "-rotate-90",
          )}
        />
      </button>

      {/* 内容区域 - 固定高度，内部滚动 */}
      <div
        className="transition-all duration-300 overflow-hidden"
        style={{ height: `${currentHeight}px` }}
      >
        <div
          ref={scrollRef}
          className={cn(
            "h-full overflow-y-auto scrollbar-thin p-3",
            contentClassName,
          )}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

export function CollapsibleMessage({
  message,
  isStreaming = false,
  streamingContent,
  streamingReasoning,
  className,
  defaultExpanded = false,
  toolResults = [],
  attachedAssistant,
}: CollapsibleMessageProps) {
  const isToolCall =
    message.role === "assistant" &&
    message.tool_calls &&
    message.tool_calls.length > 0;
  const isToolResult = message.role === "tool";

  // 工具结果不单独渲染，已合并到 Tools 区域内
  if (isToolResult) {
    return null;
  }

  const displayContent = streamingContent ?? message.content ?? "";
  const reasoningContent =
    streamingReasoning || message.reasoning_content || "";
  const hasToolCalls = !!(
    isToolCall &&
    message.tool_calls &&
    message.tool_calls.length > 0
  );

  // 调试日志
  console.log("[CollapsibleMessage] Render:", {
    role: message.role,
    hasToolCalls,
    toolCallCount: message.tool_calls?.length,
    toolResultsCount: toolResults.length,
    isToolCall,
  });

  const config = messageTypeConfig[message.role] || messageTypeConfig.assistant;
  const Icon = config.icon;
  const isUser = message.role === "user";

  const [expandState, setExpandState] = useState({
    sections: {
      reasoning: false,
      content: false,
      tools: false,
    },
    toolPanels: {} as Record<string, boolean>,
    // 用户手动展开标记，一旦用户点击过，不再自动响应流式状态
    userManuallyExpanded: {
      reasoning: false,
      content: false,
      tools: false,
    },
  });
  const previousStreamSignalsRef = useRef({
    contentLen: 0,
    reasoningLen: 0,
    toolResultsLen: 0,
    toolResultsCount: 0,
  });

  const toolResultsTextLen = useMemo(
    () =>
      toolResults.reduce(
        (sum, item) =>
          sum + (typeof item.content === "string" ? item.content.length : 0),
        0,
      ),
    [toolResults],
  );

  useEffect(() => {
    const previous = previousStreamSignalsRef.current;
    const next = {
      contentLen: displayContent.length,
      reasoningLen: reasoningContent.length,
      toolResultsLen: toolResultsTextLen,
      toolResultsCount: toolResults.length,
    };

    const contentDelta = next.contentLen - previous.contentLen;
    const reasoningDelta = next.reasoningLen - previous.reasoningLen;
    const toolDelta =
      next.toolResultsLen - previous.toolResultsLen > 0 ||
      next.toolResultsCount - previous.toolResultsCount > 0
        ? 1
        : 0;

    const reasoningActive =
      reasoningDelta > 0 &&
      hasVisibleText(next.reasoningLen ? reasoningContent : "");
    const contentActive =
      contentDelta > 0 && hasVisibleText(next.contentLen ? displayContent : "");
    const toolsActive = toolDelta > 0 && hasToolCalls;

    // 统一响应式展开标志：单通道增量自动聚焦；并行增量同时展开。
    // 工具区域默认保持收起，不自动展开（除非用户已手动展开过）
    if (reasoningActive || contentActive) {
      setExpandState((prev) => ({
        ...prev,
        sections: {
          reasoning: reasoningActive && !prev.userManuallyExpanded.reasoning ? reasoningActive : prev.sections.reasoning,
          content: contentActive && !prev.userManuallyExpanded.content ? contentActive : prev.sections.content,
          // 工具区域始终不自动展开，保持默认收起
          tools: prev.sections.tools,
        },
      }));
    }

    previousStreamSignalsRef.current = next;
  }, [
    displayContent.length,
    displayContent,
    hasToolCalls,
    reasoningContent.length,
    reasoningContent,
    toolResults.length,
    toolResultsTextLen,
  ]);

  // 确定当前活跃的 token 类型（用于响应式布局）
  const activeSection = useMemo(() => {
    return {
      reasoning:
        hasVisibleText(reasoningContent) &&
        expandState.sections.reasoning,
      content:
        hasVisibleText(displayContent) && expandState.sections.content,
      tools: hasToolCalls && expandState.sections.tools,
    };
  }, [
    displayContent,
    expandState.sections,
    hasToolCalls,
    reasoningContent,
  ]);


  // 仅处理“无内容时关闭”，避免覆盖上面的 token 驱动展开。
  useEffect(() => {
    setExpandState((prev) => ({
      ...prev,
      sections: {
        reasoning: hasVisibleText(reasoningContent)
          ? prev.sections.reasoning
          : false,
        content: hasVisibleText(displayContent) ? prev.sections.content : false,
        tools: hasToolCalls ? prev.sections.tools : false,
      },
    }));
  }, [displayContent, hasToolCalls, reasoningContent]);

  const toggleSection = (section: keyof typeof expandState.sections) => {
    setExpandState((prev) => {
      const newExpanded = !prev.sections[section];
      return {
        ...prev,
        sections: {
          ...prev.sections,
          [section]: newExpanded,
        },
        // 标记用户已手动操作过此区域
        userManuallyExpanded: {
          ...prev.userManuallyExpanded,
          [section]: true,
        },
      };
    });
  };

  // 构建工具调用和结果的映射
  const toolCallResults = useMemo(() => {
    // 只要 message.tool_calls 存在就计算，不管 hasToolCalls 如何
    if (!message.tool_calls?.length) return [];

    const unmatchedResults = toolResults.filter((r) => r.role === "tool");
    const usedResultIndexes = new Set<number>();

    return message.tool_calls.map((toolCall) => {
      // 优先按 tool_call_id 精确关联；若缺失则回退到顺序关联，避免结果“丢失”。
      let result = unmatchedResults.find((r, idx) => {
        if (usedResultIndexes.has(idx)) return false;
        return r.tool_call_id === toolCall.id;
      });

      if (!result) {
        const fallbackIdx = unmatchedResults.findIndex(
          (r, idx) => !usedResultIndexes.has(idx),
        );
        if (fallbackIdx >= 0) {
          usedResultIndexes.add(fallbackIdx);
          result = unmatchedResults[fallbackIdx];
        }
      } else {
        const matchIdx = unmatchedResults.findIndex((r) => r === result);
        if (matchIdx >= 0) {
          usedResultIndexes.add(matchIdx);
        }
      }

      const argsText = formatToolArguments(toolCall.function.arguments || "");
      const resultContent = result?.content;
      const resultText =
        typeof resultContent === "string"
          ? resultContent
          : resultContent != null
            ? JSON.stringify(resultContent, null, 2)
            : "";
      return {
        toolCall,
        result,
        argsText,
        resultText,
        hasArgs: hasVisibleText(argsText),
        hasResult: hasVisibleText(resultText),
      };
    });
  }, [message.tool_calls, toolResults]);

  // 初始化工具面板状态：新工具默认全部折叠
  useEffect(() => {
    if (!toolCallResults.length) {
      setExpandState((prev) => ({
        ...prev,
        toolPanels: {},
      }));
      return;
    }

    setExpandState((prev) => {
      const nextPanels = { ...prev.toolPanels };
      let changed = false;

      for (const item of toolCallResults) {
        const rootKey = `${item.toolCall.id}:root`;
        const argsKey = `${item.toolCall.id}:args`;
        const resultKey = `${item.toolCall.id}:result`;

        // 新工具默认全部折叠，不自动展开
        if (!(rootKey in nextPanels)) {
          nextPanels[rootKey] = false;
          changed = true;
        }
        if (!(argsKey in nextPanels)) {
          nextPanels[argsKey] = false;
          changed = true;
        }
        if (!(resultKey in nextPanels)) {
          nextPanels[resultKey] = false;
          changed = true;
        }

        if (!item.hasArgs && nextPanels[argsKey] !== false) {
          nextPanels[argsKey] = false;
          changed = true;
        }
        if (!item.hasResult && nextPanels[resultKey] !== false) {
          nextPanels[resultKey] = false;
          changed = true;
        }
      }

      if (!changed) {
        return prev;
      }

      return {
        ...prev,
        toolPanels: nextPanels,
      };
    });
  }, [toolCallResults]);


  const toggleToolPanel = (key: string) => {
    setExpandState((prev) => ({
      ...prev,
      toolPanels: {
        ...prev.toolPanels,
        [key]: !prev.toolPanels[key],
      },
    }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className={cn(
        "rounded-2xl border shadow-sm overflow-hidden backdrop-blur-sm w-full md:max-w-[82%]",
        isUser ? "md:ml-auto" : "md:mr-auto",
        config.bgColor,
        config.borderColor,
        className,
      )}
    >
      {/* 消息头部 - 始终显示 */}
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

      {/* 消息内容 - 响应式分栏布局 */}
      <div className="px-4 pb-4">
        {message.role === "assistant" ? (
          <div className="flex flex-col gap-2">
            {/* Reasoning 区域 - 有内容时才显示 */}
            <FixedHeightSection
              title="Thought Process"
              icon={Brain}
              iconColorClass="bg-violet-100 text-violet-600 dark:bg-violet-900/50 dark:text-violet-400"
              headerBgClass="bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-950/30 dark:to-purple-950/20 border-b border-violet-200 dark:border-violet-800/50"
              borderColorClass="border-violet-200 dark:border-violet-800/50"
              isExpanded={expandState.sections.reasoning}
              onToggle={() => toggleSection("reasoning")}
              isActive={activeSection.reasoning}
              isStreaming={isStreaming && activeSection.reasoning}
              streamLabel="reasoning"
              contentClassName="bg-gradient-to-r from-violet-50/50 to-purple-50/50 dark:from-violet-950/20 dark:to-purple-950/10"
              collapsedHeight={100}
              expandedHeight={350}
              hasContent={hasVisibleText(reasoningContent)}
            >
              <p className="text-sm text-violet-800 dark:text-violet-200 whitespace-pre-wrap leading-relaxed">
                {reasoningContent}
              </p>
            </FixedHeightSection>

            {/* Content 区域 - 有内容时才显示 */}
            <FixedHeightSection
              title="Response"
              icon={MessageSquare}
              iconColorClass="bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400"
              headerBgClass="bg-blue-50 dark:bg-blue-950/20 border-b border-blue-200 dark:border-blue-800/50"
              borderColorClass="border-blue-200 dark:border-blue-800/50"
              isExpanded={expandState.sections.content}
              onToggle={() => toggleSection("content")}
              isActive={activeSection.content}
              isStreaming={isStreaming && activeSection.content}
              streamLabel="generating"
              contentClassName="bg-white dark:bg-zinc-900/50"
              collapsedHeight={150}
              expandedHeight={400}
              hasContent={hasVisibleText(displayContent)}
            >
              <MarkdownContent
                content={displayContent}
                isStreaming={isStreaming}
              />
            </FixedHeightSection>

            {/* Tools 区域 - 只要有工具调用就显示 */}
            {message.tool_calls && message.tool_calls.length > 0 && (
              <FixedHeightSection
                title={`Tools (${message.tool_calls.length})`}
                icon={Wrench}
                iconColorClass="bg-slate-100 text-slate-600 dark:bg-slate-900/50 dark:text-slate-400"
                headerBgClass="bg-slate-50 dark:bg-slate-900/30 border-b border-slate-200 dark:border-slate-700"
                borderColorClass="border-slate-200/60 dark:border-slate-700/60"
                isExpanded={!!expandState.sections.tools}
                onToggle={() => toggleSection("tools")}
                isActive={false}
                contentClassName="p-2 bg-slate-50/50 dark:bg-slate-900/20 space-y-2"
                collapsedHeight={120}
                expandedHeight={350}
                hasContent={true}
              >
                {toolCallResults.map((item) => {
                  const {
                    toolCall,
                    result,
                    argsText,
                    resultText,
                    hasArgs,
                    hasResult,
                  } = item;
                  const rootKey = `${toolCall.id}:root`;
                  const argsKey = `${toolCall.id}:args`;
                  const resultKey = `${toolCall.id}:result`;

                  return (
                    <div
                      key={toolCall.id}
                      className="rounded-lg border border-slate-200/60 dark:border-slate-700/60 overflow-hidden bg-white dark:bg-zinc-950"
                    >
                      {/* 工具名称和状态（可折叠） */}
                      <button
                        onClick={() => toggleToolPanel(rootKey)}
                        className="w-full px-2 py-1.5 flex items-center gap-2 bg-slate-50 dark:bg-slate-900/50 hover:bg-slate-100 dark:hover:bg-slate-900 text-left"
                      >
                        <ChevronDown
                          className={cn(
                            "h-3.5 w-3.5 text-slate-500 transition-transform",
                            !expandState.toolPanels[rootKey] && "-rotate-90",
                          )}
                        />
                        <span className="font-medium text-xs text-slate-700 dark:text-slate-300">
                          {toolCall.function.name}
                        </span>
                        {result ? (
                          <span className="ml-auto flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
                            <CheckCircle2 className="h-3 w-3" />
                            完成
                          </span>
                        ) : (
                          <span className="ml-auto flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            执行中
                          </span>
                        )}
                      </button>

                      {expandState.toolPanels[rootKey] && (
                        <div className="border-t border-slate-100/60 dark:border-slate-800/60 p-2 space-y-2">
                          {/* 参数部分 */}
                          {hasArgs && (
                            <div className="rounded border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
                              <button
                                onClick={() => toggleToolPanel(argsKey)}
                                className="w-full px-2 py-1 flex items-center gap-1.5 bg-slate-100/50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800"
                              >
                                <ChevronDown
                                  className={cn(
                                    "h-3 w-3 text-slate-500 transition-transform",
                                    !expandState.toolPanels[argsKey] && "-rotate-90",
                                  )}
                                />
                                <span className="text-[10px] font-medium text-slate-600">参数</span>
                              </button>
                              <div
                                className="overflow-y-auto scrollbar-thin bg-white dark:bg-zinc-950 transition-all"
                                style={{ height: expandState.toolPanels[argsKey] ? "80px" : "40px" }}
                              >
                                <pre className="text-[10px] text-slate-500 dark:text-slate-400 whitespace-pre-wrap break-all leading-relaxed p-2">
                                  {argsText}
                                </pre>
                              </div>
                            </div>
                          )}

                          {/* 结果部分 */}
                          {hasResult && (
                            <div className="rounded border border-slate-200/60 dark:border-slate-700/60 overflow-hidden">
                              <button
                                onClick={() => toggleToolPanel(resultKey)}
                                className="w-full px-2 py-1 flex items-center gap-1.5 bg-slate-100/50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800"
                              >
                                <ChevronDown
                                  className={cn(
                                    "h-3 w-3 text-slate-500 transition-transform",
                                    !expandState.toolPanels[resultKey] && "-rotate-90",
                                  )}
                                />
                                <span className="text-[10px] font-medium text-slate-600">结果</span>
                              </button>
                              <div
                                className="overflow-y-auto scrollbar-thin bg-white dark:bg-zinc-950 transition-all"
                                style={{ height: expandState.toolPanels[resultKey] ? "100px" : "50px" }}
                              >
                                <div className="p-2">
                                  <MarkdownContent content={resultText} isStreaming={false} />
                                </div>
                              </div>
                            </div>
                          )}

                          {/* 等待结果提示 */}
                          {!hasResult && (
                            <div className="px-2 py-1.5 text-[10px] text-amber-600 dark:text-amber-400 flex items-center gap-1.5 bg-amber-50/50 dark:bg-amber-950/20 rounded">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              等待工具执行结果...
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </FixedHeightSection>
            )}
          </div>
        ) : (
          /* 普通用户/系统消息 */
          <div className="text-sm whitespace-pre-wrap">{displayContent}</div>
        )}
      </div>
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
          "text-white",
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

        {/* 工具调用数量标识 */}
        {isToolCall && message.tool_calls && message.tool_calls.length > 0 && (
          <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 shrink-0 font-medium">
            <Wrench className="h-3 w-3" />
            {message.tool_calls.length} 个工具
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
  const [typedContent, setTypedContent] = useState(content);

  useEffect(() => {
    if (!content) {
      setTypedContent("");
      return;
    }

    // 若是增量更新，延续已有打字进度；若不是同一前缀则重置重打。
    setTypedContent((prev) => (content.startsWith(prev) ? prev : ""));
  }, [content]);

  useEffect(() => {
    if (typedContent.length >= content.length) {
      return;
    }

    const timer = setInterval(() => {
      setTypedContent((prev) => {
        if (prev.length >= content.length) {
          return prev;
        }

        const remaining = content.length - prev.length;
        const step = Math.max(1, Math.min(4, Math.ceil(remaining / 10)));
        return content.slice(0, prev.length + step);
      });
    }, 28);

    return () => clearInterval(timer);
  }, [content, typedContent.length]);

  const renderedContent = typedContent;

  if (!renderedContent || renderedContent.trim() === "") {
    return null;
  }

  return (
    <div className="markdown-body text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
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
          p: ({ children }) => (
            <p className="text-zinc-700 dark:text-zinc-300 mb-3 last:mb-0">
              {children}
            </p>
          ),
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
          strong: ({ children }) => (
            <strong className="font-bold text-zinc-900 dark:text-zinc-100">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="italic text-zinc-600 dark:text-zinc-400">
              {children}
            </em>
          ),
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
          pre: ({ children }) => <>{children}</>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-blue-400 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-600 pl-4 py-2 pr-3 my-3 rounded-r-lg italic text-zinc-600 dark:text-zinc-400">
              {children}
            </blockquote>
          ),
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
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-zinc-200 dark:border-zinc-700">
              <table className="w-full text-sm border-collapse">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-zinc-100 dark:bg-zinc-800">{children}</thead>
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
          hr: () => (
            <hr className="my-4 border-zinc-200 dark:border-zinc-700" />
          ),
        }}
      >
        {renderedContent}
      </ReactMarkdown>

      {isStreaming && (
        <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse rounded-sm" />
      )}
    </div>
  );
}
