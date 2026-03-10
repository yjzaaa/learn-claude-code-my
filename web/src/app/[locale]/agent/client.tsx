"use client";

import { useState } from "react";
import { MessageStoreProvider, useMessageStore } from "@/hooks/useMessageStore";
import { EmbeddedDialog } from "@/components/realtime";
import { StudioDesignDemo } from "@/components/realtime/studio-design-demo";
import { cn } from "@/lib/utils";

export function AgentPageClient() {
  return (
    <MessageStoreProvider>
      <AgentPageClientContent />
    </MessageStoreProvider>
  );
}

function AgentPageClientContent() {
  const { messages } = useMessageStore();
  const [activeView, setActiveView] = useState<"chat" | "studio">("chat");

  return (
    <div className="h-full flex flex-col bg-zinc-50 dark:bg-zinc-950">
      {/* Compact toolbar - VS Code style */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-100 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Agent
          </span>
          <span className="text-zinc-300 dark:text-zinc-700">/</span>
          <span className="text-xs text-zinc-500 dark:text-zinc-500">
            {activeView === "chat" ? "Chat" : "Studio"}
          </span>
        </div>

        <div className="flex items-center gap-0.5 bg-zinc-200/50 dark:bg-zinc-800/50 rounded p-0.5">
          <button
            type="button"
            onClick={() => setActiveView("chat")}
            className={cn(
              "px-2.5 py-0.5 text-xs font-medium transition-colors rounded",
              activeView === "chat"
                ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
            )}
          >
            Chat
          </button>
          <button
            type="button"
            onClick={() => setActiveView("studio")}
            className={cn(
              "px-2.5 py-0.5 text-xs font-medium transition-colors rounded",
              activeView === "studio"
                ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
            )}
          >
            Studio
          </button>
        </div>
      </div>

      {/* Content fills remaining space */}
      <div className="flex-1 min-h-0">
        {activeView === "chat" ? (
          <EmbeddedDialog className="h-full" />
        ) : (
          <StudioDesignDemo
            className="h-full overflow-y-auto"
            messages={messages.length > 0 ? messages : undefined}
          />
        )}
      </div>
    </div>
  );
}
