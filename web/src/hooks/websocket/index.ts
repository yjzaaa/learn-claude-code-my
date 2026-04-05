/**
 * WebSocket Hooks 统一导出
 *
 * 提供分层的 WebSocket 抽象：
 * - useWebSocketBase: 基础连接层，纯 WebSocket 管理
 * - useAgentEvents: 业务事件层，处理 Agent 相关事件
 *
 * 使用方式：
 * ```tsx
 * // 基础连接
 * const { isConnected, send, onMessage } = useWebSocketBase();
 *
 * // 业务事件
 * const { currentSnapshot, handleEvent } = useAgentEvents();
 * ```
 */

export {
  useWebSocketBase,
  type WebSocketMessage,
  type UseWebSocketBaseReturn,
} from "./useWebSocketBase";

export {
  useAgentEvents,
  type AgentEventsState,
  type AgentEventsActions,
  type UseAgentEventsReturn,
} from "./useAgentEvents";
