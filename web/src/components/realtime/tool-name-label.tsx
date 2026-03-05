"use client";

import { cn } from "@/lib/utils";
import { Terminal } from "lucide-react";

interface ToolNameLabelProps {
  toolName: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_CONFIG = {
  sm: {
    container: "px-1.5 py-0.5 text-[10px]",
    icon: 10,
    gap: "gap-1",
  },
  md: {
    container: "px-2 py-0.5 text-xs",
    icon: 12,
    gap: "gap-1.5",
  },
  lg: {
    container: "px-2.5 py-1 text-sm",
    icon: 14,
    gap: "gap-2",
  },
};

export function ToolNameLabel({
  toolName,
  size = "md",
  className,
}: ToolNameLabelProps) {
  const sizeConfig = SIZE_CONFIG[size];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md font-mono font-medium",
        "bg-slate-100 text-slate-700",
        "dark:bg-slate-800 dark:text-slate-300",
        sizeConfig.container,
        sizeConfig.gap,
        className
      )}
    >
      <Terminal size={sizeConfig.icon} />
      <span>{toolName}</span>
    </span>
  );
}
