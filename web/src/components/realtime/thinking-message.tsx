"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import type { RealtimeMessage } from "@/types/realtime-message";
import { Brain, ChevronDown } from "lucide-react";

interface ThinkingMessageProps {
  message: RealtimeMessage;
  className?: string;
}

export function ThinkingMessage({ message, className }: ThinkingMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className={cn(
        "rounded-lg border border-amber-200 bg-amber-50/50",
        "dark:border-amber-900/30 dark:bg-amber-950/20",
        className
      )}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex w-full items-center justify-between px-3 py-2",
          "text-left transition-colors",
          "hover:bg-amber-100/50 dark:hover:bg-amber-900/20"
        )}
      >
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-amber-600" />
          <span className="text-xs font-medium text-amber-700 dark:text-amber-400">
            思考过程
          </span>
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-amber-600 transition-transform duration-200",
            isExpanded && "rotate-180"
          )}
        />
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-amber-200/50 dark:border-amber-900/20"
          >
            <div className="px-3 py-2">
              <pre className="whitespace-pre-wrap text-xs leading-relaxed text-amber-800 dark:text-amber-300">
                {message.content}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
