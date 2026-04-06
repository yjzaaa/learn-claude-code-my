"use client";

import { useState, useCallback, useRef } from "react";
import { globalEventEmitter } from "@/lib/event-emitter";
import type { ChatMessage, ChatRole } from "@/types/openai";
import type { SkillEditApproval } from "@/types/dialog";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// WebSocket URL
const WS_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws/client-1"
    : "ws://localhost:8001/ws/client-1";

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
}

export interface Dialog {
  id: string;
  title: string;
  messages: ChatMessage[];
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Skill {
  name: string;
  description: string;
  tags: string;
  path: string;
}

export function useAgentApi() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const REQUEST_TIMEOUT_MS = 8000;
  const MAX_WS_WAIT_MS = 5000; // 最大等待 WebSocket 就绪时间

  // WebSocket 引用
  const wsRef = useRef<WebSocket | null>(null);
  const isSubscribedRef = useRef(false);
  const pendingDialogIdRef = useRef<string | null>(null);

  // 确保 WebSocket 连接并订阅
  const ensureWebSocketReady = useCallback(async (dialogId: string): Promise<boolean> => {
    return new Promise((resolve) => {
      // 检查现有连接
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        // 如果已经订阅了这个 dialog，直接返回
        if (isSubscribedRef.current && pendingDialogIdRef.current === dialogId) {
          console.log("[useAgentApi] WebSocket already ready for dialog:", dialogId);
          resolve(true);
          return;
        }
        // 发送 subscribe
        wsRef.current.send(JSON.stringify({ type: "subscribe", dialog_id: dialogId }));
        pendingDialogIdRef.current = dialogId;
      } else {
        // 创建新连接
        console.log("[useAgentApi] Creating new WebSocket connection");
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;
        pendingDialogIdRef.current = dialogId;

        ws.onopen = () => {
          console.log("[useAgentApi] WebSocket connected, subscribing to:", dialogId);
          ws.send(JSON.stringify({ type: "subscribe", dialog_id: dialogId }));
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            // 收到 snapshot 表示订阅成功
            if (msg.type === "dialog:snapshot" && msg.dialog_id === dialogId) {
              console.log("[useAgentApi] Subscribed successfully to:", dialogId);
              isSubscribedRef.current = true;
              resolve(true);
            }
          } catch (e) {
            console.error("[useAgentApi] Failed to parse message:", e);
          }
        };

        ws.onerror = (error) => {
          console.error("[useAgentApi] WebSocket error:", error);
          resolve(false);
        };

        ws.onclose = () => {
          console.log("[useAgentApi] WebSocket closed");
          isSubscribedRef.current = false;
          wsRef.current = null;
        };
      }

      // 超时处理
      setTimeout(() => {
        if (!isSubscribedRef.current || pendingDialogIdRef.current !== dialogId) {
          console.warn("[useAgentApi] WebSocket ready timeout");
          resolve(false);
        }
      }, MAX_WS_WAIT_MS);
    });
  }, []);

  // 通用请求方法
  const request = useCallback(
    async <T>(
      endpoint: string,
      options: RequestInit = {},
    ): Promise<ApiResponse<T>> => {
      setIsLoading(true);
      setError(null);

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(
          () => controller.abort(),
          REQUEST_TIMEOUT_MS,
        );

        let response: Response;
        try {
          response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            signal: controller.signal,
            headers: {
              "Content-Type": "application/json",
              ...options.headers,
            },
          });
        } finally {
          clearTimeout(timeoutId);
        }

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`,
          );
        }

        const data = await response.json();
        return data;
      } catch (err: any) {
        const errorMessage =
          err?.name === "AbortError"
            ? "Request timeout: backend did not respond"
            : err.message || "Request failed";
        setError(errorMessage);
        return { success: false, message: errorMessage };
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  // ========== 对话框 API ==========

  const getDialogs = useCallback(async (): Promise<ApiResponse<Dialog[]>> => {
    return request("/api/dialogs");
  }, [request]);

  const createDialog = useCallback(
    async (title: string = "New Dialog"): Promise<ApiResponse<Dialog>> => {
      return request("/api/dialogs", {
        method: "POST",
        body: JSON.stringify({ title }),
      });
    },
    [request],
  );

  const getDialog = useCallback(
    async (dialogId: string): Promise<ApiResponse<Dialog>> => {
      return request(`/api/dialogs/${dialogId}`);
    },
    [request],
  );

  const deleteDialog = useCallback(
    async (dialogId: string): Promise<ApiResponse<void>> => {
      return request(`/api/dialogs/${dialogId}`, {
        method: "DELETE",
      });
    },
    [request],
  );

  const getMessages = useCallback(
    async (dialogId: string): Promise<ApiResponse<any[]>> => {
      return request(`/api/dialogs/${dialogId}/messages`);
    },
    [request],
  );

  const sendMessage = useCallback(
    async (
      dialogId: string,
      content: string,
    ): Promise<ApiResponse<{ message_id: string; status: string }>> => {
      console.log("[useAgentApi] sendMessage called:", { dialogId, content });

      // 【关键】确保 WebSocket 就绪后再发送 HTTP 请求
      console.log("[useAgentApi] Ensuring WebSocket ready...");
      const wsReady = await ensureWebSocketReady(dialogId);
      if (!wsReady) {
        console.warn("[useAgentApi] WebSocket not ready, proceeding anyway");
      } else {
        // 额外等待一小段时间确保后端 subscribe 完成
        await new Promise(resolve => setTimeout(resolve, 300));
      }

      console.log("[useAgentApi] Sending HTTP request...");
      const result = await request<{ message_id: string; status: string }>(
        `/api/dialogs/${dialogId}/messages`,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        },
      );
      console.log("[useAgentApi] sendMessage result:", result);

      // 发射本地事件，用于UI更新
      if (result.success) {
        globalEventEmitter.emit("message:sent", { dialogId, content });
      }

      return result;
    },
    [request, ensureWebSocketReady],
  );

  // ========== Skills API ==========

  const getSkills = useCallback(async (): Promise<ApiResponse<Skill[]>> => {
    return request("/api/skills");
  }, [request]);

  const getSkill = useCallback(
    async (
      skillName: string,
    ): Promise<ApiResponse<{ name: string; content: string }>> => {
      return request(`/api/skills/${skillName}`);
    },
    [request],
  );

  const loadSkill = useCallback(
    async (
      skillName: string,
    ): Promise<ApiResponse<{ name: string; content: string }>> => {
      return request(`/api/skills/${skillName}/load`, {
        method: "POST",
      });
    },
    [request],
  );

  const updateSkill = useCallback(
    async (
      skillName: string,
      data: {
        old_text?: string;
        new_text?: string;
        full_content?: string;
        reason?: string;
      },
    ): Promise<ApiResponse<{ message: string }>> => {
      return request(`/api/skills/${skillName}/update`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    [request],
  );

  // ========== Agent 控制 API ==========

  const getAgentStatus = useCallback(async (): Promise<
    ApiResponse<{
      active_dialogs: Array<{
        dialog_id: string;
        status: string;
      }>;
      total_dialogs: number;
    }>
  > => {
    return request("/api/agent/status");
  }, [request]);

  const stopAgent = useCallback(async (): Promise<
    ApiResponse<{ stopped_dialogs: string[]; count: number }>
  > => {
    return request("/api/agent/stop", {
      method: "POST",
    });
  }, [request]);

  const resumeDialog = useCallback(
    async (
      dialogId: string,
    ): Promise<
      ApiResponse<{ dialog_id: string; status: string; message?: string }>
    > => {
      return request(`/api/dialogs/${dialogId}/resume`, {
        method: "POST",
      });
    },
    [request],
  );

  const getPendingSkillEdits = useCallback(
    async (dialogId?: string): Promise<ApiResponse<SkillEditApproval[]>> => {
      const query = dialogId
        ? `/api/skill-edits/pending?dialog_id=${encodeURIComponent(dialogId)}`
        : "/api/skill-edits/pending";
      return request(query);
    },
    [request],
  );

  const decideSkillEdit = useCallback(
    async (
      approvalId: string,
      decision: "accept" | "reject" | "edit_accept",
      editedContent?: string,
    ): Promise<ApiResponse<{ approval_id: string; status: string }>> => {
      return request(`/api/skill-edits/${approvalId}/decision`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          edited_content: editedContent,
        }),
      });
    },
    [request],
  );

  return {
    isLoading,
    error,
    // 对话框
    getDialogs,
    createDialog,
    getDialog,
    deleteDialog,
    getMessages,
    sendMessage,
    // Skills
    getSkills,
    getSkill,
    loadSkill,
    updateSkill,
    // Agent
    getAgentStatus,
    stopAgent,
    resumeDialog,
    // Skill Edit HITL
    getPendingSkillEdits,
    decideSkillEdit,
  };
}
