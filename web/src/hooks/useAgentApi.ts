"use client";

import { useState, useCallback } from "react";
import { globalEventEmitter } from "@/lib/event-emitter";
import type { MessageStatus, RealtimeMessage } from "@/types/realtime-message";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
}

export interface Dialog {
  id: string;
  title: string;
  messages: RealtimeMessage[];
  status: MessageStatus;
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
    [request],
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
      is_running: boolean;
      current_dialog_id: string | null;
      model: string;
    }>
  > => {
    return request("/api/agent/status");
  }, [request]);

  const stopAgent = useCallback(async (): Promise<ApiResponse<void>> => {
    return request("/api/agent/stop", {
      method: "POST",
    });
  }, [request]);

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
  };
}
