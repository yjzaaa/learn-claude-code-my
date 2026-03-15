/**
 * MonitoringProvider - React Context Provider
 *
 * 提供 MonitoringStore 给 React 组件树
 */

import React, { createContext, useContext, useMemo, useCallback, useEffect } from 'react';
import { useSyncExternalStore } from 'react';
import { MonitoringStore, StateSelector } from '../store';
import { createDefaultServices } from '../services/factory';
import { AgentNode, AgentState, TreeNode } from '../domain';
import { globalEventEmitter } from '@/lib/event-emitter';
import { MonitoringEvent } from '../domain/Event';

// Context
const MonitoringContext = createContext<MonitoringStore | null>(null);

// Provider Props
export interface MonitoringProviderProps {
  children: React.ReactNode;
  dialogId: string;
}

// Provider Component
export function MonitoringProvider({ children, dialogId }: MonitoringProviderProps) {
  const store = useMemo(() => {
    const services = createDefaultServices(dialogId);
    return new MonitoringStore(services);
  }, [dialogId]);

  // 启动 WebSocket 连接
  useEffect(() => {
    store.connect().catch((err) => {
      console.error('[MonitoringProvider] Failed to connect:', err);
    });

    // 监听来自 useWebSocket 的监控事件
    const handleMonitorEvent = (event: unknown) => {
      try {
        console.log('[MonitoringProvider] Received monitor:event from globalEventEmitter:', event);
        const msg = event as Record<string, unknown>;
        if (msg.type?.toString().startsWith('monitor:')) {
          const monitoringEvent = MonitoringEvent.fromWebSocket(msg);
          store.dispatchEvent(monitoringEvent);
        }
      } catch (error) {
        console.error('[MonitoringProvider] Error handling monitor event:', error);
      }
    };

    globalEventEmitter.on('monitor:event', handleMonitorEvent);

    return () => {
      globalEventEmitter.off('monitor:event', handleMonitorEvent);
      store.destroy();
    };
  }, [store]);

  return (
    <MonitoringContext.Provider value={store}>
      {children}
    </MonitoringContext.Provider>
  );
}

/**
 * 获取 MonitoringStore
 */
export function useMonitoringStore(): MonitoringStore {
  const store = useContext(MonitoringContext);
  if (!store) {
    throw new Error('useMonitoringStore must be used within MonitoringProvider');
  }
  return store;
}

/**
 * 创建选择器 Hook 的工厂函数
 *
 * 使用 store.getSnapshot 确保返回缓存值，避免无限重渲染
 */
function createSelectorHook<T>(selector: StateSelector<T>): () => T {
  return function useSelector(): T {
    const store = useMonitoringStore();
    return useSyncExternalStore(
      useCallback((cb) => store.subscribe(selector, cb), [store, selector]),
      useCallback(() => store.getSnapshot(selector), [store, selector]),
      useCallback(() => store.getSnapshot(selector), [store, selector])
    );
  };
}

// ===== 预定义的选择器 Hooks =====

/**
 * 获取 Agent 层级
 */
export const useAgentHierarchy = createSelectorHook(
  (store) => store.getAgentHierarchy()
);

/**
 * 获取 Agent 状态
 */
export const useAgentState = createSelectorHook(
  (store) => store.getAgentState()
);

/**
 * 获取流式内容
 */
export const useStreamingContent = createSelectorHook(
  (store) => store.getStreamingContent()
);

/**
 * 获取活动 Agent ID
 */
export const useActiveAgentId = createSelectorHook(
  (store) => store.getActiveAgentId()
);

/**
 * 获取根 Agent
 */
export const useRootAgent = createSelectorHook(
  (store) => store.getRootAgent()
);

/**
 * 获取活动 Agents
 */
export const useActiveAgents = createSelectorHook(
  (store) => store.getActiveAgents()
);

/**
 * 获取指标报告
 */
export const useMetricsReport = createSelectorHook(
  (store) => store.getMetricsReport()
);

/**
 * 获取所有事件
 */
export const useAllEvents = createSelectorHook(
  (store) => store.getAllEvents()
);

/**
 * 获取自定义选择器（用于复杂场景）
 *
 * 使用 store.getSnapshot 确保返回缓存值，避免无限重渲染
 */
export function useMonitoringSelector<T>(selector: StateSelector<T>): T {
  const store = useMonitoringStore();
  return useSyncExternalStore(
    useCallback((cb) => store.subscribe(selector, cb), [store, selector]),
    useCallback(() => store.getSnapshot(selector), [store, selector]),
    useCallback(() => store.getSnapshot(selector), [store, selector])
  );
}
