/**
 * StateMachineViz - 状态机可视化
 *
 * 显示当前 Agent 状态、状态转换历史、在每种状态的持续时间
 */

import React, { useMemo, useState, useEffect } from 'react';
import { useAgentState, useMonitoringStore } from '@/monitoring';
import { AgentState } from '@/monitoring/domain';
import { StateTransition } from '@/monitoring/services/UIStateMachine';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';

// 状态定义和连接关系
const stateGraph: Record<AgentState, { label: string; color: string; next: AgentState[] }> = {
  [AgentState.IDLE]: {
    label: '空闲',
    color: 'bg-zinc-100 text-zinc-600 border-zinc-300',
    next: [AgentState.INITIALIZING],
  },
  [AgentState.INITIALIZING]: {
    label: '初始化',
    color: 'bg-blue-50 text-blue-600 border-blue-300',
    next: [AgentState.THINKING, AgentState.ERROR],
  },
  [AgentState.THINKING]: {
    label: '思考中',
    color: 'bg-amber-50 text-amber-600 border-amber-300',
    next: [AgentState.TOOL_CALLING, AgentState.SUBAGENT_RUNNING, AgentState.COMPLETED, AgentState.ERROR],
  },
  [AgentState.TOOL_CALLING]: {
    label: '调用工具',
    color: 'bg-violet-50 text-violet-600 border-violet-300',
    next: [AgentState.WAITING_FOR_TOOL, AgentState.ERROR],
  },
  [AgentState.WAITING_FOR_TOOL]: {
    label: '等待工具',
    color: 'bg-orange-50 text-orange-600 border-orange-300',
    next: [AgentState.THINKING, AgentState.ERROR],
  },
  [AgentState.SUBAGENT_RUNNING]: {
    label: '子智能体运行',
    color: 'bg-indigo-50 text-indigo-600 border-indigo-300',
    next: [AgentState.THINKING, AgentState.BACKGROUND_TASKS, AgentState.COMPLETED, AgentState.ERROR],
  },
  [AgentState.BACKGROUND_TASKS]: {
    label: '后台任务',
    color: 'bg-cyan-50 text-cyan-600 border-cyan-300',
    next: [AgentState.THINKING, AgentState.COMPLETED, AgentState.ERROR],
  },
  [AgentState.PAUSED]: {
    label: '暂停',
    color: 'bg-zinc-50 text-zinc-500 border-zinc-300',
    next: [AgentState.THINKING, AgentState.ERROR],
  },
  [AgentState.COMPLETED]: {
    label: '完成',
    color: 'bg-emerald-50 text-emerald-600 border-emerald-300',
    next: [],
  },
  [AgentState.ERROR]: {
    label: '错误',
    color: 'bg-red-50 text-red-600 border-red-300',
    next: [AgentState.IDLE],
  },
};

// 状态位置（用于简化布局）
const statePositions: Record<AgentState, { x: number; y: number }> = {
  [AgentState.IDLE]: { x: 50, y: 10 },
  [AgentState.INITIALIZING]: { x: 50, y: 25 },
  [AgentState.THINKING]: { x: 50, y: 40 },
  [AgentState.TOOL_CALLING]: { x: 25, y: 55 },
  [AgentState.WAITING_FOR_TOOL]: { x: 25, y: 70 },
  [AgentState.SUBAGENT_RUNNING]: { x: 75, y: 55 },
  [AgentState.BACKGROUND_TASKS]: { x: 75, y: 70 },
  [AgentState.PAUSED]: { x: 10, y: 40 },
  [AgentState.COMPLETED]: { x: 50, y: 90 },
  [AgentState.ERROR]: { x: 90, y: 40 },
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function StateNode({
  state,
  isActive,
  isInHistory,
}: {
  state: AgentState;
  isActive: boolean;
  isInHistory: boolean;
}) {
  const config = stateGraph[state];
  const pos = statePositions[state];

  return (
    <div
      className={cn(
        'absolute transform -translate-x-1/2 -translate-y-1/2 px-3 py-2 rounded-lg border-2 text-sm font-medium transition-all duration-300',
        config.color,
        isActive && 'ring-4 ring-blue-300 scale-110 shadow-lg z-10',
        isInHistory && !isActive && 'opacity-80',
        !isActive && !isInHistory && 'opacity-40'
      )}
      style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
    >
      <div className="flex items-center gap-2">
        {isActive && <span className="w-2 h-2 bg-current rounded-full animate-pulse" />}
        <span>{config.label}</span>
      </div>
      <div className="text-xs opacity-70 mt-0.5">{state}</div>
    </div>
  );
}

export default function StateMachineViz() {
  const currentState = useAgentState();
  const store = useMonitoringStore();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Get state history from store's state machine
  const stateHistory = useMemo<StateTransition[]>(() => {
    // @ts-expect-error - accessing internal state machine for visualization
    const stateMachine = store._stateMachine;
    if (stateMachine && typeof stateMachine.getHistory === 'function') {
      return stateMachine.getHistory();
    }
    return [];
  }, [store, currentState]);

  // Get time in current state
  const timeInCurrentState = useMemo(() => {
    // @ts-expect-error - accessing internal state machine
    const stateMachine = store._stateMachine;
    if (stateMachine && typeof stateMachine.getTimeInStateMs === 'function') {
      return stateMachine.getTimeInStateMs();
    }
    return 0;
  }, [store, currentState]);

  // Calculate unique states in history
  const statesInHistory = useMemo(() => {
    const states = new Set<AgentState>([currentState]);
    stateHistory.forEach((t) => {
      states.add(t.fromState);
      states.add(t.toState);
    });
    return states;
  }, [stateHistory, currentState]);

  return (
    <Card className="p-0">
      {/* Header */}
      <CardHeader className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 flex flex-row items-center justify-between">
        <CardTitle className="text-base">状态机</CardTitle>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'px-2 py-0.5 rounded-full text-xs font-medium',
              stateGraph[currentState].color
            )}
          >
            当前: {stateGraph[currentState].label}
          </span>
          {isClient && (
            <span className="text-xs text-zinc-500">{formatDuration(timeInCurrentState)}</span>
          )}
        </div>
      </CardHeader>

      {/* State Graph */}
      <div className="p-4">
        <div className="relative h-80 bg-zinc-50 dark:bg-zinc-900/30 rounded-lg border border-zinc-200 dark:border-zinc-800 overflow-hidden">
          {/* SVG Connections */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {Object.entries(stateGraph).map(([fromState, config]) =>
              config.next.map((toState) => {
                const from = statePositions[fromState as AgentState];
                const to = statePositions[toState];
                const isActiveTransition =
                  stateHistory.length > 0 &&
                  stateHistory[stateHistory.length - 1].fromState === fromState &&
                  stateHistory[stateHistory.length - 1].toState === toState;

                return (
                  <line
                    key={`${fromState}-${toState}`}
                    x1={`${from.x}%`}
                    y1={`${from.y}%`}
                    x2={`${to.x}%`}
                    y2={`${to.y}%`}
                    stroke={isActiveTransition ? '#3b82f6' : '#d4d4d8'}
                    strokeWidth={isActiveTransition ? 3 : 1}
                    strokeDasharray={isActiveTransition ? '0' : '4,4'}
                    className="transition-all duration-500"
                  />
                );
              })
            )}
          </svg>

          {/* State Nodes */}
          {Object.values(AgentState).map((state) => (
            <StateNode
              key={state}
              state={state}
              isActive={state === currentState}
              isInHistory={statesInHistory.has(state)}
            />
          ))}
        </div>
      </div>

      {/* Transition History */}
      <div className="px-4 py-3 border-t border-zinc-200 dark:border-zinc-800">
        <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">状态转换历史</h4>
        {stateHistory.length === 0 ? (
          <div className="text-sm text-zinc-400 italic">暂无状态转换记录</div>
        ) : (
          <div className="max-h-32 overflow-auto space-y-1 scrollbar-thin">
            {[...stateHistory].reverse().map((transition, index) => (
              <div
                key={index}
                className="flex items-center gap-2 text-sm p-1.5 rounded hover:bg-zinc-50 dark:hover:bg-zinc-800"
              >
                <span className="text-xs text-zinc-400 font-mono">
                  {isClient
                    ? transition.timestamp.toLocaleTimeString()
                    : transition.timestamp.toISOString().slice(11, 19)}
                </span>
                <span className={cn('px-1.5 py-0.5 rounded text-xs', stateGraph[transition.fromState].color)}>
                  {stateGraph[transition.fromState].label}
                </span>
                <span className="text-zinc-400">→</span>
                <span className={cn('px-1.5 py-0.5 rounded text-xs', stateGraph[transition.toState].color)}>
                  {stateGraph[transition.toState].label}
                </span>
                {transition.durationMs && (
                  <span className="text-xs text-zinc-500 ml-auto">
                    持续 {formatDuration(transition.durationMs)}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
