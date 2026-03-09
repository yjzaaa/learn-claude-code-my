"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import type { AgentRunReport, HookStats } from "@/types/agent-event";
import { Activity, Braces, Download, Gauge, Wrench } from "lucide-react";
import {
  JsonView,
  collapseAllNested,
  defaultStyles,
  darkStyles,
} from "react-json-view-lite";
import { Tabs } from "@/components/ui/tabs";

interface HookStatsPanelProps {
  hookStats: HookStats | null;
  runReport?: AgentRunReport | null;
  className?: string;
}

function useJsonTheme() {
  return useMemo(
    () =>
      typeof document !== "undefined" &&
      document.documentElement.classList.contains("dark")
        ? darkStyles
        : defaultStyles,
    [],
  );
}

export function HookStatsPanel({
  hookStats,
  runReport = null,
  className,
}: HookStatsPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const jsonStyle = useJsonTheme();

  const resolvedHookStats: HookStats = hookStats ??
    runReport?.hook_stats ?? {
      stream_total: 0,
      content_chunks: 0,
      reasoning_chunks: 0,
      tool_chunks: 0,
      done_chunks: 0,
      error_chunks: 0,
      tool_calls: [],
      complete_payload: "",
      errors: [],
      after_run_rounds: 0,
    };

  const handleExport = () => {
    if (!runReport) return;
    const stamp = new Date().toISOString().replace(/[.:]/g, "-");
    const blob = new Blob([JSON.stringify(runReport, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `hook_report_${stamp}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const metrics = useMemo(() => {
    return [
      { label: "Stream", value: resolvedHookStats.stream_total },
      { label: "Content", value: resolvedHookStats.content_chunks },
      { label: "Tool", value: resolvedHookStats.tool_chunks },
      { label: "Rounds", value: resolvedHookStats.after_run_rounds },
    ];
  }, [resolvedHookStats]);

  return (
    <section
      className={cn(
        "rounded-xl border border-zinc-200 bg-white p-3 shadow-sm",
        "dark:border-zinc-800 dark:bg-zinc-900",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-zinc-900 dark:text-zinc-100">
          <Gauge className="h-4 w-4" />
          <p className="text-sm font-semibold">运行仪表盘</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExport}
            disabled={!runReport}
            className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-zinc-50 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
          >
            <Download className="h-3.5 w-3.5" />
            导出
          </button>
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="rounded-md border border-zinc-300 bg-zinc-50 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
          >
            {expanded ? "收起" : "展开"}
          </button>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-lg border border-zinc-200 bg-zinc-50 px-2.5 py-2 dark:border-zinc-700 dark:bg-zinc-800/60"
          >
            <p className="text-[11px] uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              {metric.label}
            </p>
            <p className="text-base font-semibold text-zinc-800 dark:text-zinc-100">
              {metric.value}
            </p>
          </div>
        ))}
      </div>

      {expanded && (
        <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50/70 p-2 dark:border-zinc-700 dark:bg-zinc-800/30">
          <Tabs
            tabs={[
              { id: "overview", label: "概览" },
              {
                id: "tools",
                label: `工具(${resolvedHookStats.tool_calls.length})`,
              },
              { id: "result", label: "完成内容" },
            ]}
            defaultTab="overview"
          >
            {(activeTab) => {
              if (activeTab === "overview") {
                return (
                  <div className="rounded-md border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900/70">
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300">
                      <Activity className="h-3.5 w-3.5" />
                      Chunk Breakdown
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="rounded border border-zinc-200 p-2 dark:border-zinc-700">
                        <p className="text-zinc-500">Reasoning</p>
                        <p className="mt-1 text-sm font-semibold">
                          {resolvedHookStats.reasoning_chunks}
                        </p>
                      </div>
                      <div className="rounded border border-zinc-200 p-2 dark:border-zinc-700">
                        <p className="text-zinc-500">Done</p>
                        <p className="mt-1 text-sm font-semibold">
                          {resolvedHookStats.done_chunks}
                        </p>
                      </div>
                      <div className="rounded border border-zinc-200 p-2 dark:border-zinc-700">
                        <p className="text-zinc-500">Error</p>
                        <p className="mt-1 text-sm font-semibold">
                          {resolvedHookStats.error_chunks}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              }

              if (activeTab === "tools") {
                return (
                  <div className="space-y-2">
                    {resolvedHookStats.tool_calls.length === 0 ? (
                      <p className="rounded-md border border-zinc-200 bg-white p-3 text-xs text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900/70">
                        暂无工具调用
                      </p>
                    ) : (
                      resolvedHookStats.tool_calls.map((tool, idx) => (
                        <div
                          key={`${tool.name}-${idx}`}
                          className="rounded-md border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900/70"
                        >
                          <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300">
                            <Wrench className="h-3.5 w-3.5" />
                            {tool.name}
                          </div>
                          <JsonView
                            data={tool.arguments || {}}
                            shouldExpandNode={collapseAllNested}
                            style={jsonStyle}
                          />
                        </div>
                      ))
                    )}
                  </div>
                );
              }

              return (
                <div className="space-y-2 rounded-md border border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900/70">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    <Braces className="h-3.5 w-3.5" />
                    Completion Preview
                  </div>
                  <p className="whitespace-pre-wrap text-xs leading-6 text-zinc-700 dark:text-zinc-300">
                    {resolvedHookStats.complete_payload || "(无最终内容)"}
                  </p>
                  {runReport && (
                    <div className="rounded border border-dashed border-zinc-300 p-2 dark:border-zinc-700">
                      <p className="mb-2 text-[11px] text-zinc-500">
                        Report Snapshot
                      </p>
                      <JsonView
                        data={{
                          messageCount: runReport.messages.length,
                          resultLength: runReport.result?.length || 0,
                          rounds: resolvedHookStats.after_run_rounds,
                        }}
                        shouldExpandNode={collapseAllNested}
                        style={jsonStyle}
                      />
                    </div>
                  )}
                </div>
              );
            }}
          </Tabs>
        </div>
      )}
    </section>
  );
}
