"use client";

/**
 * useWebSocketWithReady - 带连接就绪状态的 WebSocket Hook
 * 
 * 确保 WebSocket 连接并发送 subscribe 后才允许发送消息
 */

import { useState, useEffect, useCallback, useRef } from "react";

interface UseWebSocketWithReadyOptions {
  url: string;
  onMessage?: (data: unknown) => void;
  onError?: (error: Event) => void;
}

interface UseWebSocketWithReadyReturn {
  isConnected: boolean;
  isSubscribed: boolean;
  isReady: boolean;  // 连接并订阅完成
  send: (data: unknown) => void;
  subscribe: (dialogId: string) => void;
}

export function useWebSocketWithReady(
  options: UseWebSocketWithReadyOptions
): UseWebSocketWithReadyReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingSubscribes = useRef<string[]>([]);

  useEffect(() => {
    const ws = new WebSocket(options.url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WebSocket] Connected");
      setIsConnected(true);
      // 发送等待中的 subscribe
      pendingSubscribes.current.forEach((dialogId) => {
        ws.send(JSON.stringify({ type: "subscribe", dialog_id: dialogId }));
      });
      pendingSubscribes.current = [];
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "dialog:snapshot") {
        setIsSubscribed(true);
      }
      options.onMessage?.(data);
    };

    ws.onerror = (error) => {
      console.error("[WebSocket] Error:", error);
      options.onError?.(error);
    };

    ws.onclose = () => {
      console.log("[WebSocket] Closed");
      setIsConnected(false);
      setIsSubscribed(false);
    };

    return () => {
      ws.close();
    };
  }, [options.url]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn("[WebSocket] Not connected, message dropped");
    }
  }, []);

  const subscribe = useCallback((dialogId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "subscribe", dialog_id: dialogId }));
    } else {
      pendingSubscribes.current.push(dialogId);
    }
  }, []);

  return {
    isConnected,
    isSubscribed,
    isReady: isConnected && isSubscribed,
    send,
    subscribe,
  };
}
