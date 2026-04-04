/**
 * Agent Event Bus - 前端唯一事件路由
 *
 * WebSocket 层只负责接收原始事件并调用此 bus，
 * 所有状态变更收敛到 agent-store。
 */

import { useAgentStore } from "./agent-store";
import type { ServerPushEvent } from "@/types/agent-events";

export class AgentEventBus {
  handleEvent(event: ServerPushEvent): void {
    useAgentStore.getState().handleEvent(event);
  }
}

export const agentEventBus = new AgentEventBus();
