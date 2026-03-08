"use client";

import { EmbeddedDialog } from "@/components/realtime";

/**
 * Agent 实时对话页面客户端组件
 *
 * 功能：
 * - 提供与 AI Agent 的实时交互界面
 * - 展示嵌入式对话组件（EmbeddedDialog）
 */
export function AgentPageClient() {

  return (
    <div className="h-[calc(100vh-100px)] mx-auto max-w-6xl px-4 py-4 sm:px-6 lg:px-8">
      <EmbeddedDialog className="h-full" />
    </div>
  );
}
