"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAgentApi } from "@/hooks/useAgentApi";
import { useMessageStore } from "@/hooks/useMessageStore";
import { buildMessageRenderItems } from "@/lib/realtime/studio-view-model";
import type { ChatSession } from "@/types/openai";
import { CollapsibleMessage } from "./collapsible-message";
import { StatusIndicator } from "./status-indicator";
import { MessageSquare, Send, Plus, Square, Workflow } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RuntimeFlowchart } from "./runtime-flowchart";
import { HookStatsPanel } from "./hook-stats-panel";

interface EmbeddedDialogProps {
  className?: string;
}

export function EmbeddedDialog({ className }: EmbeddedDialogProps) {
  const [dialogId, setDialogId] = useState<string>("");
  const [inputValue, setInputValue] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string>("");
  const [isStopping, setIsStopping] = useState(false);
  const [showFlowchart, setShowFlowchart] = useState(false);
  const activeDialogIdRef = useRef<string>("");
  const creatingDialogPromiseRef = useRef<Promise<string> | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket连接
  const { status, subscribeToDialog, isConnected } = useWebSocket();

  // HTTP API
  const { sendMessage, createDialog, getDialog, stopAgent } = useAgentApi();

  // 消息存储
  const { currentDialog, setCurrentDialog, messages, streamState } =
    useMessageStore();

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
          // 转换 Dialog 为 ChatSession 类型
          setCurrentDialog({
            ...result.data,
            created_at: Date.parse(result.data.created_at) || Date.now(),
            updated_at: Date.parse(result.data.updated_at) || Date.now(),
          } as ChatSession);
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
          // 转换 Dialog 为 ChatSession 类型
          setCurrentDialog({
            ...result.data,
            created_at: Date.parse(result.data.created_at) || Date.now(),
            updated_at: Date.parse(result.data.updated_at) || Date.now(),
          } as ChatSession);
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

  // 随消息增长和流式更新自动滚动到底部
  useEffect(() => {
    if (!messagesEndRef.current) return;
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    });
  }, [
    messages.length,
    streamState.accumulatedContent,
    streamState.accumulatedReasoning,
  ]);

  // 获取对话框状态
  const dialogStatus = (() => {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) return "completed";
    // ChatMessage 没有 status 字段，根据 role 判断
    if (lastMessage.role === "assistant") {
      // 检查是否是流式状态（通过全局事件或 WebSocket 状态判断）
      return "streaming";
    }
    return "completed";
  })();

  // 检查是否有正在运行的Agent（考虑所有消息，不只是最后一条）
  const hasRunningAgent = useMemo(() => {
    // ChatMessage 没有 status 字段，简化判断
    return messages.some(
      (msg) =>
        msg.role === "assistant" && msg.tool_calls && msg.tool_calls.length > 0,
    );
  }, [messages]);

  const renderItems = useMemo(
    () => buildMessageRenderItems(messages),
    [messages],
  );

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
        // 转换 Dialog 为 ChatSession 类型
        setCurrentDialog({
          ...result.data,
          created_at: Date.parse(result.data.created_at) || Date.now(),
          updated_at: Date.parse(result.data.updated_at) || Date.now(),
        } as ChatSession);
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
        // 转换 Dialog 为 ChatSession 类型
        setCurrentDialog({
          ...result.data,
          created_at: Date.parse(result.data.created_at) || Date.now(),
          updated_at: Date.parse(result.data.updated_at) || Date.now(),
        } as ChatSession);
        if (isConnected) {
          subscribeToDialog(result.data.id);
        }
      }
    } finally {
      setIsCreating(false);
    }
  };

  // 停止当前Agent运行
  const handleStopAgent = async () => {
    if (dialogStatus !== "streaming") return;
    setIsStopping(true);
    try {
      const result = await stopAgent();
      if (result.success) {
        console.log("[EmbeddedDialog] Agent stopped successfully");
      } else {
        console.error("[EmbeddedDialog] Failed to stop agent:", result.message);
      }
    } catch (e) {
      console.error("[EmbeddedDialog] Error stopping agent:", e);
    } finally {
      setIsStopping(false);
    }
  };

  return (
    <div
      className={cn(
        "flex h-full flex-col overflow-hidden rounded-2xl border border-[#d6deeb] bg-white/85 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.45)] backdrop-blur-sm",
        "dark:border-zinc-700 dark:bg-zinc-900/85",
        className,
      )}
    >
      {/* Header */}
<<<<<<< HEAD
      <div className="shrink-0 border-b border-[#d6deeb] bg-white/90 px-4 py-3 dark:border-zinc-700 dark:bg-zinc-900/80">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <StatusIndicator
              status={dialogStatus as any}
              size="sm"
              animate={dialogStatus === "streaming"}
            />
            <MessageSquare className="h-4 w-4 text-cyan-700" />
            <h3
              className="font-semibold text-slate-900 dark:text-zinc-100"
              style={{
                fontFamily: '"Space Grotesk", "Noto Sans SC", sans-serif',
              }}
            >
              实时对话
            </h3>
            <span className="text-xs text-slate-500 dark:text-zinc-400">
              ({messages.length} 条消息)
            </span>
          </div>
=======
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50 shrink-0">
        <div className="flex items-center gap-3">
          <StatusIndicator
            status={dialogStatus as any}
            size="sm"
            animate={dialogStatus === "streaming"}
          />
          <MessageSquare className="h-4 w-4 text-zinc-600" />
          <h3 className="font-semibold text-zinc-800 dark:text-zinc-200">
            {"实时对话"}
          </h3>
          <span className="text-xs text-zinc-400">
            ({messages.length} 条消息)
          </span>
        </div>
>>>>>>> 4aa0591 (feat: 完善实时对话界面的 Markdown 渲染和工具结果显示)

          <div className="flex items-center gap-2">
            {/* 流程图按钮 */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFlowchart(!showFlowchart)}
              className={cn(
                "border-slate-300 bg-white text-slate-700 transition-colors hover:bg-slate-50",
                showFlowchart
                  ? "border-cyan-200 bg-cyan-50 text-cyan-700 hover:bg-cyan-100 hover:text-cyan-800"
                  : "",
              )}
            >
              <Workflow className="h-4 w-4 mr-1" />
              流程图
            </Button>

            {/* 停止按钮 - 当Agent正在运行时显示 */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleStopAgent}
              disabled={isStopping || !hasRunningAgent}
              className={cn(
                "border-slate-300 bg-white text-slate-700 transition-colors hover:bg-slate-50",
                hasRunningAgent
                  ? "animate-pulse border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 hover:text-rose-800"
                  : "",
              )}
            >
              <Square className="h-4 w-4 mr-1 fill-current" />
              {isStopping ? "停止中..." : "停止"}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleNewDialog}
              disabled={isCreating}
              className="border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            >
              <Plus className="h-4 w-4 mr-1" />
              新建对话
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content Area - 左右布局 */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* 左侧：消息区域 */}
        <div
          className={cn(
            "flex flex-col transition-all duration-300 ease-in-out",
            showFlowchart ? "w-3/4" : "w-full",
          )}
        >
          {/* Sticky Dashboard */}
          <div className="shrink-0 border-b border-[#d6deeb] bg-gradient-to-r from-white to-[#f0f9ff] p-3 dark:border-zinc-700 dark:bg-zinc-900/60">
            <HookStatsPanel
              hookStats={streamState.hookStats}
              runReport={streamState.runReport}
            />
          </div>

          {/* Messages Area */}
          <div className="flex-1 space-y-3 overflow-y-auto bg-[linear-gradient(180deg,#f8fafc_0%,#f0f9ff_60%,#ecfeff_100%)] p-4 dark:bg-zinc-900">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-slate-500 dark:text-zinc-400">
                <MessageSquare className="mb-3 h-12 w-12 opacity-40" />
                <p className="text-sm">
                  开始对话，系统会展示完整的工具执行轨迹
                </p>
              </div>
            ) : (
              <>
                {renderItems.map(
                  ({ index, message, toolResults, attachedAssistant }) => {
                    const isStreaming =
                      streamState.isStreaming &&
                      message.role === "assistant" &&
                      !!message.id &&
                      message.id === streamState.currentMessageId;

                    const shouldHidePendingAssistantPlaceholder =
                      isStreaming &&
                      message.role === "assistant" &&
                      !message.tool_calls?.length &&
                      !(streamState.accumulatedContent || "").trim() &&
                      !(streamState.accumulatedReasoning || "").trim() &&
                      !(message.content || "").trim();

                    if (shouldHidePendingAssistantPlaceholder) {
                      return null;
                    }

                    return (
                      <CollapsibleMessage
                        key={`${message.id || message.role}-${index}`}
                        message={message}
                        toolResults={toolResults}
                        attachedAssistant={attachedAssistant}
                        isStreaming={isStreaming}
                        streamingContent={
                          isStreaming
                            ? streamState.accumulatedContent
                            : undefined
                        }
                        streamingReasoning={
                          isStreaming
                            ? streamState.accumulatedReasoning
                            : undefined
                        }
                        defaultExpanded={
                          message.role === "assistant" &&
                          message.tool_calls &&
                          message.tool_calls.length > 0
                            ? false
                            : index >= messages.length - 2
                        }
                      />
                    );
                  },
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="shrink-0 border-t border-[#d6deeb] bg-white/90 p-3 dark:border-zinc-700 dark:bg-zinc-900/90">
            {sendError ? (
              <div className="mb-2 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
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
                    "text-sm text-slate-700 dark:text-zinc-200",
                    "placeholder:text-slate-400",
                    "focus:outline-none focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500",
                    "bg-white dark:bg-zinc-800",
                    "border-slate-300 dark:border-zinc-700",
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
                  "bg-cyan-600 text-white",
                  "hover:bg-cyan-700 active:bg-cyan-800",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  "transition-colors",
                )}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：运行时流程图侧边栏 */}
        <RuntimeFlowchart
          isOpen={showFlowchart}
          onClose={() => setShowFlowchart(false)}
          messages={messages}
        />
      </div>
    </div>
  );
}
