/**
 * SimpleMonitor - 简单监控面板
 *
 * 最小实现，用于验证端到端数据流
 */

import React, { useEffect, useState } from 'react';
import {
  MonitoringProvider,
  useAgentState,
  useStreamingContent,
  useAllEvents,
  useAgentHierarchy,
} from '@/monitoring';

// 事件列表组件
function EventList() {
  const events = useAllEvents();

  return (
    <div className="border rounded p-4 h-64 overflow-auto bg-gray-50">
      <h3 className="font-bold mb-2">Events ({events.length})</h3>
      {events.map((event, i) => (
        <div key={i} className="text-xs mb-1 p-1 bg-white rounded border">
          <span className="text-blue-600">{event.type}</span>
          <span className="text-gray-500 ml-2">{event.source}</span>
        </div>
      ))}
    </div>
  );
}

// 状态显示组件
function StateDisplay() {
  const state = useAgentState();
  const { content, reasoning } = useStreamingContent();

  return (
    <div className="border rounded p-4 mb-4">
      <h3 className="font-bold mb-2">Current State</h3>
      <div className="text-lg font-mono text-green-600">{state}</div>
      {content && (
        <div className="mt-2">
          <div className="text-sm text-gray-500">Content:</div>
          <div className="text-sm bg-gray-100 p-2 rounded">{content}</div>
        </div>
      )}
      {reasoning && (
        <div className="mt-2">
          <div className="text-sm text-gray-500">Reasoning:</div>
          <div className="text-sm bg-yellow-50 p-2 rounded">{reasoning}</div>
        </div>
      )}
    </div>
  );
}

// 层级显示组件
function HierarchyDisplay() {
  const hierarchy = useAgentHierarchy();

  const renderNode = (node: any, depth = 0) => (
    <div key={node.data.id} style={{ marginLeft: depth * 20 }} className="mb-1">
      <div className="flex items-center gap-2 p-2 bg-blue-50 rounded">
        <span className="font-medium">{node.data.name}</span>
        <span className="text-xs text-gray-500">({node.data.status})</span>
      </div>
      {node.children.map((child: any) => renderNode(child, depth + 1))}
    </div>
  );

  return (
    <div className="border rounded p-4">
      <h3 className="font-bold mb-2">Agent Hierarchy</h3>
      {hierarchy ? renderNode(hierarchy) : <div className="text-gray-400">No agents yet</div>}
    </div>
  );
}

// 监控面板
function MonitorPanel() {
  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Agent Monitor</h2>
      <StateDisplay />
      <div className="grid grid-cols-2 gap-4">
        <EventList />
        <HierarchyDisplay />
      </div>
    </div>
  );
}

// 带 Provider 的导出
export default function SimpleMonitor({ dialogId }: { dialogId: string }) {
  return (
    <MonitoringProvider dialogId={dialogId}>
      <MonitorPanel />
    </MonitoringProvider>
  );
}
