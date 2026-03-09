"use client";

import { useState, useMemo, useEffect } from "react";
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
}

/** 可展开区域组件 */
function CollapsibleSection({
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
}) {
  return (
    <div
      className={cn(
        "rounded-xl border shadow-sm overflow-hidden transition-all duration-300",
        borderColorClass,
        isActive && "ring-2 ring-blue-500/20",
        isExpanded ? "flex-1 min-h-[120px]" : "flex-shrink-0 h-10"
      )}
    >
      {/* 头部 - 始终可见，可点击 */}
      <button
        onClick={onToggle}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 transition-colors",
          headerBgClass,
          "hover:opacity-90"
        )}
      >
        <div className={cn("flex items-center justify-center w-5 h-5 rounded-lg", iconColorClass)}>
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
        <ChevronDown
          className={cn(
            "h-4 w-4 transition-transform duration-200",
            !isExpanded && "-rotate-90"
          )}
        />
      </button>

      {/* 内容区域 */}
      <div
        className={cn(
          "overflow-hidden transition-all duration-300",
          isExpanded ? "flex-1 opacity-100" : "h-0 opacity-0"
        )}
      >
        <div className={cn("h-full overflow-y-auto scrollbar-thin", contentClassName)}>
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
  const reasoningContent = streamingReasoning || message.reasoning_content || "";
  const hasToolCalls = !!(isToolCall && message.tool_calls && message.tool_calls.length > 0);

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

  // 确定当前活跃的 token 类型（用于响应式布局）
  const activeSection = useMemo(() => {
    if (!isStreaming) {
      // 非流式状态下，有内容的展开，没内容的收起
      return {
        reasoning: !!reasoningContent,
        content: !!displayContent,
        tools: hasToolCalls,
      };
    }
    // 流式状态下，根据活跃内容动态判断
    // 如果有推理内容但没有正文，推理区域活跃
    // 如果有正文，正文区域活跃
    return {
      reasoning: !!reasoningContent && !displayContent,
      content: !!displayContent,
      tools: false, // 流式时工具区域默认不展开
    };
  }, [isStreaming, reasoningContent, displayContent, hasToolCalls]);

  // 展开状态管理 - 默认所有区域都展开
  const [expandedSections, setExpandedSections] = useState({
    reasoning: true,
    content: true,
    tools: true,
  });

  // 初始化时根据活跃区域设置展开状态（仅执行一次）
  useEffect(() => {
    const hasTools = !!(message.tool_calls && message.tool_calls.length > 0);
    setExpandedSections({
      reasoning: activeSection.reasoning,
      content: activeSection.content,
      tools: hasTools, // 有工具调用时默认展开
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 只在挂载时执行一次

  // 当工具调用出现时，自动展开工具区域
  useEffect(() => {
    if (hasToolCalls) {
      setExpandedSections((prev) => ({
        ...prev,
        tools: true,
      }));
    }
  }, [hasToolCalls]);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // 构建工具调用和结果的映射
  const toolCallResults = useMemo(() => {
    // 只要 message.tool_calls 存在就计算，不管 hasToolCalls 如何
    if (!message.tool_calls?.length) return [];
    return message.tool_calls.map((toolCall) => {
      const result = toolResults.find((r) => r.tool_call_id === toolCall.id);
      return { toolCall, result };
    });
  }, [message.tool_calls, toolResults]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className={cn(
        "rounded-2xl border shadow-sm overflow-hidden backdrop-blur-sm",
        config.bgColor,
        config.borderColor,
        className
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
            {/* Reasoning 区域 */}
            <CollapsibleSection
              title="Thought Process"
              icon={Brain}
              iconColorClass="bg-violet-100 text-violet-600 dark:bg-violet-900/50 dark:text-violet-400"
              headerBgClass="bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-950/30 dark:to-purple-950/20 border-b border-violet-200 dark:border-violet-800/50"
              borderColorClass="border-violet-200 dark:border-violet-800/50"
              isExpanded={expandedSections.reasoning}
              onToggle={() => toggleSection("reasoning")}
              isActive={activeSection.reasoning}
              isStreaming={isStreaming && activeSection.reasoning}
              streamLabel="reasoning"
              contentClassName="p-3 bg-gradient-to-r from-violet-50/50 to-purple-50/50 dark:from-violet-950/20 dark:to-purple-950/10"
            >
              {reasoningContent ? (
                <p className="text-sm text-violet-800 dark:text-violet-200 whitespace-pre-wrap leading-relaxed">
                  {reasoningContent}
                </p>
              ) : (
                <p className="text-xs text-violet-400 italic">等待推理内容...</p>
              )}
            </CollapsibleSection>

            {/* Content 区域 */}
            <CollapsibleSection
              title="Response"
              icon={MessageSquare}
              iconColorClass="bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400"
              headerBgClass="bg-blue-50 dark:bg-blue-950/20 border-b border-blue-200 dark:border-blue-800/50"
              borderColorClass="border-blue-200 dark:border-blue-800/50"
              isExpanded={expandedSections.content}
              onToggle={() => toggleSection("content")}
              isActive={activeSection.content}
              isStreaming={isStreaming && activeSection.content}
              streamLabel="generating"
              contentClassName="p-3 bg-white dark:bg-zinc-900/50"
            >
              {displayContent ? (
                <MarkdownContent content={displayContent} isStreaming={isStreaming} />
              ) : (
                <p className="text-xs text-zinc-400 italic">等待生成内容...</p>
              )}
            </CollapsibleSection>

            {/* Tools 区域 - 只要有工具调用就显示 */}
            {message.tool_calls && message.tool_calls.length > 0 && (
              <CollapsibleSection
                title={`Tools (${message.tool_calls.length})`}
                icon={Wrench}
                iconColorClass="bg-slate-100 text-slate-600 dark:bg-slate-900/50 dark:text-slate-400"
                headerBgClass="bg-slate-50 dark:bg-slate-900/30 border-b border-slate-200 dark:border-slate-700"
                borderColorClass="border-slate-200 dark:border-slate-700"
                isExpanded={!!expandedSections.tools}
                onToggle={() => toggleSection("tools")}
                isActive={false}
                contentClassName="p-2 bg-slate-50/50 dark:bg-slate-900/20 space-y-2"
              >
                {toolCallResults.map(({ toolCall, result }) => (
                  <div
                    key={toolCall.id}
                    className="rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden bg-white dark:bg-zinc-950"
                  >
                    {/* 工具名称和状态 */}
                    <div className="px-2 py-1.5 flex items-center gap-2 bg-slate-50 dark:bg-slate-900/50">
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
                    </div>
                    {/* 工具参数 */}
                    <div className="px-2 py-1 border-t border-slate-100 dark:border-slate-800">
                      <pre className="text-[10px] text-slate-500 dark:text-slate-500 whitespace-pre-wrap break-all leading-relaxed max-h-16 overflow-y-auto scrollbar-thin">
                        {toolCall.function.arguments}
                      </pre>
                    </div>
                    {/* 工具执行结果 - 使用 Markdown 渲染 */}
                    {result && (
                      <div className="px-2 py-1.5 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 max-h-48 overflow-y-auto scrollbar-thin">
                        <MarkdownContent content={String(result.content || "")} isStreaming={false} />
                      </div>
                    )}
                  </div>
                ))}
              </CollapsibleSection>
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
  if (!content || content.trim() === "") {
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
            <em className="italic text-zinc-600 dark:text-zinc-400">{children}</em>
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
          hr: () => <hr className="my-4 border-zinc-200 dark:border-zinc-700" />,
        }}
      >
        {content}
      </ReactMarkdown>

      {isStreaming && (
        <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse rounded-sm" />
      )}
    </div>
  );
}
