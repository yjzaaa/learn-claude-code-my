"use client";

import { useEffect, useRef, useCallback } from "react";
import { MessageSquare } from "lucide-react";
import { useMessageStore } from "@/hooks/useMessageStore";
import { useAgentApi } from "@/hooks/useAgentApi";
import { MessageItem } from "./MessageItem";
import { InputArea, type SendOptions } from "./InputArea";

interface ChatAreaProps {
  dialogId: string;
}

export function ChatArea({ dialogId }: ChatAreaProps) {
  const { messages, isStreaming } = useMessageStore();
  const { sendMessage, stopAgent } = useAgentApi();
  const bottomRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  // Auto-scroll when messages change, only if already near bottom
  useEffect(() => {
    if (isAtBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Track scroll position to decide whether to auto-scroll
  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const threshold = 120;
    isAtBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  }, []);

  const handleSend = useCallback(
    async (content: string, _options: SendOptions) => {
      if (!dialogId) return;
      await sendMessage(dialogId, content);
    },
    [dialogId, sendMessage],
  );

  const handleStop = useCallback(() => {
    stopAgent().catch(console.error);
  }, [stopAgent]);

  const hasDialog = Boolean(dialogId);
  const hasMessages = messages.length > 0;

  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* Empty state — no dialog selected */}
      {!hasDialog && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "var(--space-md)",
            color: "var(--text-muted)",
          }}
        >
          <MessageSquare size={40} opacity={0.2} />
          <span style={{ fontSize: 14 }}>选择或新建一个对话开始</span>
        </div>
      )}

      {/* Message list */}
      {hasDialog && (
        <div
          ref={listRef}
          onScroll={handleScroll}
          style={{
            flex: 1,
            overflowY: "auto",
            paddingTop: "var(--space-md)",
            paddingBottom: "var(--space-md)",
          }}
        >
          {!hasMessages && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                gap: "var(--space-sm)",
                color: "var(--text-muted)",
                padding: "var(--space-xl)",
              }}
            >
              <MessageSquare size={32} opacity={0.2} />
              <span style={{ fontSize: 13 }}>发送第一条消息开始对话</span>
            </div>
          )}

          {messages.map((msg, i) => {
            const isLast = i === messages.length - 1;
            return (
              <MessageItem
                key={msg.id ?? i}
                message={msg}
                isStreaming={isLast && isStreaming}
              />
            );
          })}

          <div ref={bottomRef} />
        </div>
      )}

      {/* Input area — always shown when dialog selected */}
      {hasDialog && (
        <InputArea
          dialogId={dialogId}
          isStreaming={isStreaming}
          onSend={handleSend}
          onStop={handleStop}
        />
      )}
    </div>
  );
}
