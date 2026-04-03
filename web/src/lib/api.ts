/**
 * API Client
 * 与后端 FastAPI 服务通信
 */

import { type Dialog } from '../stores/dialog-store';
import { type Message } from '../stores/message-store';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new APIError(response.status, error || `HTTP ${response.status}`);
  }

  const json = await response.json();
  // 解包后端 {success, data} 包装格式
  return (json?.data !== undefined ? json.data : json) as T;
}

/** 将后端 snake_case Dialog 快照映射为前端 camelCase Dialog */
function mapDialog(raw: Record<string, unknown>): Dialog {
  return {
    id: raw.id as string,
    title: raw.title as string,
    createdAt: (raw.created_at ?? raw.createdAt ?? new Date().toISOString()) as string,
    updatedAt: (raw.updated_at ?? raw.updatedAt ?? new Date().toISOString()) as string,
    metadata: raw.metadata as Dialog['metadata'],
  };
}

function mapMessage(raw: Record<string, unknown>): Message {
  return {
    id: raw.id as string,
    role: raw.role as Message['role'],
    content: (raw.content ?? '') as string,
    timestamp: (raw.timestamp ?? new Date().toISOString()) as string,
    status: (raw.status as Message['status']) ?? 'completed',
    metadata: raw.metadata as Message['metadata'],
  };
}

export const api = {
  // Dialog APIs
  async createDialog(title?: string): Promise<Dialog> {
    const raw = await fetchApi<Record<string, unknown>>('/api/dialogs', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
    return mapDialog(raw);
  },

  async listDialogs(): Promise<Dialog[]> {
    const raw = await fetchApi<Record<string, unknown>[]>('/api/dialogs');
    return raw.map(mapDialog);
  },

  async getDialog(id: string): Promise<Dialog & { messages: Message[] }> {
    const raw = await fetchApi<Record<string, unknown>>(`/api/dialogs/${id}`);
    return {
      ...mapDialog(raw),
      messages: ((raw.messages ?? []) as Record<string, unknown>[]).map(mapMessage),
    };
  },

  async deleteDialog(id: string): Promise<void> {
    await fetchApi(`/api/dialogs/${id}`, { method: 'DELETE' });
  },

  async updateDialog(id: string, updates: Partial<Dialog>): Promise<Dialog> {
    const raw = await fetchApi<Record<string, unknown>>(`/api/dialogs/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
    return mapDialog(raw);
  },

  // Message APIs — 发送后通过 WebSocket 接收流式更新
  async sendMessage(
    dialogId: string,
    content: string,
  ): Promise<{ message_id: string; status: string }> {
    return fetchApi(`/api/dialogs/${dialogId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },

  // Health check
  async health(): Promise<{ status: string }> {
    return fetchApi<{ status: string }>('/health');
  },
};
