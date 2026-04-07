"use client";

import { useState, useEffect } from "react";

interface MemoryStatusProps {
  isConnected: boolean;
  memoryCount: number;
  lastUpdated?: Date;
}

export function MemoryStatus({
  isConnected,
  memoryCount,
  lastUpdated,
}: MemoryStatusProps) {
  const [currentTime, setCurrentTime] = useState<Date>(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000); // Update every minute

    return () => clearInterval(timer);
  }, []);

  const formatLastUpdated = (date?: Date): string => {
    if (!date) return "从未更新";

    const diffMs = currentTime.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "刚刚";
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 14px",
        background: "var(--overlay-subtle)",
        borderTop: "1px solid var(--border)",
        fontSize: "12px",
        fontFamily: "var(--font-ui)",
        color: "var(--text-muted)",
      }}
    >
      {/* Connection status */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
        }}
      >
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: isConnected ? "#22c55e" : "#ef4444",
            boxShadow: isConnected
              ? "0 0 0 2px rgba(34, 197, 94, 0.2)"
              : "0 0 0 2px rgba(239, 68, 68, 0.2)",
            transition: "all var(--duration) var(--ease-out)",
          }}
        />
        <span>{isConnected ? "已连接" : "未连接"}</span>
      </div>

      {/* Memory count */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
        }}
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          style={{ opacity: 0.7 }}
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
        <span>{memoryCount} 条记忆</span>
      </div>

      {/* Last updated */}
      <span style={{ opacity: 0.7 }}>
        更新于 {formatLastUpdated(lastUpdated)}
      </span>
    </div>
  );
}
