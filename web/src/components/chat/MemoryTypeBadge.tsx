"use client";

import { useState } from "react";

type MemoryType = "user" | "feedback" | "project" | "reference";

interface MemoryTypeBadgeProps {
  type: MemoryType;
}

const TYPE_COLORS: Record<MemoryType, string> = {
  user: "#3b82f6", // blue-500
  feedback: "#22c55e", // green-500
  project: "#a855f7", // purple-500
  reference: "#f97316", // orange-500
};

const TYPE_LABELS: Record<MemoryType, string> = {
  user: "用户",
  feedback: "反馈",
  project: "项目",
  reference: "参考",
};

export function MemoryTypeBadge({ type }: MemoryTypeBadgeProps) {
  const [isHovered, setIsHovered] = useState(false);
  const color = TYPE_COLORS[type];
  const label = TYPE_LABELS[type];

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "var(--radius-sm)",
        background: isHovered ? color : `${color}20`,
        color: isHovered ? "#fff" : color,
        fontSize: "11px",
        fontWeight: 500,
        fontFamily: "var(--font-ui)",
        transition: "all var(--duration) var(--ease-out)",
        cursor: "default",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {label}
    </span>
  );
}
