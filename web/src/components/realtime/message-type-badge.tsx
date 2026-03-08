"use client";

import { cn } from "@/lib/utils";
import type { ChatRole } from "@/types/openai";
import {
  User,
  Bot,
  Brain,
  Wrench,
  CheckCircle,
  AlertCircle,
  Zap,
  Play,
  Square,
  Settings,
} from "lucide-react";

interface MessageTypeBadgeProps {
  role: ChatRole;
  showIcon?: boolean;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const ROLE_CONFIG: Record<ChatRole, { label: string; icon: React.ComponentType<{ className?: string }>; bgColor: string; color: string }> = {
  system: {
    label: "系统",
    icon: Settings,
    bgColor: "bg-gray-100",
    color: "text-gray-700",
  },
  user: {
    label: "用户",
    icon: User,
    bgColor: "bg-blue-100",
    color: "text-blue-700",
  },
  assistant: {
    label: "助手",
    icon: Bot,
    bgColor: "bg-purple-100",
    color: "text-purple-700",
  },
  tool: {
    label: "工具",
    icon: Wrench,
    bgColor: "bg-cyan-100",
    color: "text-cyan-700",
  },
};

const SIZE_CONFIG = {
  sm: {
    badge: "px-1.5 py-0.5 text-[10px]",
    icon: "h-2.5 w-2.5",
    gap: "gap-1",
  },
  md: {
    badge: "px-2 py-0.5 text-xs",
    icon: "h-3 w-3",
    gap: "gap-1.5",
  },
  lg: {
    badge: "px-2.5 py-1 text-sm",
    icon: "h-3.5 w-3.5",
    gap: "gap-2",
  },
};

export function MessageTypeBadge({
  role,
  showIcon = true,
  showLabel = true,
  size = "md",
  className,
}: MessageTypeBadgeProps) {
  const config = ROLE_CONFIG[role] || ROLE_CONFIG.assistant;
  const sizeConfig = SIZE_CONFIG[size];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        config.bgColor,
        config.color,
        sizeConfig.badge,
        sizeConfig.gap,
        className
      )}
    >
      {showIcon && <Icon className={sizeConfig.icon} />}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}
