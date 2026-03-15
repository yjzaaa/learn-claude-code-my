/**
 * MetricsPanel - 指标面板
 *
 * 显示 Token 使用情况、工具调用次数、延迟统计
 */

import React, { useMemo } from 'react';
import { useMetricsReport } from '@/monitoring';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';

// 格式化数字
function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

// 格式化持续时间
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
}

// 进度条组件
function ProgressBar({
  value,
  max,
  color = 'blue',
  showLabel = true,
}: {
  value: number;
  max: number;
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'red';
  showLabel?: boolean;
}) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-emerald-500',
    purple: 'bg-violet-500',
    orange: 'bg-orange-500',
    red: 'bg-red-500',
  };

  return (
    <div className="w-full">
      <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-500', colorClasses[color])}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between text-xs text-zinc-500 mt-1">
          <span>{formatNumber(value)}</span>
          <span>{formatNumber(max)}</span>
        </div>
      )}
    </div>
  );
}

// 指标卡片组件
function MetricCard({
  title,
  value,
  subtitle,
  icon,
  color = 'blue',
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'red';
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300',
    green: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300',
    purple: 'bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-300',
    orange: 'bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:text-orange-300',
    red: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300',
  };

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900/50 rounded-lg p-4 border border-zinc-200 dark:border-zinc-800">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-zinc-500">{title}</p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-zinc-400 mt-1">{subtitle}</p>}
        </div>
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>
          {icon}
        </div>
      </div>
    </div>
  );
}

// Token 使用图表
function TokenUsageChart({ input, output }: { input: number; output: number }) {
  const total = input + output;
  const inputPercentage = total > 0 ? (input / total) * 100 : 0;
  const outputPercentage = total > 0 ? (output / total) * 100 : 0;

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900/50 rounded-lg p-4 border border-zinc-200 dark:border-zinc-800">
      <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-4">Token 使用分布</h4>

      {/* Stacked Bar */}
      <div className="h-4 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden flex">
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{ width: `${inputPercentage}%` }}
        />
        <div
          className="h-full bg-emerald-500 transition-all duration-500"
          style={{ width: `${outputPercentage}%` }}
        />
      </div>

      {/* Legend */}
      <div className="flex justify-between mt-3">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <div>
            <span className="text-sm text-zinc-600 dark:text-zinc-400">Input</span>
            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 ml-2">
              {formatNumber(input)}
            </span>
            <span className="text-xs text-zinc-400 ml-1">({inputPercentage.toFixed(1)}%)</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500" />
          <div>
            <span className="text-sm text-zinc-600 dark:text-zinc-400">Output</span>
            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100 ml-2">
              {formatNumber(output)}
            </span>
            <span className="text-xs text-zinc-400 ml-1">({outputPercentage.toFixed(1)}%)</span>
          </div>
        </div>
      </div>

      {/* Total */}
      <div className="mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-700">
        <div className="flex justify-between items-center">
          <span className="text-sm text-zinc-500">总计</span>
          <span className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            {formatNumber(total)} tokens
          </span>
        </div>
      </div>
    </div>
  );
}

// 延迟分布图表
function LatencyChart({ averageLatency, p95Latency }: { averageLatency: number; p95Latency: number }) {
  const maxLatency = Math.max(p95Latency * 1.2, 100);

  return (
    <div className="bg-zinc-50 dark:bg-zinc-900/50 rounded-lg p-4 border border-zinc-200 dark:border-zinc-800">
      <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-4">延迟统计</h4>

      {/* Average Latency */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-zinc-600 dark:text-zinc-400">平均延迟</span>
          <span className="font-medium text-zinc-900 dark:text-zinc-100">{averageLatency.toFixed(0)}ms</span>
        </div>
        <ProgressBar value={averageLatency} max={maxLatency} color="purple" showLabel={false} />
      </div>

      {/* P95 Latency */}
      <div>
        <div className="flex justify-between text-sm mb-1">
          <span className="text-zinc-600 dark:text-zinc-400">P95 延迟</span>
          <span className="font-medium text-zinc-900 dark:text-zinc-100">{p95Latency.toFixed(0)}ms</span>
        </div>
        <ProgressBar value={p95Latency} max={maxLatency} color="orange" showLabel={false} />
      </div>

      {/* Latency Rating */}
      <div className="mt-4 pt-3 border-t border-zinc-200 dark:border-zinc-700">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-500">评级:</span>
          {averageLatency < 100 ? (
            <span className="text-sm font-medium text-emerald-600">优秀</span>
          ) : averageLatency < 300 ? (
            <span className="text-sm font-medium text-blue-600">良好</span>
          ) : averageLatency < 1000 ? (
            <span className="text-sm font-medium text-amber-600">一般</span>
          ) : (
            <span className="text-sm font-medium text-red-600">较慢</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MetricsPanel() {
  const metrics = useMetricsReport();

  // Loading state
  if (metrics === null) {
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

  const { tokenCount, toolCalls, subagentCalls, averageLatency, p95Latency, durationMs } = metrics;
  const totalTokens = tokenCount.input + tokenCount.output;

  // Icons
  const TokenIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );

  const ToolIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );

  const SubagentIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  );

  const DurationIcon = () => (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );

  return (
    <Card className="p-0">
      {/* Header */}
      <CardHeader className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <CardTitle className="text-base">指标面板</CardTitle>
      </CardHeader>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 gap-4">
          <MetricCard
            title="总 Token 数"
            value={formatNumber(totalTokens)}
            subtitle={`Input: ${formatNumber(tokenCount.input)} / Output: ${formatNumber(tokenCount.output)}`}
            icon={<TokenIcon />}
            color="blue"
          />
          <MetricCard
            title="工具调用"
            value={toolCalls}
            subtitle="次调用"
            icon={<ToolIcon />}
            color="purple"
          />
          <MetricCard
            title="子智能体"
            value={subagentCalls}
            subtitle="次调用"
            icon={<SubagentIcon />}
            color="green"
          />
          <MetricCard
            title="运行时间"
            value={formatDuration(durationMs)}
            subtitle="总计"
            icon={<DurationIcon />}
            color="orange"
          />
        </div>

        {/* Token Usage Chart */}
        <TokenUsageChart input={tokenCount.input} output={tokenCount.output} />

        {/* Latency Chart */}
        <LatencyChart averageLatency={averageLatency} p95Latency={p95Latency} />

        {/* Summary Stats */}
        <div className="bg-zinc-50 dark:bg-zinc-900/50 rounded-lg p-4 border border-zinc-200 dark:border-zinc-800">
          <h4 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-3">统计摘要</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">平均 Token/调用</span>
              <span className="font-medium text-zinc-900 dark:text-zinc-100">
                {toolCalls > 0 ? formatNumber(Math.round(totalTokens / toolCalls)) : '-'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">调用频率</span>
              <span className="font-medium text-zinc-900 dark:text-zinc-100">
                {durationMs > 0 ? `${((toolCalls + subagentCalls) / (durationMs / 60000)).toFixed(1)}/min` : '-'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Input/Output 比例</span>
              <span className="font-medium text-zinc-900 dark:text-zinc-100">
                {tokenCount.output > 0 ? (tokenCount.input / tokenCount.output).toFixed(2) : '-'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">延迟波动</span>
              <span className="font-medium text-zinc-900 dark:text-zinc-100">
                {averageLatency > 0 ? `${((p95Latency - averageLatency) / averageLatency * 100).toFixed(0)}%` : '-'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
