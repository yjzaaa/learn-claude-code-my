"use client";

/**
 * useWebSocketBase - WebSocket 基础连接 Hook
 *
 * 提供低层次的 WebSocket 连接管理：
 * - 连接建立和断开
 * - 自动重连
 * - 消息接收和发送
 * - 连接状态管理
 *
 * 不包含业务逻辑，纯连接层抽象。
 */

import { useState, useEffect, useCallback, useRef } from "react";

// WebSocket URL - 优先使用环境变量，否则使用默认值
const WS_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws/client-1"
    : "ws://localhost:8001/ws/client-1";

export interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

export interface UseWebSocketBaseReturn {
  /** WebSocket 实例（只读） */
  ws: WebSocket | null;
  /** 连接状态 */
  isConnected: boolean;
  /** 连接错误 */
  error: Error | null;
  /** 手动连接 */
  connect: () => void;
  /** 手动断开 */
  disconnect: () => void;
  /** 发送消息 */
  send: (message: WebSocketMessage) => boolean;
  /** 订阅消息 */
  onMessage: (handler: (message: WebSocketMessage) => void) => () => void;
}

/**
 * WebSocket 基础 Hook
 *
 * @param autoConnect 是否自动连接，默认为 true
 * @param reconnectInterval 重连间隔（毫秒），默认为 3000
 */
export function useWebSocketBase(
  autoConnect = true,
  reconnectInterval = 3000
): UseWebSocketBaseReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const activeConnIdRef = useRef<number>(0);
  const messageHandlersRef = useRef<Set<(message: WebSocketMessage) => void>>(new Set());

  // 清理函数
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // 断开连接
  const disconnect = useCallback(() => {
    cleanup();
    if (wsRef.current) {
      // 增加连接 ID 使旧连接的事件被丢弃
      activeConnIdRef.current++;
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, [cleanup]);

  // 建立连接
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    cleanup();
    setError(null);

    try {
      const connId = ++activeConnIdRef.current;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (connId !== activeConnIdRef.current) return;
        setIsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        if (connId !== activeConnIdRef.current) return;
        try {
          const msg = JSON.parse(event.data) as WebSocketMessage;
          // 广播给所有订阅者
          messageHandlersRef.current.forEach((handler) => {
            try {
              handler(msg);
            } catch (e) {
              console.error("[WebSocketBase] Message handler error:", e);
            }
          });
        } catch (e) {
          console.error("[WebSocketBase] Failed to parse message:", e);
        }
      };

      ws.onclose = () => {
        if (connId !== activeConnIdRef.current) return;
        setIsConnected(false);
        wsRef.current = null;

        // 自动重连
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      };

      ws.onerror = (event) => {
        if (connId !== activeConnIdRef.current) return;
        setError(new Error("WebSocket connection error"));
        console.error("[WebSocketBase] Connection error:", event);
      };
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
      console.error("[WebSocketBase] Failed to connect:", e);
    }
  }, [cleanup, reconnectInterval]);

  // 发送消息
  const send = useCallback((message: WebSocketMessage): boolean => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message));
        return true;
      } catch (e) {
        console.error("[WebSocketBase] Failed to send message:", e);
        return false;
      }
    }
    return false;
  }, []);

  // 订阅消息
  const onMessage = useCallback((handler: (message: WebSocketMessage) => void): (() => void) => {
    messageHandlersRef.current.add(handler);
    return () => {
      messageHandlersRef.current.delete(handler);
    };
  }, []);

  // 自动连接
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    ws: wsRef.current,
    isConnected,
    error,
    connect,
    disconnect,
    send,
    onMessage,
  };
}
