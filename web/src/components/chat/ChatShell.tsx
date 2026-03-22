"use client";

import { useState, useCallback } from "react";
import { useMessageStore, type ChatSession } from "@/hooks/useMessageStore";
import { useAgentApi } from "@/hooks/useAgentApi";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useUIStore } from "@/stores/ui";
import { SessionSidebar } from "./SessionSidebar";
import { ChatArea } from "./ChatArea";

export function ChatShell() {
  const [activeDialogId, setActiveDialogId] = useState<string>("");
  const [newChatError, setNewChatError] = useState<string | null>(null);
  const { resetAndSetDialog } = useMessageStore();
  const { createDialog } = useAgentApi();
  const { isConnected, subscribeToDialog } = useWebSocket();
  const { theme } = useUIStore();

  const handleSelectDialog = useCallback(
    (dialog: ChatSession) => {
      setActiveDialogId(dialog.id);
      resetAndSetDialog(dialog);
      if (isConnected) subscribeToDialog(dialog.id);
    },
    [isConnected, resetAndSetDialog, subscribeToDialog],
  );

  const handleNewChat = useCallback(async () => {
    setNewChatError(null);
    console.log("[ChatShell] handleNewChat called, calling createDialog...");
    try {
      const result = await createDialog();
      console.log("[ChatShell] createDialog result:", result);
      if (result.success && result.data) {
        const d = result.data;
        const dialog: ChatSession = {
          id: d.id,
          title: d.title,
          messages: [],
          created_at: Date.parse(d.created_at) || Date.now(),
          updated_at: Date.parse(d.updated_at) || Date.now(),
        };
        console.log("[ChatShell] Setting dialog:", dialog);
        resetAndSetDialog(dialog);
        setActiveDialogId(d.id);
        if (isConnected) subscribeToDialog(d.id);
      } else {
        const errMsg = result.message || "创建会话失败，请确认后端服务已启动";
        console.error("[ChatShell] createDialog failed:", errMsg);
        setNewChatError(errMsg);
      }
    } catch (e) {
      console.error("[ChatShell] createDialog threw:", e);
      setNewChatError(String(e));
    }
  }, [createDialog, isConnected, resetAndSetDialog, subscribeToDialog]);

  return (
    <div
      data-theme={theme}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        background: "var(--bg)",
        color: "var(--text)",
        fontFamily: "var(--font-ui)",
      }}
    >
      {newChatError && (
        <div
          style={{
            position: "absolute",
            top: 8,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 100,
            background: "#ff4444",
            color: "#fff",
            padding: "8px 16px",
            borderRadius: 6,
            fontSize: 13,
            maxWidth: 480,
            cursor: "pointer",
          }}
          onClick={() => setNewChatError(null)}
        >
          {newChatError}
        </div>
      )}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <SessionSidebar
          activeDialogId={activeDialogId}
          onSelectDialog={handleSelectDialog}
          onNewChat={handleNewChat}
        />

        <ChatArea dialogId={activeDialogId} />
      </div>
    </div>
  );
}
