"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMessageStore } from "@/hooks/useMessageStore";
import { useAgentApi } from "@/hooks/useAgentApi";
import type { RealtimeMessage, DialogSession } from "@/types/realtime-message";
import { CollapsibleMessage } from "./collapsible-message";
import { StatusIndicator } from "./status-indicator";
import {
  MessageSquare,
  Wifi,
  WifiOff,
  AlertCircle,
  Send,
  X,
  Maximize2,
  Minimize2,
  Power,
  Square,
} from "lucide-react";

interface RealtimeDialogProps {
  dialogId: string;
  title?: string;
  className?: string;
  position?:
    | "bottom-right"
    | "bottom-left"
    | "top-right"
    | "top-left"
    | "center";
  width?: "sm" | "md" | "lg" | "xl" | "full";
  height?: "sm" | "md" | "lg" | "xl" | "full";
  draggable?: boolean;
  closable?: boolean;
  minimizable?: boolean;
  onClose?: () => void;
}

const POSITION_CONFIG = {
  "bottom-right": "fixed bottom-4 right-4",
  "bottom-left": "fixed bottom-4 left-4",
  "top-right": "fixed top-4 right-4",
  "top-left": "fixed top-4 left-4",
  center: "fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
};

const WIDTH_CONFIG = {
  sm: "w-96",
  md: "w-[480px]",
  lg: "w-[600px]",
  xl: "w-[800px]",
  full: "w-full max-w-4xl",
};

const HEIGHT_CONFIG = {
  sm: "h-96",
  md: "h-[500px]",
  lg: "h-[600px]",
  xl: "h-[700px]",
  full: "h-[90vh]",
};

export function RealtimeDialog({
  dialogId,
  title = "实时对话",
  className,
  position = "bottom-right",
  width = "md",
  height = "lg",
  closable = true,
  minimizable = true,
  onClose,
}: RealtimeDialogProps) {
  const [isMinimized, setIsMinimized] = useState(false);
  const [isSessionClosed, setIsSessionClosed] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket连接（仅用于接收实时推送）
  const { status, subscribeToDialog, isConnected } = useWebSocket();

  // HTTP API（用于发送消息和获取对话框）
  const { sendMessage, getDialog, stopAgent } = useAgentApi();

  // 消息存储
  const {
    currentDialog,
    setCurrentDialog,
    messages,
    getStreamingContent,
    getThinkingMessages,
    getToolCalls,
  } = useMessageStore();

  // 加载对话框数据
  useEffect(() => {
    if (dialogId) {
      getDialog(dialogId).then((result) => {
        if (result.success && result.data) {
          setCurrentDialog(result.data);
        }
      });
    }
  }, [dialogId, getDialog, setCurrentDialog]);

  // 订阅WebSocket推送
  useEffect(() => {
    if (isConnected && dialogId) {
      subscribeToDialog(dialogId);
    }
  }, [isConnected, dialogId, subscribeToDialog]);

  // 自动滚动到底部
  useEffect(() => {
    if (!isMinimized && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isMinimized]);

  // 组织消息层次结构
  const organizedMessages = useMemo(() => {
    const parentMap = new Map<string, RealtimeMessage[]>();
    const parentMessages: RealtimeMessage[] = [];

    messages.forEach((msg) => {
      if (msg.parent_id) {
        // 这是子消息
        if (!parentMap.has(msg.parent_id)) {
          parentMap.set(msg.parent_id, []);
        }
        parentMap.get(msg.parent_id)!.push(msg);
      } else {
        // 这是父消息
        parentMessages.push(msg);
      }
    });

    return {
      parentMessages,
      childMap: parentMap,
    };
  }, [messages]);

  // 获取对话框状态
  const dialogStatus = useMemo(() => {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) return "completed";
    if (lastMessage.status === "streaming") return "streaming";
    if (lastMessage.status === "pending") return "pending";
    if (lastMessage.status === "error") return "error";
    return "completed";
  }, [messages]);

  // 调试：打印状态
  useEffect(() => {
    console.log("[RealtimeDialog] dialogStatus:", dialogStatus, "messages count:", messages.length);
    if (messages.length > 0) {
      console.log("[RealtimeDialog] last message status:", messages[messages.length - 1]?.status);
    }
  }, [dialogStatus, messages]);

  // 发送消息
  const handleSend = async () => {
    if (!inputValue.trim() || isSessionClosed) return;
    await sendMessage(dialogId, inputValue.trim());
    setInputValue("");
  };

  // 停止当前Agent运行
  const handleStopAgent = async () => {
    if (dialogStatus !== "streaming" && dialogStatus !== "pending") return;
    setIsStopping(true);
    try {
      const result = await stopAgent();
      if (result.success) {
        console.log("[RealtimeDialog] Agent stopped successfully");
      } else {
        console.error("[RealtimeDialog] Failed to stop agent:", result.message);
      }
    } catch (e) {
      console.error("[RealtimeDialog] Error stopping agent:", e);
    } finally {
      setIsStopping(false);
    }
  };

  // 关闭会话（保留会话ID但结束当前对话）
  const handleCloseSession = () => {
    if (confirm("确定要关闭当前会话吗？会话历史将被保留。")) {
      setIsSessionClosed(true);
      // 可选：调用onClose回调通知父组件
      onClose?.();
    }
  };

  // 处理回车发送
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 如果最小化，显示简化视图
  if (isMinimized) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={cn(POSITION_CONFIG[position], "z-50")}
      >
        <button
          onClick={() => setIsMinimized(false)}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-full shadow-lg",
            "bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700",
            "hover:shadow-xl transition-shadow",
            isSessionClosed && "opacity-70"
          )}
        >
          <StatusIndicator
            status={isSessionClosed ? "completed" : (dialogStatus as any)}
            size="sm"
            animate={!isSessionClosed && dialogStatus === "streaming"}
          />
          <MessageSquare className="h-4 w-4 text-zinc-600" />
          <span className={cn(
            "text-sm font-medium",
            isSessionClosed
              ? "text-zinc-500 line-through"
              : "text-zinc-700 dark:text-zinc-300"
          )}>
            {isSessionClosed ? `${title} (已结束)` : title}
          </span>
          {messages.length > 0 && (
            <span className={cn(
              "text-white text-xs rounded-full px-1.5 py-0.5",
              isSessionClosed ? "bg-zinc-400" : "bg-blue-500"
            )}>
              {messages.length}
            </span>
          )}
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className={cn(
        POSITION_CONFIG[position],
        WIDTH_CONFIG[width],
        HEIGHT_CONFIG[height],
        "z-50 flex flex-col rounded-xl shadow-2xl",
        "bg-white dark:bg-zinc-900",
        "border border-zinc-200 dark:border-zinc-700",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 rounded-t-xl bg-zinc-50 dark:bg-zinc-800/50">
        <div className="flex items-center gap-3">
          <StatusIndicator
            status={isSessionClosed ? "completed" : (dialogStatus as any)}
            size="sm"
            animate={!isSessionClosed && dialogStatus === "streaming"}
          />
          <MessageSquare className="h-4 w-4 text-zinc-600" />
          <h3 className={cn(
            "font-semibold",
            isSessionClosed
              ? "text-zinc-500 dark:text-zinc-500 line-through"
              : "text-zinc-800 dark:text-zinc-200"
          )}>
            {isSessionClosed ? `${title} (已结束)` : title}
          </h3>
          <span className="text-xs text-zinc-400">
            ({messages.length} 条消息)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* 连接状态 */}
          {isConnected ? (
            <Wifi className="h-4 w-4 text-green-500" />
          ) : (
            <WifiOff className="h-4 w-4 text-red-500" />
          )}

          {/* 停止按钮 - 始终显示但样式根据状态变化 */}
          <button
            onClick={handleStopAgent}
            disabled={isStopping || isSessionClosed}
            className={cn(
              "flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-colors border",
              isSessionClosed
                ? "bg-zinc-100 text-zinc-400 border-zinc-200 cursor-not-allowed"
                : (dialogStatus === "streaming" || dialogStatus === "pending")
                  ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-300 dark:border-red-700 hover:bg-red-200 dark:hover:bg-red-900/50 animate-pulse"
                  : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border-zinc-300 dark:border-zinc-600 hover:bg-zinc-200 dark:hover:bg-zinc-700"
            )}
            title={isSessionClosed ? "会话已结束" : "停止当前Agent运行"}
          >
            <Square className="h-3.5 w-3.5 fill-current" />
            <span>{isStopping ? "停止中..." : "停止"}</span>
          </button>

          {/* 关闭会话按钮 */}
          {!isSessionClosed && (
            <button
              onClick={handleCloseSession}
              className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors text-xs font-medium"
              title="关闭会话（保留会话ID）"
            >
              <Power className="h-3.5 w-3.5" />
              <span>结束</span>
            </button>
          )}

          {/* 最小化按钮 */}
          {minimizable && (
            <button
              onClick={() => setIsMinimized(true)}
              className="p-1.5 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
            >
              <Minimize2 className="h-4 w-4 text-zinc-500" />
            </button>
          )}

          {/* 关闭按钮 */}
          {closable && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30 hover:text-red-600 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* 会话已关闭提示 */}
        {isSessionClosed && (
          <div className="flex items-center justify-center gap-2 py-2 px-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <Power className="h-4 w-4 text-amber-600" />
            <span className="text-sm text-amber-700 dark:text-amber-400">
              会话已结束（会话ID: {dialogId.slice(0, 8)}...）
            </span>
          </div>
        )}
        {organizedMessages.parentMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-400">
            <MessageSquare className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm">等待消息...</p>
          </div>
        ) : (
          <>
            {organizedMessages.parentMessages.map((message, index) => {
              const childMessages =
                organizedMessages.childMap.get(message.id) || [];
              const isStreaming =
                message.status === "streaming" &&
                index === organizedMessages.parentMessages.length - 1;

              return (
                <CollapsibleMessage
                  key={message.id}
                  message={message}
                  childMessages={childMessages}
                  isStreaming={isStreaming}
                  defaultExpanded={
                    message.type !== "tool_call" &&
                    message.type !== "tool_result" &&
                    index >= organizedMessages.parentMessages.length - 2
                  }
                />
              );
            })}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-700">
        {isSessionClosed ? (
          <div className="flex items-center justify-center gap-2 py-2 text-zinc-500 text-sm">
            <Power className="h-4 w-4" />
            <span>会话已结束，无法发送新消息</span>
          </div>
        ) : (
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息..."
                disabled={false}
                className={cn(
                  "w-full resize-none rounded-lg border px-3 py-2",
                  "text-sm text-zinc-700 dark:text-zinc-300",
                  "placeholder:text-zinc-400",
                  "focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500",
                  "bg-zinc-50 dark:bg-zinc-800",
                  "border-zinc-200 dark:border-zinc-700",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                )}
                rows={1}
                style={{ minHeight: "40px", maxHeight: "120px" }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!inputValue.trim()}
              className={cn(
                "flex items-center justify-center w-10 h-10 rounded-lg",
                "bg-blue-500 text-white",
                "hover:bg-blue-600 active:bg-blue-700",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-colors",
              )}
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// 对话框容器组件 - 用于管理多个对话框
interface RealtimeDialogContainerProps {
  children?: React.ReactNode;
}

export function RealtimeDialogContainer({
  children,
}: RealtimeDialogContainerProps) {
  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      <div className="relative w-full h-full">{children}</div>
    </div>
  );
}
