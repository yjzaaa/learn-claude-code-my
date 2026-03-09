# 前端纯渲染设计文档

## 1. 架构原则

- **无状态管理**：不维护任何对话状态，所有数据来自后端推送
- **纯渲染组件**：组件只负责根据 props 渲染 UI
- **事件透传**：用户操作通过 WebSocket 直接发送给后端
- **快照驱动**：每次状态更新都基于后端发送的完整快照

## 2. 组件架构

```
EmbeddedDialog (容器)
├── Sidebar (历史对话列表 - 纯展示)
├── ChatArea (聊天区域)
│   ├── MessageList (消息列表)
│   │   ├── UserMessage (用户消息)
│   │   ├── AssistantMessage (助手消息)
│   │   │   ├── ReasoningSection (推理内容)
│   │   │   ├── ContentSection (正文内容)
│   │   │   └── ToolsSection (工具调用)
│   │   └── ToolResult (工具结果 - 嵌在 ToolsSection 中)
│   └── InputArea (输入区域)
└── FlowchartPanel (流程图面板 - 可选)
```

## 3. 状态管理

### 3.1 唯一状态源

```typescript
// hooks/useWebSocket.ts - 唯一的状态来源
export function useWebSocket() {
  // 只存储当前对话框的快照
  const [currentSnapshot, setCurrentSnapshot] = useState<DialogSession | null>(null);

  // 历史列表（只含ID和标题，不含完整消息）
  const [dialogList, setDialogList] = useState<DialogSummary[]>([]);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case "dialog:snapshot":
          // 直接替换整个快照
          setCurrentSnapshot(msg.data);
          // 更新历史列表
          updateDialogList(msg.data);
          break;

        case "stream:delta":
          // 增量更新当前快照中的流式消息
          setCurrentSnapshot((prev) => applyDelta(prev, msg));
          break;

        case "tool_call:update":
          // 更新工具调用状态
          setCurrentSnapshot((prev) => updateToolCall(prev, msg));
          break;

        case "status:change":
          // 状态变更，等待下一个 snapshot 更新
          break;
      }
    };

    return () => ws.close();
  }, []);

  // 只暴露发送事件的方法，不暴露状态修改
  const sendUserInput = useCallback((dialogId: string, content: string) => {
    ws.send(JSON.stringify({
      type: "user:input",
      dialog_id: dialogId,
      content
    }));
  }, []);

  const subscribeDialog = useCallback((dialogId: string) => {
    ws.send(JSON.stringify({
      type: "subscribe",
      dialog_id: dialogId
    }));
  }, []);

  return {
    currentSnapshot,  // 完整的对话框状态
    dialogList,       // 历史列表
    sendUserInput,    // 发送用户输入
    subscribeDialog,  // 订阅对话框
    stopAgent         // 停止 Agent
  };
}
```

### 3.2 无状态组件示例

```typescript
// 消息列表 - 纯渲染
interface MessageListProps {
  messages: Message[];
  streamingMessage: Message | null;
  isStreaming: boolean;
}

export function MessageList({ messages, streamingMessage, isStreaming }: MessageListProps) {
  // 合并已完成的和流式中的消息
  const allMessages = useMemo(() => {
    if (streamingMessage) {
      return [...messages, streamingMessage];
    }
    return messages;
  }, [messages, streamingMessage]);

  return (
    <div className="space-y-4">
      {allMessages.map((msg, index) => (
        <MessageRenderer
          key={msg.id}
          message={msg}
          isStreaming={isStreaming && index === allMessages.length - 1}
        />
      ))}
    </div>
  );
}

// 助手消息 - 纯渲染
interface AssistantMessageProps {
  message: Message;
  isStreaming: boolean;
}

export function AssistantMessage({ message, isStreaming }: AssistantMessageProps) {
  return (
    <div className="assistant-message">
      {/* 推理内容 */}
      {message.reasoning_content && (
        <ReasoningSection content={message.reasoning_content} />
      )}

      {/* 正文内容 */}
      <ContentSection
        content={message.content}
        isStreaming={isStreaming}
      />

      {/* 工具调用 */}
      {message.tool_calls && message.tool_calls.length > 0 && (
        <ToolsSection toolCalls={message.tool_calls} />
      )}
    </div>
  );
}

// 工具区域 - 纯渲染
interface ToolsSectionProps {
  toolCalls: ToolCall[];
}

export function ToolsSection({ toolCalls }: ToolsSectionProps) {
  return (
    <Accordion>
      {toolCalls.map((tool) => (
        <ToolCallItem
          key={tool.id}
          tool={tool}
          isRunning={tool.status === 'running'}
          result={tool.result}
        />
      ))}
    </Accordion>
  );
}
```

## 4. 数据结构定义

```typescript
// types/dialog.ts

export interface DialogSession {
  id: string;
  title: string;
  status: DialogStatus;
  messages: Message[];
  streaming_message: Message | null;
  metadata: DialogMetadata;
  created_at: string;
  updated_at: string;
}

export type DialogStatus =
  | "idle"
  | "thinking"
  | "tool_calling"
  | "completed"
  | "error";

export interface DialogMetadata {
  model: string;
  agent_name: string;
  tool_calls_count: number;
  total_tokens: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  content_type: "text" | "markdown" | "json";

  // Assistant only
  tool_calls?: ToolCall[];
  reasoning_content?: string;
  agent_name?: string;

  // Tool only
  tool_call_id?: string;
  tool_name?: string;

  status: "pending" | "streaming" | "completed" | "error";
  timestamp: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "error";
  result?: string;
  started_at?: string;
  completed_at?: string;
}

export interface DialogSummary {
  id: string;
  title: string;
  message_count: number;
  updated_at: string;
}

// WebSocket 事件类型
export interface DialogSnapshotEvent {
  type: "dialog:snapshot";
  dialog_id: string;
  data: DialogSession;
  timestamp: number;
}

export interface StreamDeltaEvent {
  type: "stream:delta";
  dialog_id: string;
  message_id: string;
  delta: {
    content?: string;
    reasoning?: string;
  };
  timestamp: number;
}

export interface ToolCallUpdateEvent {
  type: "tool_call:update";
  dialog_id: string;
  tool_call: ToolCall;
  timestamp: number;
}

export interface StatusChangeEvent {
  type: "status:change";
  dialog_id: string;
  from: DialogStatus;
  to: DialogStatus;
  timestamp: number;
}
```

## 5. 主组件实现

```typescript
// components/realtime/EmbeddedDialog.tsx

"use client";

import { useState, useCallback } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Sidebar } from "./Sidebar";
import { MessageList } from "./MessageList";
import { InputArea } from "./InputArea";
import { StatusBar } from "./StatusBar";

interface EmbeddedDialogProps {
  className?: string;
}

export function EmbeddedDialog({ className }: EmbeddedDialogProps) {
  const [inputValue, setInputValue] = useState("");

  const {
    currentSnapshot,
    dialogList,
    sendUserInput,
    subscribeDialog,
    stopAgent,
    isConnected
  } = useWebSocket();

  // 发送消息 - 直接透传给后端
  const handleSend = useCallback(() => {
    if (!inputValue.trim() || !currentSnapshot) return;

    sendUserInput(currentSnapshot.id, inputValue.trim());
    setInputValue("");
  }, [inputValue, currentSnapshot, sendUserInput]);

  // 新建对话
  const handleNewDialog = useCallback(async () => {
    // 调用 REST API 创建新对话框
    const response = await fetch("/api/dialogs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "新对话" })
    });
    const result = await response.json();

    if (result.success) {
      // 订阅新对话框
      subscribeDialog(result.data.id);
    }
  }, [subscribeDialog]);

  // 切换历史对话
  const handleSelectDialog = useCallback((dialogId: string) => {
    subscribeDialog(dialogId);
  }, [subscribeDialog]);

  // 停止 Agent
  const handleStop = useCallback(() => {
    if (currentSnapshot) {
      stopAgent(currentSnapshot.id);
    }
  }, [currentSnapshot, stopAgent]);

  return (
    <div className={cn("flex h-full", className)}>
      {/* 左侧历史列表 */}
      <Sidebar
        dialogs={dialogList}
        currentId={currentSnapshot?.id}
        onSelect={handleSelectDialog}
        onNew={handleNewDialog}
      />

      {/* 中间聊天区域 */}
      <div className="flex-1 flex flex-col">
        {/* 状态栏 */}
        <StatusBar
          status={currentSnapshot?.status}
          agentName={currentSnapshot?.metadata.agent_name}
          isConnected={isConnected}
          onStop={handleStop}
        />

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          {currentSnapshot ? (
            <MessageList
              messages={currentSnapshot.messages}
              streamingMessage={currentSnapshot.streaming_message}
              isStreaming={currentSnapshot.status === "thinking"}
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
          disabled={!currentSnapshot || currentSnapshot.status === "thinking"}
        />
      </div>
    </div>
  );
}
```

## 6. 增量更新处理

```typescript
// utils/snapshot-helpers.ts

import { DialogSession, StreamDeltaEvent, ToolCallUpdateEvent } from "@/types/dialog";

/**
 * 应用流式增量到快照
 */
export function applyDelta(
  snapshot: DialogSession | null,
  event: StreamDeltaEvent
): DialogSession | null {
  if (!snapshot || !snapshot.streaming_message) return snapshot;

  const { delta } = event;
  const streaming = snapshot.streaming_message;

  return {
    ...snapshot,
    streaming_message: {
      ...streaming,
      content: streaming.content + (delta.content || ""),
      reasoning_content: streaming.reasoning_content + (delta.reasoning || "")
    }
  };
}

/**
 * 更新工具调用状态
 */
export function updateToolCall(
  snapshot: DialogSession | null,
  event: ToolCallUpdateEvent
): DialogSession | null {
  if (!snapshot || !snapshot.streaming_message?.tool_calls) return snapshot;

  const { tool_call } = event;
  const streaming = snapshot.streaming_message;

  return {
    ...snapshot,
    streaming_message: {
      ...streaming,
      tool_calls: streaming.tool_calls.map((t) =>
        t.id === tool_call.id ? tool_call : t
      )
    }
  };
}
```

## 7. 组件详细设计

### 7.1 Sidebar (历史列表)

```typescript
interface SidebarProps {
  dialogs: DialogSummary[];
  currentId?: string;
  onSelect: (dialogId: string) => void;
  onNew: () => void;
}

export function Sidebar({ dialogs, currentId, onSelect, onNew }: SidebarProps) {
  return (
    <div className="w-48 border-r bg-gray-50 flex flex-col">
      <div className="p-2 border-b">
        <button
          onClick={onNew}
          className="w-full px-3 py-2 bg-blue-500 text-white rounded"
        >
          新建对话
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {dialogs.map((dialog) => (
          <button
            key={dialog.id}
            onClick={() => onSelect(dialog.id)}
            className={cn(
              "w-full px-3 py-2 text-left text-sm",
              currentId === dialog.id && "bg-blue-100"
            )}
          >
            <div className="truncate">{dialog.title}</div>
            <div className="text-xs text-gray-500">
              {dialog.message_count} 条消息
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

### 7.2 MessageList (消息列表)

```typescript
interface MessageListProps {
  messages: Message[];
  streamingMessage: Message | null;
  isStreaming: boolean;
}

export function MessageList({ messages, streamingMessage, isStreaming }: MessageListProps) {
  const allMessages = useMemo(() => {
    const list = [...messages];
    if (streamingMessage) {
      list.push(streamingMessage);
    }
    return list;
  }, [messages, streamingMessage]);

  return (
    <div className="space-y-4">
      {allMessages.map((msg, index) => {
        const isLast = index === allMessages.length - 1;
        const isStreamingThis = isStreaming && isLast;

        switch (msg.role) {
          case "user":
            return <UserMessage key={msg.id} content={msg.content} />;

          case "assistant":
            return (
              <AssistantMessage
                key={msg.id}
                message={msg}
                isStreaming={isStreamingThis}
              />
            );

          case "system":
            return <SystemMessage key={msg.id} content={msg.content} />;

          default:
            return null;
        }
      })}
    </div>
  );
}
```

### 7.3 AssistantMessage (助手消息)

```typescript
interface AssistantMessageProps {
  message: Message;
  isStreaming: boolean;
}

export function AssistantMessage({ message, isStreaming }: AssistantMessageProps) {
  return (
    <div className="assistant-message">
      {/* 头部 */}
      <div className="flex items-center gap-2 mb-2">
        <AgentAvatar name={message.agent_name} />
        <span className="font-medium">{message.agent_name}</span>
        {isStreaming && <StreamingIndicator />}
      </div>

      {/* 推理内容（可折叠） */}
      {message.reasoning_content && (
        <Collapsible title="思考过程" className="bg-purple-50">
          <pre className="text-sm whitespace-pre-wrap">
            {message.reasoning_content}
          </pre>
        </Collapsible>
      )}

      {/* 正文 */}
      <div className="prose">
        <Markdown content={message.content} />
        {isStreaming && <Cursor />}
      </div>

      {/* 工具调用 */}
      {message.tool_calls && message.tool_calls.length > 0 && (
        <ToolsSection toolCalls={message.tool_calls} />
      )}
    </div>
  );
}
```

### 7.4 ToolsSection (工具调用区域)

```typescript
interface ToolsSectionProps {
  toolCalls: ToolCall[];
}

export function ToolsSection({ toolCalls }: ToolsSectionProps) {
  return (
    <Accordion type="multiple" className="mt-4">
      {toolCalls.map((tool) => (
        <AccordionItem key={tool.id} value={tool.id}>
          <AccordionTrigger>
            <div className="flex items-center gap-2">
              <ToolStatusIcon status={tool.status} />
              <span>{tool.name}</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            {/* 参数 */}
            <div className="mb-2">
              <div className="text-xs text-gray-500 mb-1">参数</div>
              <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto">
                {JSON.stringify(tool.arguments, null, 2)}
              </pre>
            </div>

            {/* 结果 */}
            {tool.result && (
              <div>
                <div className="text-xs text-gray-500 mb-1">结果</div>
                <pre className="text-xs bg-green-50 p-2 rounded overflow-auto max-h-40">
                  {tool.result}
                </pre>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
```

### 7.5 InputArea (输入区域)

```typescript
interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

export function InputArea({ value, onChange, onSend, disabled }: InputAreaProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t p-4">
      <div className="flex gap-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? "等待响应..." : "输入消息..."}
          className="flex-1 resize-none border rounded-lg p-2 min-h-[80px]"
        />
        <button
          onClick={onSend}
          disabled={disabled || !value.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
        >
          发送
        </button>
      </div>
    </div>
  );
}
```

## 8. 状态流转示例

### 8.1 正常对话流程

```
初始状态:
  currentSnapshot = null

用户创建对话框:
  - 点击"新建对话"
  - 调用 POST /api/dialogs
  - 返回 DialogSession
  - 发送 WebSocket subscribe 事件
  - 后端推送 dialog:snapshot
  - currentSnapshot = { id, status: "idle", messages: [] }

用户发送消息:
  - 输入"你好"
  - 点击发送
  - WebSocket 发送 { type: "user:input", content: "你好" }
  - 后端处理，推送 dialog:snapshot
  - currentSnapshot = {
      status: "thinking",
      messages: [{ role: "user", content: "你好" }],
      streaming_message: { role: "assistant", content: "", status: "streaming" }
    }

Agent 流式输出:
  - 后端推送 stream:delta { content: "你" }
  - currentSnapshot.streaming_message.content += "你"
  - 后端推送 stream:delta { content: "好" }
  - currentSnapshot.streaming_message.content += "好"
  - ...

Agent 完成:
  - 后端推送 dialog:snapshot
  - currentSnapshot = {
      status: "completed",
      messages: [
        { role: "user", content: "你好" },
        { role: "assistant", content: "你好！", status: "completed" }
      ],
      streaming_message: null
    }
```

### 8.2 工具调用流程

```
Agent 调用工具:
  - 后端推送 dialog:snapshot
  - currentSnapshot = {
      status: "tool_calling",
      streaming_message: {
        role: "assistant",
        content: "我来查询一下",
        tool_calls: [
          { id: "call_1", name: "search", arguments: {...}, status: "pending" }
        ]
      }
    }

工具开始执行:
  - 后端推送 tool_call:update
  - currentSnapshot.streaming_message.tool_calls[0].status = "running"

工具执行完成:
  - 后端推送 tool_call:update
  - currentSnapshot.streaming_message.tool_calls[0].status = "completed"
  - currentSnapshot.streaming_message.tool_calls[0].result = "..."
  - currentSnapshot.messages 新增 tool 消息

Agent 继续输出:
  - 后端推送 stream:delta
  - currentSnapshot.streaming_message.content += "..."
```

## 9. 优势

1. **逻辑简单**：前端无状态管理，只接收数据渲染
2. **实时同步**：WebSocket 推送保证前后端状态一致
3. **易测试**：组件纯函数，输入确定输出就确定
4. **易维护**：状态逻辑全部在后端，前端只改样式
5. **支持离线恢复**：刷新页面后接收 snapshot 即可恢复
6. **支持多端同步**：同一账号多端可同时看到相同状态

## 10. 注意事项

1. **快照大小**：如果消息很多，snapshot 会很大，需要考虑分页加载
2. **增量更新**：stream:delta 减少不必要的全量传输
3. **错误处理**：后端推送 error 事件，前端显示错误提示
4. **重连机制**：WebSocket 断开后自动重连并重新订阅
