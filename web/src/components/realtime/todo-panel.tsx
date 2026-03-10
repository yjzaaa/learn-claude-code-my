"use client";

import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useMessageStore } from "@/hooks/useMessageStore";
import { CheckCircle2, Circle, Loader2, AlertCircle } from "lucide-react";

interface TodoPanelProps {
  className?: string;
  isOpen: boolean;
  onClose: () => void;
}

export function TodoPanel({ className, isOpen, onClose }: TodoPanelProps) {
  const { streamState } = useMessageStore();
  const { todos, roundsSinceTodo, showTodoReminder } = streamState;

  const hasTodos = todos && todos.length > 0;

  const pendingTodos = hasTodos ? todos.filter((t) => t.status === "pending") : [];
  const inProgressTodos = hasTodos ? todos.filter((t) => t.status === "in_progress") : [];
  const completedTodos = hasTodos ? todos.filter((t) => t.status === "completed") : [];

  if (!isOpen) return null;

  return (
    <div className={cn("h-full flex flex-col", className)}>
      {/* Reminder */}
      <AnimatePresence>
        {showTodoReminder && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="px-3 py-1 bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-1"
          >
            <AlertCircle className="h-3 w-3" />
            Update task status
          </motion.div>
        )}
      </AnimatePresence>

      {/* Todo List - Horizontal layout for top panel */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        {!hasTodos ? (
          <div className="h-full flex items-center justify-center text-zinc-400 text-xs">
            No tasks
          </div>
        ) : (
          <div className="flex gap-4 p-2 h-full">
            {inProgressTodos.length > 0 && (
              <div className="flex flex-col min-w-[140px]">
                <span className="text-[10px] font-medium text-amber-600 mb-1">In Progress</span>
                <div className="flex-1 overflow-y-auto space-y-1">
                  {inProgressTodos.map((todo) => (
                    <TodoCard key={todo.id} todo={todo} />
                  ))}
                </div>
              </div>
            )}

            {pendingTodos.length > 0 && (
              <div className="flex flex-col min-w-[140px]">
                <span className="text-[10px] font-medium text-zinc-500 mb-1">Pending</span>
                <div className="flex-1 overflow-y-auto space-y-1">
                  {pendingTodos.map((todo) => (
                    <TodoCard key={todo.id} todo={todo} />
                  ))}
                </div>
              </div>
            )}

            {completedTodos.length > 0 && (
              <div className="flex flex-col min-w-[140px]">
                <span className="text-[10px] font-medium text-emerald-600 mb-1">Done</span>
                <div className="flex-1 overflow-y-auto space-y-1">
                  {completedTodos.map((todo) => (
                    <TodoCard key={todo.id} todo={todo} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Timer */}
      <div className="px-3 py-1 border-t border-zinc-200/60 dark:border-zinc-700/60 bg-zinc-100/30 dark:bg-zinc-800/30">
        <div className="flex items-center justify-between text-[10px] text-zinc-400 mb-0.5">
          <span>Reminder</span>
          <span>{roundsSinceTodo}/3</span>
        </div>
        <div className="h-1 w-full bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
          <motion.div
            className={cn(
              "h-full",
              roundsSinceTodo === 0 && "bg-zinc-400",
              roundsSinceTodo === 1 && "bg-green-400",
              roundsSinceTodo === 2 && "bg-yellow-400",
              roundsSinceTodo >= 3 && "bg-red-500"
            )}
            animate={{
              width:
                roundsSinceTodo === 0
                  ? "0%"
                  : roundsSinceTodo === 1
                  ? "33%"
                  : roundsSinceTodo === 2
                  ? "66%"
                  : "100%",
            }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>
    </div>
  );
}

function TodoCard({ todo }: { todo: { id: string; text: string; status: string } }) {
  const statusConfig = {
    pending: {
      icon: Circle,
      bg: "bg-zinc-50 dark:bg-zinc-900",
      border: "border-zinc-200 dark:border-zinc-800",
      text: "text-zinc-600 dark:text-zinc-400",
      iconColor: "text-zinc-400",
    },
    in_progress: {
      icon: Loader2,
      bg: "bg-amber-50 dark:bg-amber-950/20",
      border: "border-amber-200 dark:border-amber-800",
      text: "text-amber-700 dark:text-amber-300",
      iconColor: "text-amber-500 animate-spin",
    },
    completed: {
      icon: CheckCircle2,
      bg: "bg-emerald-50 dark:bg-emerald-950/20",
      border: "border-emerald-200 dark:border-emerald-800",
      text: "text-emerald-700 dark:text-emerald-300",
      iconColor: "text-emerald-500",
    },
  };

  const config = statusConfig[todo.status as keyof typeof statusConfig];
  const Icon = config.icon;

  return (
    <motion.div
      layout
      layoutId={`todo-${todo.id}`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        "flex items-start gap-1.5 rounded px-1.5 py-1 border",
        config.bg,
        config.border
      )}
    >
      <Icon className={cn("h-3 w-3 mt-0.5 shrink-0", config.iconColor)} />
      <span className={cn("text-[11px] leading-tight", config.text)}>{todo.text}</span>
    </motion.div>
  );
}
