"use client";

import { cn } from "@/lib/utils";
import { AgentType, AGENT_TYPE_CONFIG } from "@/types/realtime-message";
import { Bot, Database, Search, ShieldCheck, BarChart3, Puzzle, Settings, HardHat } from "lucide-react";

interface AgentTypeLabelProps {
  agentType: AgentType | string | undefined;
  size?: "sm" | "md" | "lg";
  showDescription?: boolean;
  className?: string;
}

const AGENT_ICONS: Record<AgentType, React.ComponentType<{ className?: string }>> = {
  master: Bot,
  sql_executor: Database,
  schema_explorer: Search,
  data_validator: ShieldCheck,
  analyzer: BarChart3,
  skill_loader: Puzzle,
  default: Settings,
};

// Worker 类型配置（处理 worker:xxx 格式）
const WORKER_CONFIG: Record<string, { label: string; description: string; icon: React.ComponentType<{ className?: string }>; color: string; bgColor: string; borderColor: string }> = {
  "worker:sql_executor": {
    label: "SQL执行",
    description: "SQL执行子代理",
    icon: Database,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
  },
  "worker:schema_explorer": {
    label: "Schema探索",
    description: "Schema探索子代理",
    icon: Search,
    color: "text-cyan-600",
    bgColor: "bg-cyan-50",
    borderColor: "border-cyan-200",
  },
  "worker:data_validator": {
    label: "数据验证",
    description: "数据验证子代理",
    icon: ShieldCheck,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
  },
  "worker:analyzer": {
    label: "分析器",
    description: "数据分析子代理",
    icon: BarChart3,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-200",
  },
};

// 解析 agent_type，支持 worker:xxx 格式
function parseAgentType(agentType: AgentType | string | undefined): {
  type: AgentType | string;
  config: typeof AGENT_TYPE_CONFIG[AgentType] | typeof WORKER_CONFIG[string];
  Icon: React.ComponentType<{ className?: string }>;
  isWorker: boolean;
} {
  const type = agentType || "default";

  // 检查是否是 worker 类型
  if (typeof type === "string" && type.startsWith("worker:")) {
    const workerType = type as keyof typeof WORKER_CONFIG;
    const workerConfig = WORKER_CONFIG[workerType] || {
      label: type.replace("worker:", ""),
      description: "子代理",
      icon: HardHat,
      color: "text-slate-600",
      bgColor: "bg-slate-50",
      borderColor: "border-slate-200",
    };
    return {
      type,
      config: workerConfig,
      Icon: workerConfig.icon,
      isWorker: true,
    };
  }

  // 标准 agent 类型
  const config = AGENT_TYPE_CONFIG[type as AgentType] || AGENT_TYPE_CONFIG.default;
  const Icon = AGENT_ICONS[type as AgentType] || AGENT_ICONS.default;
  return {
    type,
    config,
    Icon,
    isWorker: false,
  };
}

export function AgentTypeLabel({
  agentType,
  size = "md",
  showDescription = false,
  className,
}: AgentTypeLabelProps) {
  const { config, Icon } = parseAgentType(agentType);

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
      title={config.description}
    >
      <Icon className={iconSizes[size]} />
      <span>{config.label}</span>
    </div>
  );
}

// 紧凑版本（仅图标）
export function AgentTypeIcon({
  agentType,
  size = "md",
  className,
}: {
  agentType: AgentType | string | undefined;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const { config, Icon } = parseAgentType(agentType);

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

// 代理类型选择器（用于切换代理）
export function AgentTypeSelector({
  currentAgent,
  onSelect,
  className,
}: {
  currentAgent: AgentType;
  onSelect: (agent: AgentType) => void;
  className?: string;
}) {
  const agents: AgentType[] = [
    "master",
    "sql_executor",
    "schema_explorer",
    "data_validator",
    "analyzer",
  ];

  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {agents.map((agent) => (
        <button
          key={agent}
          onClick={() => onSelect(agent)}
          className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
            "border hover:shadow-sm",
            currentAgent === agent
              ? `${AGENT_TYPE_CONFIG[agent].bgColor} ${AGENT_TYPE_CONFIG[agent].borderColor} ${AGENT_TYPE_CONFIG[agent].color} ring-1 ring-offset-1`
              : "bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50"
          )}
        >
          {(() => {
            const Icon = AGENT_ICONS[agent];
            return <Icon className="h-3.5 w-3.5" />;
          })()}
          <span>{AGENT_TYPE_CONFIG[agent].label}</span>
        </button>
      ))}
    </div>
  );
}
