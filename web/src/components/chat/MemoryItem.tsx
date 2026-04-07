"use client";

import { useState } from "react";
import { MemoryTypeBadge } from "./MemoryTypeBadge";
import { Edit2, Trash2 } from "lucide-react";
import type { Memory } from "@/hooks/useMemory";

export type { Memory };

export interface MemoryItemProps {
  memory: Memory;
  onEdit?: (memory: Memory) => void;
  onDelete?: (memoryId: string) => void;
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays === 0) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  if (diffDays === 1) return "昨天";
  if (diffDays < 7) return `${diffDays}天前`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function MemoryItem({ memory, onEdit, onDelete }: MemoryItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(memory);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(memory.id);
  };

  return (
    <div
      style={{
        borderBottom: "1px solid var(--border)",
        background: isHovered ? "var(--overlay-subtle)" : "transparent",
        transition: "background var(--duration) var(--ease-out)",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: "100%",
          textAlign: "left",
          padding: "12px 14px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
        }}
      >
        {/* Top row: name and actions */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "8px",
          }}
        >
          <span
            style={{
              fontSize: "13px",
              fontWeight: 500,
              color: "var(--text)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              flex: 1,
            }}
          >
            {memory.name}
          </span>

          {/* Action buttons - visible on hover */}
          {isHovered && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "2px",
                flexShrink: 0,
              }}
            >
              <ActionButton onClick={handleEdit} title="编辑">
                <Edit2 size={12} />
              </ActionButton>
              <ActionButton onClick={handleDelete} title="删除">
                <Trash2 size={12} />
              </ActionButton>
            </div>
          )}
        </div>

        {/* Bottom row: type badge and time */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "8px",
          }}
        >
          <MemoryTypeBadge type={memory.type} />
          <span
            style={{
              fontSize: "11px",
              color: "var(--text-muted)",
              fontFamily: "var(--font-ui)",
            }}
          >
            {formatTime(memory.updated_at)}
          </span>
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div
          style={{
            padding: "0 14px 14px",
            animation: "slideDown var(--duration) var(--ease-out)",
          }}
        >
          {/* Description */}
          {memory.description && (
            <p
              style={{
                fontSize: "12px",
                color: "var(--text-light)",
                marginBottom: "8px",
                lineHeight: 1.5,
              }}
            >
              {memory.description}
            </p>
          )}

          {/* Content preview */}
          <div
            style={{
              padding: "10px 12px",
              background: "var(--bg-card)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--overlay-light)",
              fontSize: "12px",
              lineHeight: 1.6,
              color: "var(--text-light)",
              maxHeight: "200px",
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {memory.content}
          </div>
        </div>
      )}
    </div>
  );
}

interface ActionButtonProps {
  children: React.ReactNode;
  onClick: (e: React.MouseEvent) => void;
  title: string;
}

function ActionButton({ children, onClick, title }: ActionButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      onClick={onClick}
      title={title}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          onClick(e as unknown as React.MouseEvent);
        }
      }}
      style={{
        width: "24px",
        height: "24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "var(--radius-sm)",
        border: "none",
        background: isHovered ? "var(--overlay-medium)" : "transparent",
        color: isHovered ? "var(--text)" : "var(--text-muted)",
        cursor: "pointer",
        transition: "all var(--duration) var(--ease-out)",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {children}
    </div>
  );
}
