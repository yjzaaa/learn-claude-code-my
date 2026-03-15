/**
 * AgentHierarchy - Agent 层级树形图
 *
 * 显示 Agent 调用树，包括子智能体和后台任务
 */

import React, { useState } from 'react';
import { useAgentHierarchy, useActiveAgentId } from '@/monitoring';
import { AgentNode, AgentState, AgentType, TreeNode } from '@/monitoring/domain';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface TreeNodeProps {
  node: TreeNode<AgentNode>;
  depth: number;
  activeAgentId: string | null;
  expandedNodes: Set<string>;
  onToggleExpand: (id: string) => void;
}

const stateColors: Record<AgentState, string> = {
  [AgentState.IDLE]: 'bg-zinc-100 text-zinc-600 border-zinc-300',
  [AgentState.INITIALIZING]: 'bg-blue-50 text-blue-600 border-blue-300',
  [AgentState.THINKING]: 'bg-amber-50 text-amber-600 border-amber-300',
  [AgentState.TOOL_CALLING]: 'bg-violet-50 text-violet-600 border-violet-300',
  [AgentState.WAITING_FOR_TOOL]: 'bg-orange-50 text-orange-600 border-orange-300',
  [AgentState.SUBAGENT_RUNNING]: 'bg-indigo-50 text-indigo-600 border-indigo-300',
  [AgentState.BACKGROUND_TASKS]: 'bg-cyan-50 text-cyan-600 border-cyan-300',
  [AgentState.PAUSED]: 'bg-zinc-50 text-zinc-500 border-zinc-300',
  [AgentState.COMPLETED]: 'bg-emerald-50 text-emerald-600 border-emerald-300',
  [AgentState.ERROR]: 'bg-red-50 text-red-600 border-red-300',
};

const stateDotColors: Record<AgentState, string> = {
  [AgentState.IDLE]: 'bg-zinc-400',
  [AgentState.INITIALIZING]: 'bg-blue-500',
  [AgentState.THINKING]: 'bg-amber-500',
  [AgentState.TOOL_CALLING]: 'bg-violet-500',
  [AgentState.WAITING_FOR_TOOL]: 'bg-orange-500',
  [AgentState.SUBAGENT_RUNNING]: 'bg-indigo-500',
  [AgentState.BACKGROUND_TASKS]: 'bg-cyan-500',
  [AgentState.PAUSED]: 'bg-zinc-400',
  [AgentState.COMPLETED]: 'bg-emerald-500',
  [AgentState.ERROR]: 'bg-red-500',
};

const typeIcons: Record<AgentType, React.ReactNode> = {
  root: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  ),
  subagent: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  background_task: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
};

const typeLabels: Record<AgentType, string> = {
  root: '根节点',
  subagent: '子智能体',
  background_task: '后台任务',
};

function formatDuration(startTime: Date, endTime?: Date): string {
  const end = endTime || new Date();
  const ms = end.getTime() - startTime.getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function TreeNodeComponent({
  node,
  depth,
  activeAgentId,
  expandedNodes,
  onToggleExpand,
}: TreeNodeProps) {
  const agent = node.data;
  const isActive = agent.id === activeAgentId;
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedNodes.has(agent.id);

  return (
    <div className="select-none">
      <div
        className={cn(
          'flex items-center gap-2 p-2.5 rounded-lg border transition-all duration-200',
          stateColors[agent.status],
          isActive && 'ring-2 ring-offset-1 ring-blue-500 shadow-md',
          !isActive && 'hover:shadow-sm'
        )}
        style={{ marginLeft: depth * 12 }}
      >
        {/* Expand/Collapse Button */}
        <button
          onClick={() => hasChildren && onToggleExpand(agent.id)}
          className={cn(
            'w-5 h-5 flex items-center justify-center rounded text-sm transition-colors',
            hasChildren ? 'hover:bg-black/10 cursor-pointer' : 'invisible'
          )}
        >
          {hasChildren && (isExpanded ? '▼' : '▶')}
        </button>

        {/* Status Dot */}
        <div
          className={cn(
            'w-2 h-2 rounded-full shrink-0',
            stateDotColors[agent.status],
            (agent.status === AgentState.THINKING || agent.status === AgentState.TOOL_CALLING) && 'animate-pulse'
          )}
        />

        {/* Type Icon */}
        <div
          className={cn(
            'w-7 h-7 rounded-md flex items-center justify-center shrink-0',
            agent.type === 'root' && 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
            agent.type === 'subagent' && 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
            agent.type === 'background_task' && 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300'
          )}
          title={typeLabels[agent.type]}
        >
          {typeIcons[agent.type]}
        </div>

        {/* Agent Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{agent.name}</span>
            {isActive && (
              <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full shrink-0">
                活动
              </span>
            )}
          </div>
          <div className="text-xs text-zinc-500">
            {formatDuration(agent.startTime, agent.endTime)}
          </div>
        </div>

        {/* Status Label */}
        <div className="text-xs px-2 py-0.5 rounded-full bg-white/50 dark:bg-zinc-800/50 shrink-0">
          {agent.status}
        </div>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="mt-1">
          {node.children.map((child) => (
            <TreeNodeComponent
              key={child.data.id}
              node={child}
              depth={depth + 1}
              activeAgentId={activeAgentId}
              expandedNodes={expandedNodes}
              onToggleExpand={onToggleExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AgentHierarchy() {
  const hierarchy = useAgentHierarchy();
  const activeAgentId = useActiveAgentId();
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  const handleToggleExpand = (id: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const expandAll = () => {
    if (!hierarchy) return;
    const allIds = new Set<string>();
    const collectIds = (node: TreeNode<AgentNode>) => {
      allIds.add(node.data.id);
      node.children.forEach(collectIds);
    };
    collectIds(hierarchy);
    setExpandedNodes(allIds);
  };

  const collapseAll = () => {
    setExpandedNodes(new Set());
  };

  // Loading state
  if (hierarchy === null) {
    return (
      <Card>
        <div className="flex items-center justify-center h-32 text-zinc-400">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 border-2 border-zinc-300 border-t-blue-500 rounded-full animate-spin" />
            <span className="text-sm">加载中...</span>
          </div>
        </div>
      </Card>
    );
  }

  // Empty state
  if (!hierarchy) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center h-32 text-zinc-400">
          <svg className="w-10 h-10 mb-2 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <span className="text-sm">暂无 Agent 数据</span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-0">
      {/* Header */}
      <CardHeader className="flex flex-row items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <CardTitle className="text-base">Agent 层级</CardTitle>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={expandAll}>
            展开全部
          </Button>
          <Button variant="outline" size="sm" onClick={collapseAll}>
            收起全部
          </Button>
        </div>
      </CardHeader>

      {/* Tree Content */}
      <div className="p-4 max-h-96 overflow-auto scrollbar-thin">
        <TreeNodeComponent
          node={hierarchy}
          depth={0}
          activeAgentId={activeAgentId}
          expandedNodes={expandedNodes}
          onToggleExpand={handleToggleExpand}
        />
      </div>

      {/* Legend */}
      <div className="px-4 py-2 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50">
        <div className="flex flex-wrap gap-3 text-xs">
          <span className="text-zinc-500">图例:</span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            根节点
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-indigo-500" />
            子智能体
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500" />
            后台任务
          </span>
        </div>
      </div>
    </Card>
  );
}
