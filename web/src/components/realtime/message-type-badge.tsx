"use client";

import { cn } from "@/lib/utils";
import type { RealtimeMessageType } from "@/types/realtime-message";
import { MESSAGE_TYPE_CONFIG } from "@/types/realtime-message";
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
} from "lucide-react";

interface MessageTypeBadgeProps {
  type: RealtimeMessageType;
  showIcon?: boolean;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const ICON_MAP = {
  User,
  Bot,
  Brain,
  Wrench,
  CheckCircle,
  AlertCircle,
  Zap,
  Play,
  Square,
};

const SIZE_CONFIG = {
  sm: {
    badge: "px-1.5 py-0.5 text-[10px]",
    icon: 10,
    gap: "gap-1",
  },
  md: {
    badge: "px-2 py-0.5 text-xs",
    icon: 12,
    gap: "gap-1.5",
  },
  lg: {
    badge: "px-2.5 py-1 text-sm",
    icon: 14,
    gap: "gap-2",
  },
};

export function MessageTypeBadge({
  type,
  showIcon = true,
  showLabel = true,
  size = "md",
  className,
}: MessageTypeBadgeProps) {
  const config = MESSAGE_TYPE_CONFIG[type];
  const sizeConfig = SIZE_CONFIG[size];
  const Icon = ICON_MAP[config.icon as keyof typeof ICON_MAP];

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
      {showIcon && Icon && <Icon size={sizeConfig.icon} />}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}
