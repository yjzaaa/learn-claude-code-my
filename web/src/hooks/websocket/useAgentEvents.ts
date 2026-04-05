"use client";

/**
 * useAgentEvents - Agent 事件处理 Hook
 *
 * 处理服务端推送的 Agent 相关事件：
 * - dialog:snapshot - 对话快照
 * - stream:delta - 流式内容增量
 * - status:change - 状态变更
 * - agent:tool_call - 工具调用
 * - agent:tool_result - 工具结果
 * - error - 错误事件
 *
 * 以及技能编辑相关事件：
 * - skill_edit:pending
 * - skill_edit:resolved
 * - skill_edit:error
 */

import { useState, useEffect, useCallback } from "react";
import type { DialogSession, DialogSummary, SkillEditApproval } from "@/types/dialog";
import type { ServerPushEvent } from "@/types/agent-events";
import { agentEventBus } from "@/agent/agent-event-bus";
import { useAgentStore } from "@/agent/agent-store";

export interface AgentEventsState {
  /** 当前对话框完整状态快照 */
  currentSnapshot: DialogSession | null;
  /** 历史对话框列表 */
  dialogList: DialogSummary[];
  /** 待审批的技能编辑列表 */
  pendingSkillEdits: SkillEditApproval[];
}

export interface AgentEventsActions {
  /** 处理单个事件 */
  handleEvent: (event: ServerPushEvent) => void;
  /** 清除所有待审批 */
  clearPendingEdits: () => void;
  /** 移除特定审批 */
  removePendingEdit: (approvalId: string) => void;
}

export type UseAgentEventsReturn = AgentEventsState & AgentEventsActions;

/**
 * Agent 事件处理 Hook
 *
 * 订阅 WebSocket 消息并处理 Agent 相关事件。
 * 使用 AgentEventBus 进行事件路由。
 */
export function useAgentEvents(
  onMessage?: (message: unknown) => void
): UseAgentEventsReturn {
  const [pendingSkillEdits, setPendingSkillEdits] = useState<SkillEditApproval[]>([]);

  // 从统一 store 读取状态
  const currentSnapshot = useAgentStore((s) => s.currentSnapshot);
  const dialogList = useAgentStore((s) => s.dialogList);

  // 处理单个事件
  const handleEvent = useCallback((event: ServerPushEvent) => {
    // 技能编辑事件由本地 handler 处理
    if (event.type === "skill_edit:pending") {
      const msg = event as { data: { approval: SkillEditApproval } };
      setPendingSkillEdits((prev) => {
        const exists = prev.find(
          (item) => item.approval_id === msg.data.approval.approval_id
        );
        if (exists) {
          return prev.map((item) =>
            item.approval_id === msg.data.approval.approval_id
              ? msg.data.approval
              : item
          );
        }
        return [msg.data.approval, ...prev];
      });
      return;
    }

    if (event.type === "skill_edit:resolved") {
      const msg = event as { data: { approval_id: string } };
      setPendingSkillEdits((prev) =>
        prev.filter((item) => item.approval_id !== msg.data.approval_id)
      );
      return;
    }

    if (event.type === "skill_edit:error") {
      const msg = event as { data: { error: string } };
      console.error("[AgentEvents] skill_edit:error", msg.data.error);
      return;
    }

    // 其余所有事件统一交给 AgentEventBus
    agentEventBus.handleEvent(event);
  }, []);

  // 清除所有待审批
  const clearPendingEdits = useCallback(() => {
    setPendingSkillEdits([]);
  }, []);

  // 移除特定审批
  const removePendingEdit = useCallback((approvalId: string) => {
    setPendingSkillEdits((prev) =>
      prev.filter((item) => item.approval_id !== approvalId)
    );
  }, []);

  // 监听外部消息
  useEffect(() => {
    if (onMessage) {
      const unsubscribe = agentEventBus.subscribe(onMessage);
      return unsubscribe;
    }
  }, [onMessage]);

  return {
    currentSnapshot,
    dialogList,
    pendingSkillEdits,
    handleEvent,
    clearPendingEdits,
    removePendingEdit,
  };
}
