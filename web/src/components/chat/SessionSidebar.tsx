"use client";

import { useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { DialogSummary } from "@/types/dialog";
import { Plus, MessageSquare, Settings } from "lucide-react";

interface SessionSidebarProps {
  dialogs: DialogSummary[];
  activeDialogId: string;
  onSelectDialog: (dialog: DialogSummary) => void;
  onNewChat: () => void;
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (diffDays === 1) return "昨天";
  if (diffDays < 7) return `${diffDays}天前`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function SessionSidebar({ dialogs, activeDialogId, onSelectDialog, onNewChat }: SessionSidebarProps) {
  const params = useParams();
  const locale = (params?.locale as string) || "zh";

  const sorted = [...dialogs].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

  return (
    <div
      style={{
        width: "var(--sidebar-width)",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        background: "var(--sidebar-bg)",
        borderRight: "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          height: "var(--titlebar-height)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 var(--space-md)",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--text)",
            letterSpacing: "0.02em",
          }}
        >
          花子
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "2px" }}>
          <Link
            href={`/${locale}/settings`}
            title="设置"
            style={{
              width: 28,
              height: 28,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "var(--radius-sm)",
              color: "var(--text-light)",
              textDecoration: "none",
              transition: `background var(--duration) var(--ease-out), color var(--duration) var(--ease-out)`,
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = "var(--overlay-medium)";
              (e.currentTarget as HTMLElement).style.color = "var(--text)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
              (e.currentTarget as HTMLElement).style.color = "var(--text-light)";
            }}
          >
            <Settings size={13} />
          </Link>
          <button
            onClick={onNewChat}
            title="新建对话"
            style={{
              width: 28,
              height: 28,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "var(--radius-sm)",
              border: "none",
              background: "transparent",
              color: "var(--text-light)",
              cursor: "pointer",
              transition: `background var(--duration) var(--ease-out), color var(--duration) var(--ease-out)`,
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "var(--overlay-medium)";
              (e.currentTarget as HTMLButtonElement).style.color = "var(--text)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              (e.currentTarget as HTMLButtonElement).style.color = "var(--text-light)";
            }}
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      {/* Session list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-sm) 0" }}>
        {sorted.length === 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "var(--space-xl) var(--space-md)",
              gap: "var(--space-sm)",
              color: "var(--text-muted)",
            }}
          >
            <MessageSquare size={24} opacity={0.3} />
            <span style={{ fontSize: 12 }}>暂无对话</span>
          </div>
        ) : (
          sorted.map((dialog) => (
            <SessionItem
              key={dialog.id}
              dialog={dialog}
              isActive={dialog.id === activeDialogId}
              onSelect={onSelectDialog}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface SessionItemProps {
  dialog: DialogSummary;
  isActive: boolean;
  onSelect: (dialog: DialogSummary) => void;
}

function SessionItem({ dialog, isActive, onSelect }: SessionItemProps) {
  const handleClick = useCallback(() => onSelect(dialog), [dialog, onSelect]);

  return (
    <button
      onClick={handleClick}
      style={{
        width: "100%",
        textAlign: "left",
        padding: "var(--space-sm) var(--space-md)",
        background: isActive ? "var(--accent-light)" : "transparent",
        borderLeft: isActive ? `2px solid var(--accent)` : "2px solid transparent",
        border: "none",
        cursor: "pointer",
        color: isActive ? "var(--text)" : "var(--text-light)",
        transition: `background var(--duration) var(--ease-out)`,
        display: "block",
      }}
      onMouseEnter={(e) => {
        if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = "var(--overlay-medium)";
      }}
      onMouseLeave={(e) => {
        if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = "transparent";
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontWeight: isActive ? 500 : 400,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          marginBottom: 2,
        }}
      >
        {dialog.title || "新对话"}
      </div>
      <div
        style={{
          fontSize: 11,
          color: "var(--text-muted)",
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span>{dialog.message_count} 条</span>
        <span>{formatTime(dialog.updated_at)}</span>
      </div>
    </button>
  );
}
