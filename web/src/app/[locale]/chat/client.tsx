"use client";

import "@/styles/globals.css";
import "@/styles/themes/index.css";
import { MessageStoreProvider } from "@/hooks/useMessageStore";
import { ChatShell } from "@/components/chat/ChatShell";

export function ChatPageClient() {
  return (
    <MessageStoreProvider>
      <ChatShell />
    </MessageStoreProvider>
  );
}
