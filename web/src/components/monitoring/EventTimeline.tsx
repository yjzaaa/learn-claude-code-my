/**
 * EventTimeline - 事件时间线
 *
 * 按时间顺序显示所有事件
 * 支持事件类型过滤
 * 显示事件详情（类型、来源、时间戳）
 * 支持展开查看 payload
 */

import React, { useState, useMemo } from 'react';
import { useAllEvents } from '@/monitoring';
import { EventType, MonitoringEvent, EventPriority } from '@/monitoring/domain';

// 事件类型分组和颜色
const eventTypeConfig: Record<
  string,
  { label: string; color: string; bgColor: string }
> = {
  // Agent 生命周期
  [EventType.AGENT_STARTED]: {
    label: 'Agent 启动',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  [EventType.AGENT_STOPPED]: {
    label: 'Agent 停止',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
  },
  [EventType.AGENT_ERROR]: {
    label: 'Agent 错误',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
  [EventType.AGENT_PAUSED]: {
    label: 'Agent 暂停',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
  },
  [EventType.AGENT_RESUMED]: {
    label: 'Agent 恢复',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },

  // 消息流
  [EventType.MESSAGE_START]: {
    label: '消息开始',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
  [EventType.MESSAGE_DELTA]: {
    label: '消息增量',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
  },
  [EventType.MESSAGE_COMPLETE]: {
    label: '消息完成',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  [EventType.REASONING_DELTA]: {
    label: '推理增量',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },

  // 工具调用
  [EventType.TOOL_CALL_START]: {
    label: '工具调用开始',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
  },
  [EventType.TOOL_CALL_END]: {
    label: '工具调用结束',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  [EventType.TOOL_CALL_ERROR]: {
    label: '工具调用错误',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
  [EventType.TOOL_RESULT]: {
    label: '工具结果',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },

  // 子智能体
  [EventType.SUBAGENT_SPAWNED]: {
    label: '子智能体创建',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
  },
  [EventType.SUBAGENT_STARTED]: {
    label: '子智能体启动',
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-50',
  },
  [EventType.SUBAGENT_PROGRESS]: {
    label: '子智能体进度',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-50',
  },
  [EventType.SUBAGENT_COMPLETED]: {
    label: '子智能体完成',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  [EventType.SUBAGENT_FAILED]: {
    label: '子智能体失败',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },

  // 后台任务
  [EventType.BG_TASK_QUEUED]: {
    label: '任务入队',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
  },
  [EventType.BG_TASK_STARTED]: {
    label: '任务开始',
    color: 'text-cyan-500',
    bgColor: 'bg-cyan-50',
  },
  [EventType.BG_TASK_PROGRESS]: {
    label: '任务进度',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-50',
  },
  [EventType.BG_TASK_COMPLETED]: {
    label: '任务完成',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  [EventType.BG_TASK_FAILED]: {
    label: '任务失败',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },

  // 状态机
  [EventType.STATE_TRANSITION]: {
    label: '状态转换',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
  [EventType.STATE_ENTER]: {
    label: '进入状态',
    color: 'text-purple-500',
    bgColor: 'bg-purple-50',
  },
  [EventType.STATE_EXIT]: {
    label: '退出状态',
    color: 'text-purple-400',
    bgColor: 'bg-purple-50',
  },

  // 资源使用
  [EventType.TOKEN_USAGE]: {
    label: 'Token 使用',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50',
  },
  [EventType.MEMORY_USAGE]: {
    label: '内存使用',
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
  },
  [EventType.LATENCY_METRIC]: {
    label: '延迟指标',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
  },

  // Todo
  [EventType.TODO_CREATED]: {
    label: 'Todo 创建',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
  },
  [EventType.TODO_UPDATED]: {
    label: 'Todo 更新',
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-50',
  },
  [EventType.TODO_COMPLETED]: {
    label: 'Todo 完成',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
  },
};

const priorityConfig: Record<EventPriority, { label: string; color: string }> = {
  [EventPriority.CRITICAL]: { label: '严重', color: 'text-red-600 bg-red-100' },
  [EventPriority.HIGH]: { label: '高', color: 'text-orange-600 bg-orange-100' },
  [EventPriority.NORMAL]: { label: '普通', color: 'text-blue-600 bg-blue-100' },
  [EventPriority.LOW]: { label: '低', color: 'text-gray-600 bg-gray-100' },
};

// 事件类型分组
const eventGroups = [
  { key: 'agent', label: 'Agent 生命周期', types: [EventType.AGENT_STARTED, EventType.AGENT_STOPPED, EventType.AGENT_ERROR, EventType.AGENT_PAUSED, EventType.AGENT_RESUMED] },
  { key: 'message', label: '消息流', types: [EventType.MESSAGE_START, EventType.MESSAGE_DELTA, EventType.MESSAGE_COMPLETE, EventType.REASONING_DELTA] },
  { key: 'tool', label: '工具调用', types: [EventType.TOOL_CALL_START, EventType.TOOL_CALL_END, EventType.TOOL_CALL_ERROR, EventType.TOOL_RESULT] },
  { key: 'subagent', label: '子智能体', types: [EventType.SUBAGENT_SPAWNED, EventType.SUBAGENT_STARTED, EventType.SUBAGENT_PROGRESS, EventType.SUBAGENT_COMPLETED, EventType.SUBAGENT_FAILED] },
  { key: 'bg_task', label: '后台任务', types: [EventType.BG_TASK_QUEUED, EventType.BG_TASK_STARTED, EventType.BG_TASK_PROGRESS, EventType.BG_TASK_COMPLETED, EventType.BG_TASK_FAILED] },
  { key: 'state', label: '状态机', types: [EventType.STATE_TRANSITION, EventType.STATE_ENTER, EventType.STATE_EXIT] },
  { key: 'metrics', label: '资源使用', types: [EventType.TOKEN_USAGE, EventType.MEMORY_USAGE, EventType.LATENCY_METRIC] },
  { key: 'todo', label: 'Todo', types: [EventType.TODO_CREATED, EventType.TODO_UPDATED, EventType.TODO_COMPLETED] },
];

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });
}

// Agent 名称解析结果
interface AgentNameInfo {
  displayName: string;  // 显示名称
  agentType: string;    // 智能体类型 (Main|Subagent|BackgroundTask|Teammate|Unknown)
  subtype?: string;     // 子类型 (如 Explore, Code, Test)
  icon?: string;        // 图标
}

// 解析 Agent 名称格式
// 支持格式: ClassName | Subagent:Type:Name | BackgroundTask:task_id | Teammate:name
function parseAgentName(name: string): AgentNameInfo {
  if (name.startsWith('Subagent:')) {
    const parts = name.split(':');
    const subtype = parts[1] || 'Unknown';
    const displayName = parts[2] || 'Unnamed';
    return {
      displayName: `${displayName}`,
      agentType: 'Subagent',
      subtype,
      icon: '🤖',
    };
  }

  if (name.startsWith('BackgroundTask:')) {
    const taskId = name.split(':')[1] || 'unknown';
    return {
      displayName: `Task:${taskId.slice(0, 8)}`,
      agentType: 'BackgroundTask',
      icon: '⚙️',
    };
  }

  if (name.startsWith('Teammate:')) {
    const teammateName = name.split(':')[1] || 'Unknown';
    return {
      displayName: teammateName,
      agentType: 'Teammate',
      icon: '👤',
    };
  }

  // 主 Agent (如 SFullAgent, TeamLeadAgent 等)
  if (name && name !== 'Unknown Agent') {
    return {
      displayName: name,
      agentType: 'Main',
      icon: '🎯',
    };
  }

  return {
    displayName: name || 'Unknown',
    agentType: 'Unknown',
    icon: '❓',
  };
}

// 从事件中提取 Agent 名称
function getAgentNameInfo(event: MonitoringEvent): AgentNameInfo {
  const payload = event.payload as Record<string, unknown>;

  // 1. 优先从 payload.agent_name 获取
  if (payload?.agent_name && typeof payload.agent_name === 'string') {
    return parseAgentName(payload.agent_name);
  }

  // 2. 尝试驼峰命名 (兼容性)
  if (payload?.agentName && typeof payload.agentName === 'string') {
    return parseAgentName(payload.agentName);
  }

  // 3. 子智能体事件: 从 subagent_name 构建
  if (payload?.subagent_name && typeof payload.subagent_name === 'string') {
    const subagentType = (payload.subagent_type as string) || 'Generic';
    return parseAgentName(`Subagent:${subagentType}:${payload.subagent_name}`);
  }

  // 4. 使用 source 字段
  if (event.source) {
    return parseAgentName(event.source);
  }

  // 5. 默认
  return { displayName: 'Unknown', agentType: 'Unknown', icon: '❓' };
}

// 保持向后兼容
function getAgentName(event: MonitoringEvent): string {
  return getAgentNameInfo(event).displayName;
}

// Agent 类型颜色配置
const agentTypeColors: Record<string, { bg: string; text: string }> = {
  Main: { bg: 'bg-blue-100', text: 'text-blue-700' },
  Subagent: { bg: 'bg-purple-100', text: 'text-purple-700' },
  BackgroundTask: { bg: 'bg-orange-100', text: 'text-orange-700' },
  Teammate: { bg: 'bg-green-100', text: 'text-green-700' },
  Unknown: { bg: 'bg-gray-100', text: 'text-gray-600' },
};

function EventItem({
  event,
  isExpanded,
  onToggle,
}: {
  event: MonitoringEvent;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const config = eventTypeConfig[event.type] || {
    label: event.type,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
  };
  const priority = priorityConfig[event.priority];
  const agentInfo = getAgentNameInfo(event);
  const typeColors = agentTypeColors[agentInfo.agentType] || agentTypeColors.Unknown;

  return (
    <div className="border-l-2 border-gray-200 pl-4 py-2 hover:bg-gray-50 transition-colors">
      {/* Event Header */}
      <div
        className="flex items-start gap-3 cursor-pointer"
        onClick={onToggle}
      >
        {/* Timestamp */}
        <div className="text-xs text-gray-400 font-mono whitespace-nowrap pt-1">
          {formatTimestamp(event.timestamp)}
        </div>

        {/* Type Badge */}
        <div
          className={`
            px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap
            ${config.bgColor} ${config.color}
          `}
        >
          {config.label}
        </div>

        {/* Agent Type Badge */}
        <div
          className={`
            px-1.5 py-0.5 rounded text-xs font-medium whitespace-nowrap
            ${typeColors.bg} ${typeColors.text}
          `}
          title={agentInfo.agentType}
        >
          <span className="mr-1">{agentInfo.icon}</span>
          {agentInfo.agentType === 'Subagent' && agentInfo.subtype
            ? `${agentInfo.subtype}`
            : agentInfo.agentType}
        </div>

        {/* Agent Name */}
        <div className="text-sm text-gray-600 truncate flex-1" title={`${agentInfo.agentType}: ${agentInfo.displayName}`}>
          {agentInfo.displayName}
        </div>

        {/* Priority */}
        {event.priority !== EventPriority.NORMAL && (
          <span
            className={`
              text-xs px-1.5 py-0.5 rounded
              ${priority.color}
            `}
          >
            {priority.label}
          </span>
        )}

        {/* Expand Icon */}
        <div className="text-gray-400">
          {isExpanded ? '▼' : '▶'}
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-2 ml-16 space-y-2">
          {/* Event ID */}
          <div className="text-xs text-gray-400">
            ID: <span className="font-mono">{event.id}</span>
          </div>

          {/* Context Info */}
          <div className="text-xs text-gray-500 flex gap-4">
            <span>Dialog: <span className="font-mono">{event.dialogId}</span></span>
            <span>Context: <span className="font-mono">{event.contextId}</span></span>
            {event.parentId && (
              <span>Parent: <span className="font-mono">{event.parentId}</span></span>
            )}
          </div>

          {/* Payload */}
          {Object.keys(event.payload).length > 0 && (
            <div className="mt-2">
              <div className="text-xs text-gray-500 mb-1">Payload:</div>
              <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-48">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </div>
          )}

          {/* Metadata */}
          {Object.keys(event.metadata).length > 0 && (
            <div className="mt-2">
              <div className="text-xs text-gray-500 mb-1">Metadata:</div>
              <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-32">
                {JSON.stringify(event.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function EventTimeline() {
  const events = useAllEvents();
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set(eventGroups.map(g => g.key)));
  const [searchTerm, setSearchTerm] = useState('');

  const toggleExpand = (eventId: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  const toggleGroup = (groupKey: string) => {
    setSelectedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  };

  const selectAllGroups = () => {
    setSelectedGroups(new Set(eventGroups.map(g => g.key)));
  };

  const clearAllGroups = () => {
    setSelectedGroups(new Set());
  };

  // Filter events
  const filteredEvents = useMemo(() => {
    // Get all allowed event types from selected groups
    const allowedTypes = new Set<EventType>();
    eventGroups.forEach((group) => {
      if (selectedGroups.has(group.key)) {
        group.types.forEach((type) => allowedTypes.add(type));
      }
    });

    return events
      .filter((event) => allowedTypes.has(event.type))
      .filter((event) => {
        if (!searchTerm) return true;
        const search = searchTerm.toLowerCase();
        return (
          event.type.toLowerCase().includes(search) ||
          event.source.toLowerCase().includes(search) ||
          JSON.stringify(event.payload).toLowerCase().includes(search)
        );
      })
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }, [events, selectedGroups, searchTerm]);

  // Loading state
  if (events === null) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-center h-32 text-gray-400">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
            <span>加载中...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">事件时间线</h3>
          <span className="text-sm text-gray-500">
            {filteredEvents.length} / {events.length} 事件
          </span>
        </div>

        {/* Search */}
        <div className="relative mb-3">
          <input
            type="text"
            placeholder="搜索事件..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          )}
        </div>

        {/* Filter Groups */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={selectAllGroups}
            className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
          >
            全选
          </button>
          <button
            onClick={clearAllGroups}
            className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
          >
            清空
          </button>
          <div className="w-px h-5 bg-gray-300 mx-1" />
          {eventGroups.map((group) => (
            <button
              key={group.key}
              onClick={() => toggleGroup(group.key)}
              className={`
                text-xs px-2 py-1 rounded transition-colors
                ${selectedGroups.has(group.key)
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }
              `}
            >
              {group.label}
            </button>
          ))}
        </div>
      </div>

      {/* Event List */}
      <div className="max-h-96 overflow-auto">
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-400">
            <svg
              className="w-10 h-10 mb-2 text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm">暂无事件</span>
          </div>
        ) : (
          <div className="py-2">
            {filteredEvents.map((event) => (
              <EventItem
                key={event.id}
                event={event}
                isExpanded={expandedEvents.has(event.id)}
                onToggle={() => toggleExpand(event.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
