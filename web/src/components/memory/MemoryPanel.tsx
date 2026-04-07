"use client";

import { useState, useEffect } from "react";
import { Brain, X, User, MessageSquare, FolderOpen, BookOpen } from "lucide-react";
import { memoryManager, type Memory } from "@/services/memory/client_memory_manager";
import { syncManager } from "@/services/memory/sync_manager";

interface MemoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const typeIcons = {
  user: User,
  feedback: MessageSquare,
  project: FolderOpen,
  reference: BookOpen,
};

const typeLabels = {
  user: "用户",
  feedback: "反馈",
  project: "项目",
  reference: "参考",
};

const typeColors = {
  user: "#4CAF50",
  feedback: "#FF9800",
  project: "#2196F3",
  reference: "#9C27B0",
};

export function MemoryPanel({ isOpen, onClose }: MemoryPanelProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedType, setSelectedType] = useState<Memory["type"] | "all">("all");
  const [syncStatus, setSyncStatus] = useState<{ queueLength: number; isOnline: boolean }>({
    queueLength: 0,
    isOnline: true,
  });

  useEffect(() => {
    if (isOpen) {
      loadMemories();
      updateSyncStatus();
    }
  }, [isOpen]);

  const loadMemories = async () => {
    try {
      setIsLoading(true);
      await memoryManager.init();
      const recentMemories = await memoryManager.getRecentMemories(20);
      setMemories(recentMemories);
    } catch (error) {
      console.error("[MemoryPanel] Failed to load memories:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateSyncStatus = () => {
    setSyncStatus({
      queueLength: syncManager.getQueueLength(),
      isOnline: syncManager.getNetworkStatus(),
    });
  };

  const filteredMemories =
    selectedType === "all" ? memories : memories.filter((m) => m.type === selectedType);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        width: 280,
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
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Brain size={14} style={{ color: "var(--accent)" }} />
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text)",
              letterSpacing: "0.02em",
            }}
          >
            记忆
          </span>
        </div>
        <button
          onClick={onClose}
          title="关闭"
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
          <X size={14} />
        </button>
      </div>

      {/* Sync Status */}
      <div
        style={{
          padding: "var(--space-sm) var(--space-md)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: 11,
          color: "var(--text-muted)",
        }}
      >
        <span>{syncStatus.isOnline ? "在线" : "离线"}</span>
        {syncStatus.queueLength > 0 && <span>待同步: {syncStatus.queueLength}</span>}
      </div>

      {/* Type Filter */}
      <div
        style={{
          padding: "var(--space-sm) var(--space-md)",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          gap: 4,
          flexWrap: "wrap",
        }}
      >
        {(["all", "user", "feedback", "project", "reference"] as const).map((type) => (
          <button
            key={type}
            onClick={() => setSelectedType(type)}
            style={{
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              background: selectedType === type ? "var(--accent-light)" : "transparent",
              color: selectedType === type ? "var(--accent)" : "var(--text-light)",
              fontSize: 11,
              cursor: "pointer",
              transition: `background var(--duration) var(--ease-out)`,
            }}
          >
            {type === "all" ? "全部" : typeLabels[type]}
          </button>
        ))}
      </div>

      {/* Memory List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-sm) 0" }}>
        {isLoading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 100,
              color: "var(--text-muted)",
              fontSize: 12,
            }}
          >
            加载中...
          </div>
        ) : filteredMemories.length === 0 ? (
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
            <Brain size={24} opacity={0.3} />
            <span style={{ fontSize: 12 }}>暂无记忆</span>
          </div>
        ) : (
          filteredMemories.map((memory) => {
            const Icon = typeIcons[memory.type];
            return (
              <div
                key={memory.id}
                style={{
                  padding: "var(--space-sm) var(--space-md)",
                  borderBottom: "1px solid var(--border-subtle)",
                  cursor: "pointer",
                  transition: `background var(--duration) var(--ease-out)`,
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "var(--overlay-medium)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 4,
                  }}
                >
                  <Icon size={12} style={{ color: typeColors[memory.type] }} />
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 500,
                      color: "var(--text)",
                      flex: 1,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={memory.name}
                  >
                    {memory.name}
                  </span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                    {formatTime(memory.updated_at)}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--text-light)",
                    lineHeight: 1.4,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {memory.description}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
