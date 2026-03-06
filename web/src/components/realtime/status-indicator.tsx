"use client";

import { cn } from "@/lib/utils";
import type { MessageStatus } from "@/types/realtime-message";
import { MESSAGE_STATUS_CONFIG } from "@/types/realtime-message";

interface StatusIndicatorProps {
  status: MessageStatus;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  animate?: boolean;
  className?: string;
}

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
  const config = MESSAGE_STATUS_CONFIG[status];
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
