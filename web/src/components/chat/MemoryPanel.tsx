"use client";

import { useState, useCallback } from "react";
import { MemoryItem } from "./MemoryItem";
import type { Memory } from "@/hooks/useMemory";
import { MemoryStatus } from "./MemoryStatus";
import { RefreshCw, Plus } from "lucide-react";

export interface MemoryPanelProps {
  memories?: Memory[];
  isConnected?: boolean;
  isLoading?: boolean;
  lastUpdated?: Date;
  onRefresh?: () => void;
  onAddMemory?: () => void;
  onEditMemory?: (memory: Memory) => void;
  onDeleteMemory?: (memoryId: string) => void;
}

export function MemoryPanel({
  memories = [],
  isConnected = true,
  isLoading = false,
  lastUpdated,
  onRefresh,
  onAddMemory,
  onEditMemory,
  onDeleteMemory,
}: MemoryPanelProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await onRefresh?.();
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  }, [onRefresh]);

  return (
    <div
      style={{
        width: "280px",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        background: "var(--sidebar-bg)",
        borderLeft: "1px solid var(--border)",
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
          记忆库
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "2px" }}>
          <HeaderButton
            onClick={handleRefresh}
            title="刷新"
            isSpinning={isRefreshing}
          >
            <RefreshCw size={13} />
          </HeaderButton>
          <HeaderButton onClick={onAddMemory} title="添加记忆">
            <Plus size={14} />
          </HeaderButton>
        </div>
      </div>

      {/* Memory list */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          scrollbarWidth: "thin",
          scrollbarColor: "var(--overlay-medium) transparent",
        }}
        className="scrollbar-thin"
      >
        {isLoading ? (
          <LoadingState />
        ) : memories.length === 0 ? (
          <EmptyState onAdd={onAddMemory} />
        ) : (
          memories.map((memory) => (
            <MemoryItem
              key={memory.id}
              memory={memory}
              onEdit={onEditMemory}
              onDelete={onDeleteMemory}
            />
          ))
        )}
      </div>

      {/* Status bar */}
      <MemoryStatus
        isConnected={isConnected}
        memoryCount={memories.length}
        lastUpdated={lastUpdated}
      />
    </div>
  );
}

interface HeaderButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  title: string;
  isSpinning?: boolean;
}

function HeaderButton({
  children,
  onClick,
  title,
  isSpinning,
}: HeaderButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        width: 28,
        height: 28,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "var(--radius-sm)",
        border: "none",
        background: isHovered ? "var(--overlay-medium)" : "transparent",
        color: isHovered ? "var(--text)" : "var(--text-light)",
        cursor: "pointer",
        transition: `background var(--duration) var(--ease-out), color var(--duration) var(--ease-out)`,
        transform: isSpinning ? "rotate(360deg)" : "rotate(0deg)",
        transitionProperty: "background, color, transform",
        transitionDuration: isSpinning ? "500ms" : "var(--duration)",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {children}
    </button>
  );
}

function LoadingState() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-xl) var(--space-md)",
        gap: "var(--space-sm)",
        color: "var(--text-muted)",
        textAlign: "center",
      }}
    >
      <div
        style={{
          width: 24,
          height: 24,
          border: "2px solid var(--overlay-medium)",
          borderTopColor: "var(--accent)",
          borderRadius: "50%",
          animation: "spin 1s linear infinite",
        }}
      />
      <span style={{ fontSize: 12 }}>加载中...</span>
    </div>
  );
}

interface EmptyStateProps {
  onAdd?: () => void;
}

function EmptyState({ onAdd }: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-xl) var(--space-md)",
        gap: "var(--space-sm)",
        color: "var(--text-muted)",
        textAlign: "center",
      }}
    >
      <svg
        width="32"
        height="32"
        viewBox="0 0 12 12"
        fill="none"
        style={{ opacity: 0.3 }}
      >
        <path
          d="M6 1L1 3.5V8.5L6 11L11 8.5V3.5L6 1Z"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M1 3.5L6 6L11 3.5"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M6 6V11"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div style={{ fontSize: 12 }}>
        <p style={{ margin: "0 0 4px", fontWeight: 500 }}>暂无记忆</p>
        <p style={{ margin: 0, opacity: 0.7 }}>点击 + 添加第一条记忆</p>
      </div>
      {onAdd && (
        <button
          onClick={onAdd}
          style={{
            marginTop: "8px",
            padding: "6px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border)",
            background: "var(--bg-card)",
            color: "var(--text-light)",
            fontSize: "12px",
            cursor: "pointer",
            transition: "all var(--duration) var(--ease-out)",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background =
              "var(--overlay-medium)";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--text)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background =
              "var(--bg-card)";
            (e.currentTarget as HTMLButtonElement).style.color =
              "var(--text-light)";
          }}
        >
          添加记忆
        </button>
      )}
    </div>
  );
}
