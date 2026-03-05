"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { RealtimeMessage } from "@/types/realtime-message";
import { StatusIndicator } from "./status-indicator";
import { MessageTypeBadge } from "./message-type-badge";
import { ToolNameLabel } from "./tool-name-label";
import { ThinkingMessage } from "./thinking-message";
import { ChevronDown, ChevronRight } from "lucide-react";

interface CollapsibleMessageProps {
  message: RealtimeMessage;
  childMessages?: RealtimeMessage[];
  allMessages?: RealtimeMessage[];
  isStreaming?: boolean;
  className?: string;
  defaultExpanded?: boolean;
}

export function CollapsibleMessage({
  message,
  childMessages = [],
  allMessages = [],
  isStreaming = false,
  className,
  defaultExpanded = false,
}: CollapsibleMessageProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // 分离不同类型的子消息（包括嵌套的 tool_result）
  const { thinkingMessages, toolCalls, streamTokens } = useMemo(() => {
    const thinking: RealtimeMessage[] = [];
    const tools: RealtimeMessage[] = [];
    const tokens: string[] = [];

    childMessages.forEach((child) => {
      switch (child.type) {
        case "assistant_thinking":
          thinking.push(child);
          break;
        case "tool_call":
          tools.push(child);
          break;
        case "stream_token":
          tokens.push(child.content);
          break;
      }
    });

    return {
      thinkingMessages: thinking,
      toolCalls: tools,
      streamTokens: tokens,
    };
  }, [childMessages]);

  // 判断是否为工具调用或工具结果
  const isToolCall = message.type === "tool_call";
  const isToolResult = message.type === "tool_result";

  // 获取工具调用的结果（从所有消息中查找嵌套结果）
  const getToolResults = (toolId: string): RealtimeMessage[] => {
    return allMessages.filter((m) => m.parent_id === toolId && m.type === "tool_result");
  };

  // 获取当前工具调用的结果（用于预览）
  const currentToolResults = isToolCall ? getToolResults(message.id) : [];

  // 是否显示下拉箭头（有子消息或者是流式消息）
  const hasChildren = childMessages.length > 0;
  const showExpandButton = hasChildren || isStreaming;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "rounded-lg border bg-white shadow-sm",
        "dark:bg-zinc-900 dark:border-zinc-700",
        className
      )}
    >
      {/* Header - 始终可见 */}
      <div
        className={cn(
          "flex items-center justify-between px-3 py-2.5",
          "border-b border-zinc-100 dark:border-zinc-800",
          showExpandButton && "cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
          "transition-colors"
        )}
        onClick={() => showExpandButton && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2.5">
          {/* 状态点 */}
          <StatusIndicator
            status={message.status}
            size="sm"
            animate={isStreaming}
          />

          {/* 消息类型标签 */}
          <MessageTypeBadge type={message.type} size="sm" />

          {/* 工具名称（如果是工具调用） */}
          {message.tool_name && (
            <ToolNameLabel toolName={message.tool_name} size="sm" />
          )}

          {/* 流式指示器 */}
          {isStreaming && (
            <span className="text-xs text-blue-500 animate-pulse">
              流式传输中...
            </span>
          )}
        </div>

        {/* 右侧：展开按钮和时间戳 */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-400">
            {new Date(message.timestamp).toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>

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

      {/* Preview - 简要内容预览（折叠时显示） */}
      {!isExpanded && (
        <div className="px-3 py-2">
          {isToolCall ? (
            // 工具调用：显示工具名称和参数缩略
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-purple-700 dark:text-purple-400">
                {message.tool_name || "unknown"}
              </span>
              {message.tool_input && (
                <span className="text-zinc-500 dark:text-zinc-400 line-clamp-1 font-mono">
                  {JSON.stringify(message.tool_input).slice(0, 80)}
                  {JSON.stringify(message.tool_input).length > 80 ? "..." : ""}
                </span>
              )}
              {/* 如果有结果，显示完成标记 */}
              {currentToolResults.length > 0 && (
                <span className="text-emerald-600 dark:text-emerald-400 text-[10px]">
                  ✓ 已完成
                </span>
              )}
            </div>
          ) : isToolResult ? (
            // 工具结果：折叠时不单独显示（作为子消息显示在父工具调用中）
            <p className="text-sm text-zinc-700 dark:text-zinc-300 line-clamp-2 font-mono text-xs text-emerald-700 dark:text-emerald-400">
              {message.content?.slice(0, 100) || "(无内容)"}
              {message.content?.length > 100 ? "..." : ""}
            </p>
          ) : (
            // 其他消息类型
            <p className="text-sm text-zinc-700 dark:text-zinc-300 line-clamp-2">
              {message.content || "(无内容)"}
            </p>
          )}
        </div>
      )}

      {/* Expanded Content - 展开后的详细内容 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {/* 主内容 */}
            <div className="px-3 py-3 border-b border-zinc-100 dark:border-zinc-800">
              {isToolCall ? (
                // 工具调用展开：显示参数和结果
                <div className="space-y-3">
                  {/* 参数 */}
                  <div>
                    <p className="text-[10px] text-zinc-400 mb-1">参数</p>
                    <pre className="whitespace-pre-wrap rounded-md bg-purple-900/20 p-3 font-mono text-xs leading-relaxed text-purple-100 border border-purple-700/30">
                      {message.tool_input
                        ? JSON.stringify(message.tool_input, null, 2)
                        : "(无参数)"}
                    </pre>
                  </div>
                  {/* 结果（如果有） */}
                  {currentToolResults.length > 0 && (
                    <div>
                      <p className="text-[10px] text-zinc-400 mb-1">结果</p>
                      <pre className="whitespace-pre-wrap rounded-md bg-emerald-900/20 p-3 font-mono text-xs leading-relaxed text-emerald-100 border border-emerald-700/30">
                        {currentToolResults[0].content || "(无输出)"}
                      </pre>
                    </div>
                  )}
                  {isStreaming && currentToolResults.length === 0 && (
                    <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                  )}
                </div>
              ) : isToolResult ? (
                // 工具结果：在展开状态下详细显示
                <pre className="whitespace-pre-wrap rounded-md bg-emerald-900/20 p-3 font-mono text-xs leading-relaxed text-emerald-100 border border-emerald-700/30">
                  {message.content || "(无输出)"}
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                  )}
                </pre>
              ) : (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                    {message.content}
                    {isStreaming && (
                      <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                    )}
                  </p>
                </div>
              )}

              {/* 流式tokens显示 */}
              {streamTokens.length > 0 && (
                <div className="mt-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                  <p className="text-[10px] text-zinc-400 mb-1">流式Tokens</p>
                  <div className="flex flex-wrap gap-1">
                    {streamTokens.slice(-10).map((token, i) => (
                      <span
                        key={i}
                        className="inline-block px-1.5 py-0.5 bg-cyan-50 text-cyan-700 text-[10px] rounded"
                      >
                        {token}
                      </span>
                    ))}
                    {streamTokens.length > 10 && (
                      <span className="text-[10px] text-zinc-400">
                        +{streamTokens.length - 10} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* 思考过程 */}
            {thinkingMessages.length > 0 && (
              <div className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800">
                <p className="text-[10px] text-zinc-400 mb-2">思考过程</p>
                <div className="space-y-2">
                  {thinkingMessages.map((thinking) => (
                    <ThinkingMessage key={thinking.id} message={thinking} />
                  ))}
                </div>
              </div>
            )}

            {/* 子消息中的工具调用和结果 - 只在非工具消息中显示 */}
            {!isToolCall &&
              !isToolResult &&
              toolCalls.length > 0 && (
                <div className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800">
                  <p className="text-[10px] text-zinc-400 mb-2">工具调用</p>
                  <div className="space-y-2">
                    {toolCalls.map((tool) => {
                      const toolResults = getToolResults(tool.id);
                      return (
                        <div
                          key={tool.id}
                          className="rounded-md border border-purple-200 bg-purple-50/50 dark:border-purple-900/30 dark:bg-purple-950/20 p-2"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <ToolNameLabel
                              toolName={tool.tool_name || "unknown"}
                              size="sm"
                            />
                            <StatusIndicator status={tool.status} size="sm" />
                          </div>
                          {tool.tool_input && (
                            <pre className="text-[10px] text-purple-800 dark:text-purple-300 overflow-x-auto">
                              {JSON.stringify(tool.tool_input, null, 2)}
                            </pre>
                          )}
                          {/* 显示对应的结果 */}
                          {toolResults.map((result) => (
                            <div
                              key={result.id}
                              className="mt-2 pt-2 border-t border-emerald-200/50 dark:border-emerald-800/30"
                            >
                              <span className="text-[10px] text-emerald-600 dark:text-emerald-400">
                                结果:
                              </span>
                              <pre className="text-[10px] text-emerald-800 dark:text-emerald-300 whitespace-pre-wrap mt-1">
                                {result.content?.slice(0, 200)}
                                {result.content?.length > 200 ? "..." : ""}
                              </pre>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

            {/* 元数据 */}
            {message.metadata && Object.keys(message.metadata).length > 0 && (
              <div className="px-3 py-2">
                <p className="text-[10px] text-zinc-400 mb-1">元数据</p>
                <pre className="text-[10px] text-zinc-500 bg-zinc-50 dark:bg-zinc-800 p-2 rounded">
                  {JSON.stringify(message.metadata, null, 2)}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
