/**
 * TypeScript 类型定义
 */

// 重新导出 store 中的类型
export type { Message, Dialog } from '../stores/dialog';
export type { Theme, FontMode, LayoutMode } from '../stores/ui';
export type { WSMessage } from '../stores/websocket';

// HITL 相关类型
export interface SkillEditProposal {
  approval_id: string;
  dialog_id: string;
  path: string;
  old_content: string;
  new_content: string;
  unified_diff: string;
  reason: string;
  status: 'pending' | 'accepted' | 'rejected' | 'edited_accepted';
  created_at: string;
}

export interface TodoItem {
  id: string;
  dialog_id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'done';
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  updated_at: string;
}

// 工具相关类型
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResult {
  tool_call_id: string;
  name: string;
  output: unknown;
  error?: string;
}

// Agent 配置
export interface AgentConfig {
  model: string;
  temperature?: number;
  max_tokens?: number;
  thinking_level?: 'none' | 'brief' | 'full';
}

// 系统事件
export interface SystemEvent {
  type: string;
  timestamp: string;
  payload: unknown;
}
