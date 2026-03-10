"use client";

import {
  useEffect,
  useState,
  useCallback,
  useRef,
  type WheelEvent,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
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
  Bell,
  ListTodo,
} from "lucide-react";
import { TodoPanel } from "./todo-panel";
import { Button } from "@/components/ui/button";
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
  const [showHistory, setShowHistory] = useState(false);
  const [rightPanelTab, setRightPanelTab] = useState<"none" | "todo">("none");
  const [showSkillEditDrawer, setShowSkillEditDrawer] = useState(false);
  const [selectedApproval, setSelectedApproval] =
    useState<SkillEditApproval | null>(null);
  const [editedSkillContent, setEditedSkillContent] = useState("");
  const [isDecidingSkillEdit, setIsDecidingSkillEdit] = useState(false);
  const activeDialogIdRef = useRef<string>("");

  const { subscribeToDialog, isConnected, pendingSkillEdits } = useWebSocket();

  const {
    sendMessage,
    createDialog,
    getDialog,
    stopAgent,
    getPendingSkillEdits,
    decideSkillEdit,
  } = useAgentApi();

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
    streamState,
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

  useEffect(() => {
    if (dialogId) {
      getDialog(dialogId).then((result) => {
        if (result.success && result.data) {
          setCurrentDialog({
            ...result.data,
            created_at: Date.parse(result.data.created_at) || Date.now(),
            updated_at: Date.parse(result.data.updated_at) || Date.now(),
          } as ChatSession);
          subscribeToDialog(dialogId);
        }
      });
    }
  }, [dialogId, getDialog, setCurrentDialog, subscribeToDialog]);

  useEffect(() => {
    console.log("[EmbeddedDialog] WebSocket isConnected:", isConnected);
  }, [isConnected]);

  useEffect(() => {
    if (dialogId && isConnected) {
      console.log("[EmbeddedDialog] Resubscribing to dialog:", dialogId);
      subscribeToDialog(dialogId);
    }
  }, [dialogId, isConnected, subscribeToDialog]);

  useEffect(() => {
    console.log("[EmbeddedDialog] Messages updated:", messages);
  }, [messages]);

  const dialogStatus = isStreaming ? "streaming" : "completed";
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
        setInputValue(content);
        setSendError(sendResult.message || "发送失败，请检查后端接口");
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewDialog = async () => {
    setIsCreating(true);
    try {
      const result = await createDialog("新对话");
      if (result.success && result.data) {
        activeDialogIdRef.current = result.data.id;
        setDialogId(result.data.id);
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
    <div className={cn("flex flex-col h-full bg-white dark:bg-zinc-950", className)}>
      {/* Compact Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 shrink-0">
        <div className="flex items-center gap-2">
          <StatusIndicator status={dialogStatus as any} size="sm" animate={dialogStatus === "streaming"} />
          <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {messages.length > 0 ? `${messages.length} messages` : "New Chat"}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowHistory((v) => !v)}
            className={cn("h-7 w-7 flex items-center justify-center rounded hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50", showHistory && "bg-zinc-200/50 dark:bg-zinc-700/50")}
            title="历史"
          >
            <MessageSquare className="h-3.5 w-3.5" />
          </button>

          <button
            onClick={() => setRightPanelTab(rightPanelTab === "todo" ? "none" : "todo")}
            className={cn("h-7 w-7 flex items-center justify-center rounded hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50 relative", rightPanelTab === "todo" && "bg-emerald-100/50 dark:bg-emerald-900/30 text-emerald-600")}
          >
            <ListTodo className="h-3.5 w-3.5" />
            {streamState.todos && streamState.todos.length > 0 && (
              <span className="absolute -top-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-emerald-500 text-white text-[8px] flex items-center justify-center">
                {streamState.todos.length}
              </span>
            )}
          </button>

          <button
            onClick={handleStopAgent}
            disabled={isStopping || !isStreaming}
            className={cn("h-7 w-7 flex items-center justify-center rounded hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50 disabled:opacity-50", isStreaming && "text-red-500")}
          >
            <Square className="h-3.5 w-3.5 fill-current" />
          </button>

          <button onClick={handleNewDialog} disabled={isCreating} className="h-7 w-7 flex items-center justify-center rounded hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50 disabled:opacity-50">
            <Plus className="h-3.5 w-3.5" />
          </button>

          <button
            onClick={() => setShowSkillEditDrawer(true)}
            className={cn("h-7 w-7 flex items-center justify-center rounded hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50 relative", activeSkillApprovals.length > 0 && "text-amber-500")}
          >
            <Bell className="h-3.5 w-3.5" />
            {activeSkillApprovals.length > 0 && (
              <span className="absolute -top-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-red-500 text-white text-[8px] flex items-center justify-center animate-pulse">
                {activeSkillApprovals.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Skill Edit Drawer */}
      {showSkillEditDrawer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-4xl max-h-[90vh] bg-white dark:bg-zinc-900 rounded-lg shadow-2xl flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-amber-500" />
                <h3 className="font-medium text-sm">Skill Approval</h3>
                {activeSkillApprovals.length > 0 && (
                  <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 text-xs">{activeSkillApprovals.length}</span>
                )}
              </div>
              <button onClick={() => setShowSkillEditDrawer(false)} className="p-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded">
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-hidden flex min-h-0">
              {activeSkillApprovals.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 p-8">
                  <Bell className="h-10 w-10 mb-2 opacity-30" />
                  <p className="text-sm">No pending approvals</p>
                </div>
              ) : (
                <>
                  <div className="w-56 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 overflow-y-auto">
                    <div className="p-2">
                      <span className="text-xs font-medium text-zinc-500">Pending</span>
                    </div>
                    <div className="px-1 pb-1 space-y-0.5">
                      {activeSkillApprovals.map((approval) => (
                        <button
                          key={approval.approval_id}
                          onClick={() => {
                            setSelectedApproval(approval);
                            setEditedSkillContent(approval.new_content || "");
                          }}
                          className={cn(
                            "w-full text-left px-2 py-1.5 rounded text-xs transition-colors",
                            selectedApproval?.approval_id === approval.approval_id
                              ? "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                              : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600",
                          )}
                        >
                          <div className="font-medium truncate">{approval.path}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex-1 flex flex-col min-h-0">
                    {selectedApproval ? (
                      <>
                        <div className="flex-1 overflow-y-auto p-4 space-y-3">
                          <CodeDiff
                            oldSource={selectedApproval.old_content || ""}
                            newSource={editedSkillContent}
                            oldLabel="Current"
                            newLabel="Proposed"
                          />
                          <textarea
                            value={editedSkillContent}
                            onChange={(e) => setEditedSkillContent(e.target.value)}
                            onWheel={handleTextareaWheel}
                            className="w-full h-24 rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-2 text-xs font-mono"
                            placeholder="Edit before accepting..."
                          />
                        </div>
                        <div className="px-4 py-2 border-t border-zinc-200 dark:border-zinc-800 flex gap-2">
                          <Button size="sm" onClick={() => handleSkillEditDecision("accept")} disabled={isDecidingSkillEdit} className="bg-emerald-600 hover:bg-emerald-700">
                            Accept
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleSkillEditDecision("reject")} disabled={isDecidingSkillEdit}>
                            Reject
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleSkillEditDecision("edit_accept")} disabled={isDecidingSkillEdit}>
                            Edit & Accept
                          </Button>
                        </div>
                      </>
                    ) : (
                      <div className="flex-1 flex items-center justify-center text-zinc-400">
                        <p className="text-sm">Select an item</p>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex flex-1 min-h-0">
        {/* History Sidebar */}
        <AnimatePresence initial={false}>
          {showHistory && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 180, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/30 dark:bg-zinc-900/30 flex flex-col overflow-hidden"
            >
              <div className="px-2 py-1.5 text-xs font-medium text-zinc-500 border-b border-zinc-200 dark:border-zinc-800">
                History
              </div>
              <div className="flex-1 overflow-y-auto">
                {dialogs.length === 0 ? (
                  <div className="text-xs text-zinc-400 text-center py-4">No chats</div>
                ) : (
                  dialogs.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => {
                        setDialogId(d.id);
                        setCurrentDialog(d);
                        if (isConnected) subscribeToDialog(d.id);
                      }}
                      className={cn(
                        "w-full text-left px-2 py-1.5 text-xs transition-colors",
                        currentDialog?.id === d.id
                          ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                          : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600",
                      )}
                    >
                      <div className="font-medium truncate">{d.title}</div>
                      <div className="text-[10px] opacity-60">{d.messages.length} msgs</div>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Messages Area */}
        <div className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-zinc-400">
                <MessageSquare className="h-10 w-10 mb-2 opacity-20" />
                <p className="text-sm">Start a conversation...</p>
              </div>
            ) : (
              renderItems
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
                      streamingContent={isMessageStreaming ? streamingContent : undefined}
                      streamingReasoning={isMessageStreaming ? streamingReasoning : undefined}
                      defaultExpanded={
                        message.role === "assistant" &&
                        message.tool_calls &&
                        message.tool_calls.length > 0 &&
                        index === messages.length - 1
                      }
                    />
                  );
                })
            )}
          </div>

          {/* Input */}
          <div className="p-2 border-t border-zinc-200 dark:border-zinc-800">
            {sendError && <div className="mb-1 text-xs text-red-500">{sendError}</div>}
            <div className="flex items-end gap-1.5">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message..."
                className="flex-1 resize-none rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                rows={1}
                style={{ minHeight: "36px", maxHeight: "120px" }}
              />
              <button
                onClick={handleSend}
                disabled={!inputValue.trim() || isSending}
                className="flex items-center justify-center w-9 h-9 rounded-md bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

      {/* Todo Panel - Fixed top area with scroll */}
      <AnimatePresence>
        {rightPanelTab === "todo" && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 140, opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="shrink-0 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 overflow-hidden"
          >
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-3 py-1.5 border-b border-zinc-200/60 dark:border-zinc-700/60">
                <span className="text-xs font-medium text-zinc-500">Tasks</span>
                <button
                  onClick={() => setRightPanelTab("none")}
                  className="text-zinc-400 hover:text-zinc-600 text-xs w-5 h-5 flex items-center justify-center rounded hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50"
                >
                  ✕
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                <TodoPanel isOpen={true} onClose={() => setRightPanelTab("none")} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      </div>
    </div>
  );
}
