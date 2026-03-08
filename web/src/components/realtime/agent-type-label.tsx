"use client";

import { cn } from "@/lib/utils";
import type { ChatRole } from "@/types/openai";
import { Bot, Database, Search, ShieldCheck, BarChart3, Puzzle, Settings, HardHat, User, Wrench } from "lucide-react";

interface RoleLabelProps {
  role: ChatRole | string | undefined;
  size?: "sm" | "md" | "lg";
  showDescription?: boolean;
  className?: string;
  /** Agent 名称（动态显示，如 TodoAgent、SubAgentWithPlugins） */
  agentName?: string;
}

// 角色图标映射
const ROLE_ICONS: Record<ChatRole, React.ComponentType<{ className?: string }>> = {
  system: Settings,
  user: User,
  assistant: Bot,
  tool: Wrench,
};

// 角色配置
const ROLE_CONFIG: Record<ChatRole, { label: string; description: string; color: string; bgColor: string; borderColor: string }> = {
  system: {
    label: "系统",
    description: "系统消息",
    color: "text-gray-600",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-200",
  },
  user: {
    label: "用户",
    description: "用户输入",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
  },
  assistant: {
    label: "助手",
    description: "AI 助手",
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
  },
  tool: {
    label: "工具",
    description: "工具调用结果",
    color: "text-cyan-600",
    bgColor: "bg-cyan-50",
    borderColor: "border-cyan-200",
  },
};

// 解析角色类型
function parseRole(role: ChatRole | string | undefined): {
  type: ChatRole | string;
  config: typeof ROLE_CONFIG[ChatRole];
  Icon: React.ComponentType<{ className?: string }>;
} {
  const type = (role || "assistant") as ChatRole;
  const config = ROLE_CONFIG[type] || ROLE_CONFIG.assistant;
  const Icon = ROLE_ICONS[type] || ROLE_ICONS.assistant;

  return {
    type,
    config,
    Icon,
  };
}

export function RoleLabel({
  role,
  size = "md",
  showDescription = false,
  className,
  agentName,
}: RoleLabelProps) {
  const { config, Icon } = parseRole(role);

  const sizeClasses = {
    sm: "px-1.5 py-0.5 text-[10px] gap-1",
    md: "px-2 py-1 text-xs gap-1.5",
    lg: "px-3 py-1.5 text-sm gap-2",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-3.5 w-3.5",
    lg: "h-4 w-4",
  };

  // 使用传入的 agentName（如 TodoAgent），否则使用默认标签（如 助手）
  const displayLabel = agentName || config.label;
  const displayTitle = agentName
    ? `${agentName} (${config.description})`
    : config.description;

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md border font-medium",
        config.bgColor,
        config.borderColor,
        config.color,
        sizeClasses[size],
        className
      )}
      title={displayTitle}
    >
      <Icon className={iconSizes[size]} />
      <span>{displayLabel}</span>
    </div>
  );
}

// 紧凑版本（仅图标）
export function RoleIcon({
  role,
  size = "md",
  className,
}: {
  role: ChatRole | string | undefined;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const { config, Icon } = parseRole(role);

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center rounded-full p-1",
        config.bgColor,
        config.color,
        className
      )}
      title={config.description}
    >
      <Icon className={iconSizes[size]} />
    </div>
  );
}

// 角色选择器（用于切换角色）
export function RoleSelector({
  currentRole,
  onSelect,
  className,
}: {
  currentRole: ChatRole;
  onSelect: (role: ChatRole) => void;
  className?: string;
}) {
  const roles: ChatRole[] = ["system", "user", "assistant", "tool"];

  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {roles.map((role) => {
        const config = ROLE_CONFIG[role];
        const Icon = ROLE_ICONS[role];
        return (
          <button
            key={role}
            onClick={() => onSelect(role)}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              "border hover:shadow-sm",
              currentRole === role
                ? `${config.bgColor} ${config.borderColor} ${config.color} ring-1 ring-offset-1`
                : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{config.label}</span>
          </button>
        );
      })}
    </div>
  );
}
