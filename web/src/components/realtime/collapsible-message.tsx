"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { ChatMessage, ChatRole } from "@/types/openai";
import { parseToolCallArguments } from "@/types/openai";
import { StatusIndicator } from "./status-indicator";
import { MessageTypeBadge } from "./message-type-badge";
import { ToolNameLabel } from "./tool-name-label";
import { ThinkingMessage } from "./thinking-message";
import { RoleLabel } from "./agent-type-label";
import { ChevronDown, ChevronRight } from "lucide-react";

interface CollapsibleMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
  /** 流式内容（增量更新） */
  streamingContent?: string;
  /** 流式推理内容 */
  streamingReasoning?: string;
  className?: string;
  defaultExpanded?: boolean;
}

export function CollapsibleMessage({
  message,
  isStreaming = false,
  streamingContent,
  streamingReasoning,
  className,
  defaultExpanded = false,
}: CollapsibleMessageProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // 判断是否为工具调用或工具结果
  const isToolCall = message.role === "assistant" && message.tool_calls && message.tool_calls.length > 0;
  const isToolResult = message.role === "tool";

  // 是否显示下拉箭头
  const displayContent = streamingContent ?? message.content ?? "";
  const hasContent = !!displayContent || isToolCall || !!streamingReasoning;
  const showExpandButton = hasContent || isStreaming;

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
          {/* 角色标签 */}
          <RoleLabel role={message.role} size="sm" agentName={message.agent_name} />

          {/* 工具名称（如果是工具调用） */}
          {isToolCall && message.tool_calls?.[0] && (
            <ToolNameLabel toolName={message.tool_calls[0].function.name} size="sm" />
          )}

          {/* 工具名称（如果是工具结果） */}
          {isToolResult && message.name && (
            <ToolNameLabel toolName={message.name} size="sm" />
          )}

          {/* 流式指示器 */}
          {isStreaming && (
            <span className="text-xs text-blue-500 animate-pulse">
              流式传输中...
            </span>
          )}
        </div>

        {/* 右侧：展开按钮 */}
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

      {/* Preview - 简要内容预览（折叠时显示） */}
      {!isExpanded && (
        <div className="px-3 py-2">
          {isToolCall ? (
            // 工具调用：显示工具名称、参数缩略，以及内容预览
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-medium text-purple-700 dark:text-purple-400">
                  {message.tool_calls?.[0]?.function.name || "unknown"}
                </span>
                {message.tool_calls?.[0]?.function.arguments && (
                  <span className="text-zinc-500 dark:text-zinc-400 line-clamp-1 font-mono">
                    {message.tool_calls[0].function.arguments.slice(0, 80)}
                    {message.tool_calls[0].function.arguments.length > 80 ? "..." : ""}
                  </span>
                )}
              </div>
              {/* 同时显示内容预览 */}
              {(displayContent || streamingReasoning) && (
                <div className="space-y-1 border-t border-zinc-100 dark:border-zinc-800 pt-2">
                  {streamingReasoning && (
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-1 italic">
                      思考中: {streamingReasoning.slice(0, 60)}
                      {streamingReasoning.length > 60 ? "..." : ""}
                    </p>
                  )}
                  {displayContent && (
                    <p className="text-sm text-zinc-700 dark:text-zinc-300 line-clamp-2">
                      {displayContent}
                    </p>
                  )}
                </div>
              )}
            </div>
          ) : isToolResult ? (
            // 工具结果
            <p className="text-sm text-zinc-700 dark:text-zinc-300 line-clamp-2 font-mono text-xs text-emerald-700 dark:text-emerald-400">
              {message.content?.slice(0, 100) || "(无内容)"}
              {message.content && message.content.length > 100 ? "..." : ""}
            </p>
          ) : (
            // 其他消息类型
            <div className="space-y-1">
              {streamingReasoning && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-1 italic">
                  思考中: {streamingReasoning.slice(0, 60)}
                  {streamingReasoning.length > 60 ? "..." : ""}
                </p>
              )}
              <p className="text-sm text-zinc-700 dark:text-zinc-300 line-clamp-2">
                {displayContent || "(无内容)"}
              </p>
            </div>
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
                // 工具调用展开：显示参数
                <div className="space-y-3">
                  {message.tool_calls?.map((toolCall) => (
                    <div key={toolCall.id}>
                      <p className="text-[10px] text-zinc-400 mb-1">工具: {toolCall.function.name}</p>
                      <pre className="whitespace-pre-wrap rounded-md bg-purple-50 dark:bg-purple-950/20 p-3 font-mono text-xs leading-relaxed text-purple-800 dark:text-purple-300 border border-purple-200 dark:border-purple-900/30">
                        {(() => {
                          try {
                            return JSON.stringify(parseToolCallArguments(toolCall), null, 2);
                          } catch {
                            return toolCall.function.arguments;
                          }
                        })()}
                      </pre>
                    </div>
                  ))}
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                  )}
                </div>
              ) : isToolResult ? (
                // 工具结果：在展开状态下详细显示
                <pre className="whitespace-pre-wrap rounded-md bg-emerald-50 dark:bg-emerald-950/20 p-3 font-mono text-xs leading-relaxed text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900/30">
                  {message.content || "(无输出)"}
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                  )}
                </pre>
              ) : (
                <div className="space-y-3">
                  {/* 推理内容 (仅流式时显示) */}
                  {streamingReasoning && (
                    <div className="rounded-md bg-amber-50 dark:bg-amber-950/20 p-3 border border-amber-200 dark:border-amber-900/30">
                      <p className="text-[10px] text-amber-600 dark:text-amber-400 mb-1 font-medium">思考过程</p>
                      <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-amber-800 dark:text-amber-300">
                        {streamingReasoning}
                      </pre>
                    </div>
                  )}
                  {/* 主内容 */}
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                      {displayContent}
                      {isStreaming && (
                        <span className="inline-block w-2 h-4 bg-blue-500 ml-0.5 animate-pulse" />
                      )}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
