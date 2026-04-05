/**
 * Hooks 统一导出
 */

// WebSocket Hooks（新架构）
export {
  useWebSocketBase,
  useAgentEvents,
  type WebSocketMessage,
  type UseWebSocketBaseReturn,
  type AgentEventsState,
  type AgentEventsActions,
  type UseAgentEventsReturn,
} from './websocket';

// 传统 Hooks（保持向后兼容）
export { useWebSocket } from './useWebSocket';
export { useDialog } from './useDialog';
export { useAgentApi } from './useAgentApi';
export { useMessageStore, MessageStoreProvider } from './useMessageStore';
export { useSimulator } from './useSimulator';
export { useSteppedVisualization } from './useSteppedVisualization';
export { useDarkMode, useSvgPalette } from './useDarkMode';
