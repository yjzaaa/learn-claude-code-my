/**
 * Monitoring Services
 *
 * 核心服务
 */

export {
  EventDispatcher,
  type EventObserver,
  type EventHandler,
} from './EventDispatcher';

export {
  UIStateMachine,
  type StateTransition,
} from './UIStateMachine';

export {
  MetricsCollector,
  type MetricsReport,
} from './MetricsCollector';

export {
  WebSocketEventAdapter,
  type ConnectionStatus,
  type WebSocketEventAdapterOptions,
} from './WebSocketEventAdapter';
