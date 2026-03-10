"use client";

import {
  useEffect,
  useState,
  useCallback,
  useRef,
  type WheelEvent,
} from "react";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAgentApi } from "@/hooks/useAgentApi";
import { useMessageStore } from "@/hooks/useMessageStore";
import type { ChatSession } from "@/types/openai";
import type { SkillEditApproval } from "@/types/dialog";
import { CollapsibleMessage } from "./collapsible-message";
import { StatusIndicator } from "./status-indicator";
import {
  MessageSquare,
  Send,
  Plus,
  Square,
  Workflow,
  Bell,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { RuntimeFlowchart } from "./runtime-flowchart";
import { buildMessageRenderItems } from "@/lib/realtime/studio-view-model";
import { CodeDiff } from "@/components/diff/code-diff";

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
  const [showSkillEditPanel, setShowSkillEditPanel] = useState(false);
  const [selectedApproval, setSelectedApproval] =
    useState<SkillEditApproval | null>(null);
  const [editedSkillContent, setEditedSkillContent] = useState("");
  const [isDecidingSkillEdit, setIsDecidingSkillEdit] = useState(false);
  const activeDialogIdRef = useRef<string>("");

  // WebSocket连接
  const { subscribeToDialog, isConnected, pendingSkillEdits } = useWebSocket();

  // HTTP API
  const {
    sendMessage,
    createDialog,
    getDialog,
    stopAgent,
    getPendingSkillEdits,
    decideSkillEdit,
  } = useAgentApi();

  // 消息存储
  const {
    dialogs,
    currentDialog,
    setCurrentDialog,
    resetAndSetDialog,
    messages,
    isStreaming,
    streamingContent,
    streamingReasoning,
    currentStreamingMessageId,
  } = useMessageStore();

  const activeDialogId = dialogId || currentDialog?.id || "";
  const activeSkillApprovals = pendingSkillEdits.filter(
    (item) => !activeDialogId || item.dialog_id === activeDialogId,
  );

  useEffect(() => {
    activeDialogIdRef.current = activeDialogId;
  }, [activeDialogId]);

  useEffect(() => {
    if (!activeDialogId) return;
    getPendingSkillEdits(activeDialogId).then((result) => {
      if (!result.success || !result.data || result.data.length === 0) return;
      if (!selectedApproval) {
        setSelectedApproval(result.data[0]);
        setEditedSkillContent(result.data[0].new_content || "");
      }
    });
  }, [activeDialogId, getPendingSkillEdits, selectedApproval]);

  useEffect(() => {
    if (!selectedApproval && activeSkillApprovals.length > 0) {
      setSelectedApproval(activeSkillApprovals[0]);
      setEditedSkillContent(activeSkillApprovals[0].new_content || "");
      return;
    }

    if (
      selectedApproval &&
      activeSkillApprovals.findIndex(
        (item) => item.approval_id === selectedApproval.approval_id,
      ) === -1
    ) {
      const next = activeSkillApprovals[0] || null;
      setSelectedApproval(next);
      setEditedSkillContent(next?.new_content || "");
    }
  }, [activeSkillApprovals, selectedApproval]);

  const handleSkillEditDecision = useCallback(
    async (decision: "accept" | "reject" | "edit_accept") => {
      if (!selectedApproval || isDecidingSkillEdit) return;
      setIsDecidingSkillEdit(true);
      try {
        await decideSkillEdit(
          selectedApproval.approval_id,
          decision,
          decision === "edit_accept" ? editedSkillContent : undefined,
        );
      } finally {
        setIsDecidingSkillEdit(false);
      }
    },
    [
      decideSkillEdit,
      editedSkillContent,
      isDecidingSkillEdit,
      selectedApproval,
    ],
  );

  // Keep textarea wheel scrolling local so parent panels do not hijack it.
  const handleTextareaWheel = useCallback(
    (e: WheelEvent<HTMLTextAreaElement>) => {
      const el = e.currentTarget;
      if (el.scrollHeight <= el.clientHeight) {
        return;
      }
      e.stopPropagation();
    },
    [],
  );

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
    console.log("[EmbeddedDialog] WebSocket isConnected:", isConnected);
  }, [isConnected]);

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

  // 使用 useMessageStore 中的 isStreaming 状态
  const dialogStatus = isStreaming ? "streaming" : "completed";

  // 构建消息渲染项（用于正确匹配 toolResults）
  const renderItems = buildMessageRenderItems(messages);

  const handleSend = async () => {
    if (isSending) {
      return;
    }

    const content = inputValue.trim();
    console.log("[EmbeddedDialog] handleSend called, inputValue:", content);

    if (!content) {
      console.log("[EmbeddedDialog] Send aborted - empty input");
      return;
    }

    setSendError("");
    setIsSending(true);
    try {
      // 优先复用当前对话，只有首次发送时才创建新对话。
      let targetDialogId = activeDialogIdRef.current || activeDialogId;

      if (!targetDialogId) {
        const result = await createDialog("Agent 对话");
        if (!result.success || !result.data) {
          console.error("[EmbeddedDialog] Failed to create dialog:", result);
          setSendError(result.message || "创建对话失败，请检查后端服务");
          return;
        }

        const newDialogId = result.data.id;
        targetDialogId = newDialogId;
        activeDialogIdRef.current = newDialogId;
        setDialogId(newDialogId);

        // 仅在新建对话时重置当前会话状态。
        resetAndSetDialog({
          ...result.data,
          created_at: Date.parse(result.data.created_at) || Date.now(),
          updated_at: Date.parse(result.data.updated_at) || Date.now(),
        } as ChatSession);

        if (isConnected) {
          subscribeToDialog(newDialogId);
        }
      }

      setInputValue("");

      console.log(
        "[EmbeddedDialog] Sending message to dialog:",
        targetDialogId,
      );
      const sendResult = await sendMessage(targetDialogId, content);
      console.log("[EmbeddedDialog] sendMessage result:", sendResult);
      if (!sendResult.success) {
        // Keep user input when API send fails, so users can retry quickly.
        setInputValue(content);
        setSendError(sendResult.message || "发送失败，请检查后端接口");
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
        // 转换 Dialog 为 ChatSession 类型，使用 resetAndSetDialog 重置状态
        resetAndSetDialog({
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
    if (!isStreaming) return;
    setIsStopping(true);
    try {
      console.log(
        "[EmbeddedDialog] Stopping agent, current messages:",
        messages,
      );
      const result = await stopAgent();
      if (result.success) {
        console.log("[EmbeddedDialog] Agent stopped successfully");
        console.log("[EmbeddedDialog] Messages after stop:", messages);
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
        "flex flex-col h-full rounded-xl border border-zinc-200 bg-white shadow-sm overflow-hidden",
        "dark:border-zinc-800 dark:bg-zinc-900",
        className,
      )}
    >
      {/* Header */}
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

        <div className="flex items-center gap-2">
          {/* 流程图按钮 */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFlowchart(!showFlowchart)}
            className={cn(
              "transition-colors",
              showFlowchart
                ? "bg-blue-50 text-blue-600 border-blue-200 hover:bg-blue-100 hover:text-blue-700"
                : "",
            )}
          >
            <Workflow className="h-4 w-4 mr-1" />
            流程图
          </Button>

          {/* 停止按钮 - 当Agent正在流式输出时显示 */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleStopAgent}
            disabled={isStopping || !isStreaming}
            className={cn(
              "transition-colors",
              isStreaming
                ? "bg-red-50 text-red-600 border-red-200 hover:bg-red-100 hover:text-red-700 animate-pulse"
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
          >
            <Plus className="h-4 w-4 mr-1" />
            新建对话
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSkillEditPanel((v) => !v)}
            className="relative"
          >
            <Bell className="h-4 w-4 mr-1" />
            Skill审批
            {activeSkillApprovals.length > 0 && (
              <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1 rounded-full bg-red-500 text-white text-[10px] leading-5 text-center">
                {activeSkillApprovals.length}
              </span>
            )}
          </Button>
        </div>
      </div>

      {showSkillEditPanel && (
        <div className="border-b border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/40 p-3 space-y-3">
          {activeSkillApprovals.length === 0 ? (
            <div className="text-xs text-zinc-500">当前无待审批 skill 修改</div>
          ) : (
            <>
              <div className="flex gap-2 flex-wrap">
                {activeSkillApprovals.map((approval) => (
                  <button
                    key={approval.approval_id}
                    onClick={() => {
                      setSelectedApproval(approval);
                      setEditedSkillContent(approval.new_content || "");
                    }}
                    className={cn(
                      "px-2 py-1 rounded text-xs border",
                      selectedApproval?.approval_id === approval.approval_id
                        ? "bg-blue-100 border-blue-300 text-blue-700"
                        : "bg-white dark:bg-zinc-900 border-zinc-300 dark:border-zinc-700",
                    )}
                  >
                    {approval.path}
                  </button>
                ))}
              </div>

              {selectedApproval && (
                <div className="space-y-3">
                  <CodeDiff
                    oldSource={selectedApproval.old_content || ""}
                    newSource={editedSkillContent}
                    oldLabel={`${selectedApproval.path} (old)`}
                    newLabel={`${selectedApproval.path} (new)`}
                  />

                  <textarea
                    value={editedSkillContent}
                    onChange={(e) => setEditedSkillContent(e.target.value)}
                    onWheel={handleTextareaWheel}
                    className="w-full h-28 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-2 text-xs font-mono overflow-y-auto overscroll-contain"
                    placeholder="可编辑后再接受"
                  />

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={isDecidingSkillEdit}
                      onClick={() => handleSkillEditDecision("accept")}
                    >
                      接受
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={isDecidingSkillEdit}
                      onClick={() => handleSkillEditDecision("reject")}
                    >
                      拒绝
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={isDecidingSkillEdit}
                      onClick={() => handleSkillEditDecision("edit_accept")}
                    >
                      编辑后接受
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Main Content Area - 三栏布局 */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* 左侧：历史对话列表 */}
        <div className="w-48 flex-shrink-0 border-r border-zinc-200 dark:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-900/50 flex flex-col">
          <div className="px-3 py-2 border-b border-zinc-200 dark:border-zinc-700">
            <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
              历史对话
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {dialogs.length === 0 ? (
              <div className="text-xs text-zinc-400 text-center py-4">
                暂无对话
              </div>
            ) : (
              dialogs.map((d) => (
                <button
                  key={d.id}
                  onClick={() => {
                    setDialogId(d.id);
                    setCurrentDialog(d);
                    if (isConnected) {
                      subscribeToDialog(d.id);
                    }
                  }}
                  className={cn(
                    "w-full text-left px-2 py-1.5 rounded-md text-xs transition-colors",
                    currentDialog?.id === d.id
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                      : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400",
                  )}
                >
                  <div className="font-medium truncate">{d.title}</div>
                  <div className="text-[10px] opacity-70 truncate">
                    {d.messages.length} 条消息 ·{" "}
                    {new Date(d.updated_at).toLocaleTimeString()}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* 中间：消息区域 */}
        <div
          className={cn(
            "flex flex-col transition-all duration-300 ease-in-out",
            showFlowchart ? "w-[calc(100%-12rem-25%)]" : "w-[calc(100%-12rem)]",
          )}
        >
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-zinc-400">
                <MessageSquare className="h-12 w-12 mb-3 opacity-30" />
                <p className="text-sm">开始对话...</p>
              </div>
            ) : (
              <>
                {renderItems
                  // 过滤掉工具结果消息，它们已经通过 toolResults 传递
                  .filter(({ message }) => message.role !== "tool")
                  .map(({ index, message, toolResults, attachedAssistant }) => {
                    const isMessageStreaming =
                      isStreaming &&
                      message.role === "assistant" &&
                      !!message.id &&
                      message.id === currentStreamingMessageId;

                    return (
                      <CollapsibleMessage
                        key={index}
                        message={message}
                        toolResults={toolResults}
                        attachedAssistant={attachedAssistant}
                        isStreaming={isMessageStreaming}
                        streamingContent={
                          isMessageStreaming ? streamingContent : undefined
                        }
                        streamingReasoning={
                          isMessageStreaming ? streamingReasoning : undefined
                        }
                        defaultExpanded={
                          // 只展开最后一条工具消息，其他都收起
                          message.role === "assistant" &&
                          message.tool_calls &&
                          message.tool_calls.length > 0 &&
                          index === messages.length - 1
                        }
                      />
                    );
                  })}
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="p-3 border-t border-zinc-200 dark:border-zinc-700 shrink-0">
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
