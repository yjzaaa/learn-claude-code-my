/**
 * Monitoring Dashboard Page
 *
 * 智能体监控仪表板主页面
 */

'use client';

import { useState } from 'react';
import { MonitoringProvider } from '@/monitoring';
import AgentHierarchy from '@/components/monitoring/AgentHierarchy';
import StateMachineViz from '@/components/monitoring/StateMachineViz';
import EventTimeline from '@/components/monitoring/EventTimeline';
import MetricsPanel from '@/components/monitoring/MetricsPanel';
import SimpleMonitor from '@/components/monitoring/SimpleMonitor';

// 标签页类型
type TabType = 'overview' | 'hierarchy' | 'timeline' | 'metrics' | 'debug';

// 监控仪表板内容
function MonitoringDashboardContent() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const tabs: { id: TabType; label: string }[] = [
    { id: 'overview', label: '概览' },
    { id: 'hierarchy', label: '层级' },
    { id: 'timeline', label: '时间线' },
    { id: 'metrics', label: '指标' },
    { id: 'debug', label: '调试' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Agent 监控中心</h1>
            <p className="text-sm text-gray-500 mt-1">
              实时监控智能体执行过程、状态和性能指标
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              运行中
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex gap-1 mt-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Content */}
      <main className="p-6">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-6">
              <StateMachineViz />
              <MetricsPanel />
            </div>
            <div className="space-y-6">
              <AgentHierarchy />
            </div>
          </div>
        )}

        {activeTab === 'hierarchy' && (
          <div className="max-w-4xl">
            <AgentHierarchy />
          </div>
        )}

        {activeTab === 'timeline' && (
          <div className="max-w-6xl">
            <EventTimeline />
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="max-w-4xl">
            <MetricsPanel />
          </div>
        )}

        {activeTab === 'debug' && (
          <div className="max-w-6xl">
            <SimpleMonitor dialogId="debug-dialog" />
          </div>
        )}
      </main>
    </div>
  );
}

// 带 Provider 的页面导出
export default function MonitoringPage() {
  return (
    <MonitoringProvider dialogId="monitoring-dashboard">
      <MonitoringDashboardContent />
    </MonitoringProvider>
  );
}
