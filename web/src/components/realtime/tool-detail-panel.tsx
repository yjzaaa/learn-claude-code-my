"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { MarkdownContent, type ToolDetailPayload } from "./collapsible-message";
import { CheckCircle2, Loader2, AlertCircle, ChevronDown } from "lucide-react";

interface ToolDetailPanelProps {
  className?: string;
  isOpen: boolean;
  detail: ToolDetailPayload | null;
  onClose: () => void;
}

export function ToolDetailPanel({
  className,
  isOpen,
  detail,
  onClose,
}: ToolDetailPanelProps) {
  const [isArgsExpanded, setIsArgsExpanded] = useState(true);
  const [isResultExpanded, setIsResultExpanded] = useState(true);

  useEffect(() => {
    setIsArgsExpanded(true);
    setIsResultExpanded(true);
  }, [detail?.id]);

  if (!isOpen) return null;

  const hasDetail = !!detail;

  return (
    <div className={cn("h-full flex flex-col", className)}>
      {/* Reminder */}
      {!hasDetail && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="px-3 py-1 bg-zinc-100/70 dark:bg-zinc-800/50 text-zinc-500 dark:text-zinc-400 text-xs flex items-center gap-1"
        >
          <AlertCircle className="h-3 w-3" />
          请选择一个工具
        </motion.div>
      )}

      <div className="flex-1 overflow-hidden">
        {!hasDetail ? (
          <div className="h-full flex items-center justify-center text-zinc-400 text-xs">
            选择一个工具查看详情
          </div>
        ) : (
          <div className="h-full p-2">
            <div className="h-full flex flex-col gap-2 min-h-0">
              {detail.hasArgs && (
                <div
                  className={cn(
                    "min-h-0 rounded border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-2 flex flex-col",
                    isArgsExpanded ? "basis-2/5" : "flex-none",
                  )}
                >
                  <button
                    onClick={() => setIsArgsExpanded((prev) => !prev)}
                    className="flex items-center justify-between text-left"
                  >
                    <span className="text-[10px] font-medium text-zinc-500">
                      Arguments
                    </span>
                    <ChevronDown
                      className={cn(
                        "h-3.5 w-3.5 text-zinc-400 transition-transform",
                        !isArgsExpanded && "-rotate-90",
                      )}
                    />
                  </button>
                  {isArgsExpanded && (
                    <div className="mt-1 flex-1 min-h-0 overflow-y-auto">
                      <MarkdownContent
                        content={`\`\`\`json\n${detail.argsText}\n\`\`\``}
                        isStreaming={false}
                      />
                    </div>
                  )}
                </div>
              )}

              <div
                className={cn(
                  "min-h-0 rounded border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-2 flex flex-col",
                  isResultExpanded
                    ? detail.hasArgs
                      ? "basis-3/5"
                      : "flex-1"
                    : "flex-none",
                )}
              >
                <button
                  onClick={() => setIsResultExpanded((prev) => !prev)}
                  className="flex items-center justify-between text-left"
                >
                  <span className="text-[10px] font-medium text-sky-600 dark:text-sky-300">
                    Result
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
                        detail.status === "completed"
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
                      )}
                    >
                      {detail.status === "completed" ? (
                        <CheckCircle2 className="h-3 w-3" />
                      ) : (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      )}
                      {detail.status === "completed" ? "完成" : "执行中"}
                    </span>
                    <ChevronDown
                      className={cn(
                        "h-3.5 w-3.5 text-zinc-400 transition-transform",
                        !isResultExpanded && "-rotate-90",
                      )}
                    />
                  </div>
                </button>
                {isResultExpanded && (
                  <div className="mt-1 flex-1 min-h-0 overflow-y-auto">
                    {detail.hasResult ? (
                      <MarkdownContent
                        content={detail.resultText}
                        isStreaming={detail.status === "running"}
                      />
                    ) : (
                      <div className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        等待工具执行结果...
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="px-3 py-1 border-t border-zinc-200/60 dark:border-zinc-700/60 bg-zinc-100/30 dark:bg-zinc-800/30">
        <div className="flex items-center justify-between text-[10px] text-zinc-400">
          <span>{detail ? `Tool: ${detail.name}` : "Tool Detail"}</span>
          <button
            onClick={onClose}
            className="rounded px-1.5 py-0.5 hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
