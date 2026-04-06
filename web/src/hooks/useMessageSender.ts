"use client";

/**
 * useMessageSender - 安全的消息发送 Hook
 * 
 * 确保 WebSocket 就绪后才发送消息
 */

import { useCallback } from "react";
import { useWebSocketWithReady } from "./useWebSocketWithReady";

interface UseMessageSenderOptions {
  dialogId: string;
  onMessage?: (data: unknown) => void;
}

interface UseMessageSenderReturn {
  isReady: boolean;
  sendMessage: (content: string) => Promise<void>;
}

export function useMessageSender(
  options: UseMessageSenderOptions
): UseMessageSenderReturn {
  const ws = useWebSocketWithReady({
    url: `ws://localhost:8001/ws/client-${Date.now()}`,
    onMessage: options.onMessage,
  });

  // 组件挂载时订阅对话
  useEffect(() => {
    if (options.dialogId) {
      ws.subscribe(options.dialogId);
    }
  }, [options.dialogId]);

  const sendMessage = useCallback(
    async (content: string) => {
      // 等待 WebSocket 就绪
      let attempts = 0;
      while (!ws.isReady && attempts < 50) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        attempts++;
      }

      if (!ws.isReady) {
        throw new Error("WebSocket not ready after 5s");
      }

      // 发送 HTTP 请求
      const response = await fetch(
        `/api/dialogs/${options.dialogId}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to send message");
      }
    },
    [options.dialogId, ws.isReady]
  );

  return {
    isReady: ws.isReady,
    sendMessage,
  };
}
