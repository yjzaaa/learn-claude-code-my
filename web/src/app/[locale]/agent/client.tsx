"use client";

import { useState } from "react";
import { useMessageStore } from "@/hooks/useMessageStore";
import { EmbeddedDialog } from "@/components/realtime";
import { StudioDesignDemo } from "@/components/realtime/studio-design-demo";
import { cn } from "@/lib/utils";

/**
 * Agent 实时对话页面客户端组件
 *
 * 功能：
 * - 提供与 AI Agent 的实时交互界面
 * - 展示嵌入式对话组件（EmbeddedDialog）
 */
export function AgentPageClient() {
  const { messages } = useMessageStore();
  const [activeView, setActiveView] = useState<"chat" | "studio">("chat");

  return (
    <div className="mx-auto h-[calc(100vh-100px)] max-w-6xl px-4 py-4 sm:px-6 lg:px-8">
      <div className="relative h-full overflow-hidden rounded-3xl border border-[#d7deea] bg-[radial-gradient(circle_at_top_left,_#f0f9ff_0%,_#f8fafc_44%,_#ecfeff_100%)] p-3 shadow-[0_18px_60px_-30px_rgba(2,132,199,0.55)] md:p-4">
        <div className="pointer-events-none absolute -left-8 -top-16 h-44 w-44 rounded-full bg-[#7dd3fc]/30 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 right-0 h-56 w-56 rounded-full bg-[#a7f3d0]/25 blur-3xl" />

        <div className="relative mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#d7deea] bg-white/85 p-2 backdrop-blur-sm">
          <div className="px-2">
            <p className="text-[11px] uppercase tracking-[0.16em] text-[#6b7280]">
              Agent Workspace
            </p>
            <p className="text-sm text-[#334155]">
              在实时对话与结构演示之间切换
            </p>
          </div>

          <div className="flex items-center gap-1.5 rounded-xl border border-[#d7deea] bg-white p-1">
            <button
              type="button"
              onClick={() => setActiveView("chat")}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                activeView === "chat"
                  ? "bg-[#0f172a] text-white"
                  : "text-[#475569] hover:bg-[#f1f5f9]",
              )}
            >
              实时对话
            </button>
            <button
              type="button"
              onClick={() => setActiveView("studio")}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                activeView === "studio"
                  ? "bg-[#0f172a] text-white"
                  : "text-[#475569] hover:bg-[#f1f5f9]",
              )}
            >
              结构演示
            </button>
          </div>
        </div>

        <div className="relative h-[calc(100%-88px)] md:h-[calc(100%-84px)]">
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
    </div>
  );
}
