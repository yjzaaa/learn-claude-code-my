"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { DialogSession, Message, ToolCall } from "@/types/dialog";
import {
  Send,
  Plus,
  Square,
  Bot,
  User,
  MessageSquare,
  Loader2,
  CheckCircle2,
  Wrench,
  ChevronDown,
} from "lucide-react";

// ========== 子组件 ==========

/** 侧边栏 - 历史对话列表 */
function Sidebar({
  dialogs,
  currentId,
  onSelect,
  onNew,
}: {
  dialogs: { id: string; title: string; message_count: number; updated_at: string }[];
  currentId?: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  return (
    <div className="w-48 border-r border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/50 flex flex-col">
      <div className="p-3 border-b border-zinc-200 dark:border-zinc-700">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-1 px-3 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 transition-colors"
        >
          <Plus className="h-4 w-4" />
          新建对话
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {dialogs.length === 0 ? (
          <div className="text-xs text-zinc-400 text-center py-4">暂无对话</div>
        ) : (
          dialogs.map((dialog) => (
            <button
              key={dialog.id}
              onClick={() => onSelect(dialog.id)}
              className={cn(
                "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                currentId === dialog.id
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                  : "hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
              )}
            >
              <div className="font-medium truncate">{dialog.title}</div>
              <div className="text-[10px] opacity-70">
                {dialog.message_count} 条消息
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

/** 状态栏 */
function StatusBar({
  status,
  agentName,
  isConnected,
  onStop,
}: {
  status?: string;
  agentName?: string;
  isConnected: boolean;
  onStop: () => void;
}) {
  const isStreaming = status === "thinking" || status === "tool_calling";

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/50">
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "w-2 h-2 rounded-full",
            isConnected ? "bg-green-500" : "bg-red-500"
          )}
        />
        <span className="font-medium text-sm">
          {agentName || "Agent"}
        </span>
        {status && (
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded-full",
              status === "completed" && "bg-green-100 text-green-700",
              status === "thinking" && "bg-blue-100 text-blue-700 animate-pulse",
              status === "tool_calling" && "bg-purple-100 text-purple-700",
              status === "error" && "bg-red-100 text-red-700",
              status === "idle" && "bg-zinc-100 text-zinc-600"
            )}
          >
            {status === "thinking" && "思考中..."}
            {status === "tool_calling" && "工具调用..."}
            {status === "completed" && "已完成"}
            {status === "error" && "错误"}
            {status === "idle" && "空闲"}
          </span>
        )}
      </div>
      {isStreaming && (
        <button
          onClick={onStop}
          className="flex items-center gap-1 px-3 py-1.5 bg-red-100 text-red-700 rounded-md text-xs hover:bg-red-200 transition-colors"
        >
          <Square className="h-3 w-3 fill-current" />
          停止
        </button>
      )}
    </div>
  );
}

/** 用户消息 */
function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-white shrink-0">
        <User className="h-4 w-4" />
      </div>
      <div className="flex-1 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
        <p className="text-sm whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}

/** 工具调用项 */
function ToolCallItem({ tool }: { tool: ToolCall }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 bg-zinc-50 dark:bg-zinc-900/50 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          {tool.status === "completed" ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : tool.status === "running" ? (
            <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
          ) : (
            <Wrench className="h-4 w-4 text-zinc-400" />
          )}
          <span className="text-sm font-medium">{tool.name}</span>
          <span
            className={cn(
              "text-xs px-1.5 py-0.5 rounded",
              tool.status === "completed" && "bg-green-100 text-green-700",
              tool.status === "running" && "bg-blue-100 text-blue-700",
              tool.status === "pending" && "bg-zinc-100 text-zinc-600"
            )}
          >
            {tool.status === "completed" && "完成"}
            {tool.status === "running" && "执行中"}
            {tool.status === "pending" && "等待中"}
          </span>
        </div>
        <ChevronDown
          className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")}
        />
      </button>
      {isOpen && (
        <div className="p-3 space-y-2">
          <div>
            <div className="text-xs text-zinc-500 mb-1">参数</div>
            <pre className="text-xs bg-zinc-100 dark:bg-zinc-800 p-2 rounded overflow-auto max-h-32">
              {JSON.stringify(tool.arguments, null, 2)}
            </pre>
          </div>
          {tool.result && (
            <div>
              <div className="text-xs text-zinc-500 mb-1">结果</div>
              <pre className="text-xs bg-green-50 dark:bg-green-900/20 p-2 rounded overflow-auto max-h-40">
                {tool.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** 助手消息 */
function AssistantMessage({
  message,
  isStreaming,
}: {
  message: Message;
  isStreaming?: boolean;
}) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-zinc-700 to-zinc-600 flex items-center justify-center text-white shrink-0">
        <Bot className="h-4 w-4" />
      </div>
      <div className="flex-1 space-y-3">
        {/* 推理内容 */}
        {message.reasoning_content && (
          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <Loader2 className="h-3 w-3 text-purple-500" />
              <span className="text-xs font-medium text-purple-700 dark:text-purple-300">
                思考过程
              </span>
            </div>
            <pre className="text-sm text-purple-800 dark:text-purple-200 whitespace-pre-wrap">
              {message.reasoning_content}
            </pre>
          </div>
        )}

        {/* 正文内容 */}
        {message.content && (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg p-3">
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            {isStreaming && (
              <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse" />
            )}
          </div>
        )}

        {/* 工具调用 */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-zinc-500 flex items-center gap-1">
              <Wrench className="h-3 w-3" />
              工具调用 ({message.tool_calls.length})
            </div>
            {message.tool_calls.map((tool) => (
              <ToolCallItem key={tool.id} tool={tool} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** 消息列表 */
function MessageList({
  messages,
  streamingMessage,
  isStreaming,
}: {
  messages: Message[];
  streamingMessage: Message | null;
  isStreaming: boolean;
}) {
  const allMessages = useMemo(() => {
    const list = [...messages];
    if (streamingMessage) {
      list.push(streamingMessage);
    }
    return list;
  }, [messages, streamingMessage]);

  return (
    <div className="space-y-4 p-4">
      {allMessages.map((msg, index) => {
        const isLast = index === allMessages.length - 1;
        const isStreamingThis = isStreaming && isLast;

        if (msg.role === "user") {
          return <UserMessage key={msg.id} content={msg.content} />;
        }

        if (msg.role === "assistant") {
          return (
            <AssistantMessage
              key={msg.id}
              message={msg}
              isStreaming={isStreamingThis}
            />
          );
        }

        if (msg.role === "system") {
          return (
            <div
              key={msg.id}
              className="text-center text-xs text-zinc-400 py-2"
            >
              {msg.content}
            </div>
          );
        }

        return null;
      })}
    </div>
  );
}

/** 输入区域 */
function InputArea({
  value,
  onChange,
  onSend,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
}) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t border-zinc-200 dark:border-zinc-700 p-4">
      <div className="flex gap-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? "等待响应..." : "输入消息..."}
          className="flex-1 resize-none border border-zinc-200 dark:border-zinc-700 rounded-lg p-3 min-h-[80px] bg-zinc-50 dark:bg-zinc-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 disabled:opacity-50"
        />
        <button
          onClick={onSend}
          disabled={disabled || !value.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1"
        >
          <Send className="h-4 w-4" />
          发送
        </button>
      </div>
    </div>
  );
}

/** 空状态 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-zinc-400">
      <MessageSquare className="h-16 w-16 mb-4 opacity-30" />
      <p className="text-sm">开始一个新的对话...</p>
    </div>
  );
}

// ========== 主组件 ==========

interface EmbeddedDialogProps {
  className?: string;
}

export function EmbeddedDialog({ className }: EmbeddedDialogProps) {
  const [inputValue, setInputValue] = useState("");

  const {
    currentSnapshot,
    dialogList,
    isConnected,
    subscribeToDialog,
    sendUserInput,
    stopAgent,
    createDialog,
  } = useWebSocket();

  // 发送消息 - 创建新对话框并发送
  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const content = inputValue.trim();

    // 创建新对话框
    const result = await createDialog("Agent 对话");
    if (!result.success || !result.data) {
      console.error("[EmbeddedDialog] Failed to create dialog");
      return;
    }

    setInputValue("");

    // 发送用户输入
    sendUserInput(result.data.id, content);
  };

  // 新建对话
  const handleNewDialog = async () => {
    await createDialog("新对话");
  };

  // 切换对话
  const handleSelectDialog = (dialogId: string) => {
    subscribeToDialog(dialogId);
  };

  // 停止 Agent
  const handleStop = () => {
    if (currentSnapshot) {
      stopAgent(currentSnapshot.id);
    }
  };

  return (
    <div
      className={cn(
        "flex h-full rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-sm overflow-hidden",
        className
      )}
    >
      {/* 左侧历史列表 */}
      <Sidebar
        dialogs={dialogList}
        currentId={currentSnapshot?.id}
        onSelect={handleSelectDialog}
        onNew={handleNewDialog}
      />

      {/* 中间聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 状态栏 */}
        <StatusBar
          status={currentSnapshot?.status}
          agentName={currentSnapshot?.metadata.agent_name}
          isConnected={isConnected}
          onStop={handleStop}
        />

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto">
          {currentSnapshot ? (
            <MessageList
              messages={currentSnapshot.messages}
              streamingMessage={currentSnapshot.streaming_message}
              isStreaming={
                currentSnapshot.status === "thinking" ||
                currentSnapshot.status === "tool_calling"
              }
            />
          ) : (
            <EmptyState />
          )}
        </div>

        {/* 输入区域 */}
        <InputArea
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          disabled={
            !currentSnapshot ||
            currentSnapshot.status === "thinking" ||
            currentSnapshot.status === "tool_calling"
          }
        />
      </div>
    </div>
  );
}
