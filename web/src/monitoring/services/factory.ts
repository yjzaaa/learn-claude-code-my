/**
 * Service Factory
 *
 * 创建监控服务的工厂函数
 */

import { EventDispatcher } from './EventDispatcher';
import { UIStateMachine } from './UIStateMachine';
import { MetricsCollector } from './MetricsCollector';
import { WebSocketEventAdapter } from './WebSocketEventAdapter';

export interface StoreServices {
  dispatcher: EventDispatcher;
  stateMachine: UIStateMachine;
  metricsCollector: MetricsCollector;
  wsAdapter: WebSocketEventAdapter;
}

/**
 * 创建默认服务实例
 */
export function createDefaultServices(dialogId: string): StoreServices {
  // 创建事件分发器
  const dispatcher = new EventDispatcher();

  // 创建状态机
  const stateMachine = new UIStateMachine();

  // 创建指标收集器
  const metricsCollector = new MetricsCollector();

  // 创建 WebSocket 适配器
  // 连接到后端 WebSocket 端点
  const wsAdapter = new WebSocketEventAdapter({
    url: `ws://localhost:8001/ws/monitor-${Date.now()}`,
    dispatcher,
    onStatusChange: (status) => {
      console.log(`[Monitoring WebSocket] Status: ${status}`);
    },
    onError: (error) => {
      console.error('[Monitoring WebSocket] Error:', error);
    },
  });

  // 注意：需要在连接成功后发送订阅消息来接收特定对话的事件
  // 或者后端支持订阅所有对话的事件（通配符）

  return {
    dispatcher,
    stateMachine,
    metricsCollector,
    wsAdapter,
  };
}
