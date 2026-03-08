"use client";

import { cn } from "@/lib/utils";

// 简化的状态类型（基于 ChatMessage 没有 status 字段，使用 streaming 状态）
type StatusType = "pending" | "streaming" | "completed" | "error";

interface StatusIndicatorProps {
  status: StatusType;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  animate?: boolean;
  className?: string;
}

const STATUS_CONFIG: Record<StatusType, { label: string; dotColor: string; color: string; animate: boolean }> = {
  pending: {
    label: "等待中",
    dotColor: "bg-yellow-400",
    color: "text-yellow-600",
    animate: true,
  },
  streaming: {
    label: "流式传输",
    dotColor: "bg-blue-500",
    color: "text-blue-600",
    animate: true,
  },
  completed: {
    label: "已完成",
    dotColor: "bg-green-500",
    color: "text-green-600",
    animate: false,
  },
  error: {
    label: "错误",
    dotColor: "bg-red-500",
    color: "text-red-600",
    animate: false,
  },
};

const SIZE_CONFIG = {
  sm: {
    dot: "w-1.5 h-1.5",
    label: "text-[10px]",
  },
  md: {
    dot: "w-2 h-2",
    label: "text-xs",
  },
  lg: {
    dot: "w-2.5 h-2.5",
    label: "text-sm",
  },
};

export function StatusIndicator({
  status,
  size = "md",
  showLabel = false,
  animate,
  className,
}: StatusIndicatorProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.completed;
  const sizeConfig = SIZE_CONFIG[size];

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <span
        className={cn(
          "rounded-full",
          sizeConfig.dot,
          config.dotColor,
          (animate ?? config.animate) && "animate-pulse",
        )}
      />
      {showLabel && (
        <span className={cn(sizeConfig.label, config.color)}>
          {config.label}
        </span>
      )}
    </div>
  );
}
