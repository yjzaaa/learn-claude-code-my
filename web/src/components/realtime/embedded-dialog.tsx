"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAgentApi } from "@/hooks/useAgentApi";
import { useMessageStore } from "@/hooks/useMessageStore";
import type { RealtimeMessage } from "@/types/realtime-message";
import { CollapsibleMessage } from "./collapsible-message";
import { StatusIndicator } from "./status-indicator";
import { MessageSquare, Send, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface EmbeddedDialogProps {
  className?: string;
}

export function EmbeddedDialog({ className }: EmbeddedDialogProps) {
  const [dialogId, setDialogId] = useState<string>("");
  const [inputValue, setInputValue] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string>("");
  const activeDialogIdRef = useRef<string>("");
  const creatingDialogPromiseRef = useRef<Promise<string> | null>(null);

  // WebSocket连接
  const { status, subscribeToDialog, isConnected } = useWebSocket();

  // HTTP API
  const { sendMessage, createDialog, getDialog } = useAgentApi();

  // 消息存储
  const { currentDialog, setCurrentDialog, messages } = useMessageStore();

  const activeDialogId = dialogId || currentDialog?.id || "";

  useEffect(() => {
    activeDialogIdRef.current = activeDialogId;
  }, [activeDialogId]);

  // 初始化：如果没有对话框，创建一个
  useEffect(() => {
    if (!dialogId) {
      void (async () => {
        const result = await createDialog("Agent 对话");
        if (result.success && result.data) {
          activeDialogIdRef.current = result.data.id;
          setDialogId(result.data.id);
          setCurrentDialog(result.data);
          if (isConnected) {
            subscribeToDialog(result.data.id);
          }
        }
      })();
    }
  }, [
    dialogId,
    createDialog,
    isConnected,
    setCurrentDialog,
    subscribeToDialog,
  ]);

  // 加载对话框数据并订阅
  useEffect(() => {
    if (dialogId) {
      getDialog(dialogId).then((result) => {
        if (result.success && result.data) {
          // 设置对话框（会自动添加到 dialogs 列表）
          setCurrentDialog(result.data);
          // 订阅 WebSocket
          subscribeToDialog(dialogId);
        }
      });
    }
  }, [dialogId, getDialog, setCurrentDialog, subscribeToDialog]);

  // 监控 WebSocket 连接状态
  useEffect(() => {
    console.log(
      "[EmbeddedDialog] WebSocket status:",
      status,
      "isConnected:",
      isConnected,
    );
  }, [status, isConnected]);

  // 当对话框 ID 变化时，重新订阅
  useEffect(() => {
    if (dialogId && isConnected) {
      console.log("[EmbeddedDialog] Resubscribing to dialog:", dialogId);
      subscribeToDialog(dialogId);
    }
  }, [dialogId, isConnected, subscribeToDialog]);

  // 调试：打印消息变化
  useEffect(() => {
    console.log("[EmbeddedDialog] Messages updated:", messages);
  }, [messages]);

  // 组织消息层次结构
  const organizedMessages = useMemo(() => {
    console.log("[EmbeddedDialog] Organizing messages:", messages);
    const parentMsgs = messages.filter((msg) => !msg.parent_id);
    const childMap = messages.reduce((map, msg) => {
      if (msg.parent_id) {
        if (!map.has(msg.parent_id)) {
          map.set(msg.parent_id, []);
        }
        map.get(msg.parent_id)!.push(msg);
        console.log(
          `[EmbeddedDialog] Child message ${msg.id} (type: ${msg.type}) -> parent ${msg.parent_id}`,
        );
      }
      return map;
    }, new Map<string, RealtimeMessage[]>());

    console.log(
      "[EmbeddedDialog] Parent messages:",
      parentMsgs.map((m) => ({ id: m.id, type: m.type })),
    );
    console.log(
      "[EmbeddedDialog] Child map keys:",
      Array.from(childMap.keys()),
    );

    return { parentMessages: parentMsgs, childMap };
  }, [messages]);

  // 获取对话框状态
  const dialogStatus = (() => {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) return "completed";
    if (lastMessage.status === "streaming") return "streaming";
    if (lastMessage.status === "pending") return "pending";
    if (lastMessage.status === "error") return "error";
    return "completed";
  })();

  // 发送消息
  const ensureDialogReady = useCallback(async (): Promise<string> => {
    const currentId = activeDialogIdRef.current || activeDialogId;
    if (currentId) {
      return currentId;
    }

    if (creatingDialogPromiseRef.current) {
      return creatingDialogPromiseRef.current;
    }

    creatingDialogPromiseRef.current = (async () => {
      const result = await createDialog("Agent 对话");
      if (result.success && result.data) {
        activeDialogIdRef.current = result.data.id;
        setDialogId(result.data.id);
        setCurrentDialog(result.data);
        if (isConnected) {
          subscribeToDialog(result.data.id);
        }
        return result.data.id;
      }

      console.error("[EmbeddedDialog] createDialog failed:", result);
      setSendError(result.message || "创建对话失败，请检查后端服务");
      return "";
    })();

    try {
      return await creatingDialogPromiseRef.current;
    } finally {
      creatingDialogPromiseRef.current = null;
    }
  }, [
    activeDialogId,
    createDialog,
    isConnected,
    setCurrentDialog,
    subscribeToDialog,
  ]);

  const handleSend = async () => {
    if (isSending) {
      return;
    }

    const content = inputValue.trim();
    console.log(
      "[EmbeddedDialog] handleSend called, inputValue:",
      content,
      "dialogId:",
      activeDialogId,
    );

    if (!content) {
      console.log("[EmbeddedDialog] Send aborted - empty input");
      return;
    }

    setSendError("");
    setIsSending(true);
    try {
      const targetDialogId =
        activeDialogIdRef.current || (await ensureDialogReady());
      if (!targetDialogId) {
        console.log("[EmbeddedDialog] Send aborted - failed to create dialog");
        return;
      }

      setInputValue("");

      console.log("[EmbeddedDialog] Sending message to API...");
      const result = await sendMessage(targetDialogId, content);
      console.log("[EmbeddedDialog] sendMessage result:", result);
      if (!result.success) {
        // Keep user input when API send fails, so users can retry quickly.
        setInputValue(content);
        setSendError(result.message || "发送失败，请检查后端接口");
      }
    } finally {
      setIsSending(false);
    }
  };

  // 处理回车发送
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 创建新对话框
  const handleNewDialog = async () => {
    setIsCreating(true);
    try {
      const result = await createDialog("新对话");
      if (result.success && result.data) {
        activeDialogIdRef.current = result.data.id;
        setDialogId(result.data.id);
        setCurrentDialog(result.data);
        if (isConnected) {
          subscribeToDialog(result.data.id);
        }
      }
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div
      className={cn(
        "flex flex-col rounded-xl border border-zinc-200 bg-white shadow-sm",
        "dark:border-zinc-800 dark:bg-zinc-900",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 rounded-t-xl bg-zinc-50 dark:bg-zinc-800/50">
        <div className="flex items-center gap-3">
          <StatusIndicator
            status={dialogStatus as any}
            size="sm"
            animate={dialogStatus === "streaming"}
          />
          <MessageSquare className="h-4 w-4 text-zinc-600" />
          <h3 className="font-semibold text-zinc-800 dark:text-zinc-200">
            {currentDialog?.title || "实时对话"}
          </h3>
          <span className="text-xs text-zinc-400">
            ({messages.length} 条消息)
          </span>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleNewDialog}
          disabled={isCreating}
        >
          <Plus className="h-4 w-4 mr-1" />
          新建对话
        </Button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[400px] max-h-[600px]">
        {organizedMessages.parentMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-zinc-400">
            <MessageSquare className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm">开始对话...</p>
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
                  allMessages={messages}
                  isStreaming={isStreaming}
                  defaultExpanded={
                    message.type !== "tool_call" &&
                    message.type !== "tool_result" &&
                    index >= organizedMessages.parentMessages.length - 2
                  }
                />
              );
            })}
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-zinc-200 dark:border-zinc-700">
        {sendError ? (
          <div className="mb-2 text-xs text-red-600 dark:text-red-400">
            {sendError}
          </div>
        ) : null}
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息..."
              className={cn(
                "w-full resize-none rounded-lg border px-3 py-2",
                "text-sm text-zinc-700 dark:text-zinc-300",
                "placeholder:text-zinc-400",
                "focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500",
                "bg-zinc-50 dark:bg-zinc-800",
                "border-zinc-200 dark:border-zinc-700",
              )}
              rows={1}
              style={{ minHeight: "40px", maxHeight: "120px" }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending}
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
      </div>
    </div>
  );
}
