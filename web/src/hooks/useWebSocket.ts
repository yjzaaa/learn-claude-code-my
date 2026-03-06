"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { globalEventEmitter } from "@/lib/event-emitter";
import type {
  WebSocketMessage,
  StreamTokenMessage,
  MessageAddedEvent,
  MessageUpdatedEvent,
  DialogSubscribedEvent,
} from "@/types/realtime-message";

export type WebSocketStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

interface UseWebSocketOptions {
  url?: string;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

// 全局WebSocket状态（避免React StrictMode重复创建连接）
const globalWsRef = { current: null as WebSocket | null };
const globalClientId = { current: "" };
const subscribedDialogs = new Set<string>();

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws",
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>(
    globalWsRef.current?.readyState === WebSocket.OPEN
      ? "connected"
      : "disconnected",
  );
  const [error, setError] = useState<string | null>(null);

  const wsRef = globalWsRef;
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const clientIdRef = globalClientId;
  const optionsRef = useRef(options);
  const isConnectingRef = useRef(false);
  const mountedRef = useRef(true);
  const subscribedDialogsRef = useRef(subscribedDialogs);

  // Update options ref when they change
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  // Generate client ID once
  if (!clientIdRef.current) {
    clientIdRef.current = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      isConnectingRef.current
    ) {
      return;
    }

    isConnectingRef.current = true;
    setStatus("connecting");
    setError(null);

    const fullUrl = `${url}/${clientIdRef.current}`;
    console.log("[WebSocket] Connecting to:", fullUrl);

    try {
      const ws = new WebSocket(fullUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        isConnectingRef.current = false;
        setStatus("connected");
        reconnectAttemptsRef.current = 0;
        optionsRef.current.onConnect?.();
        globalEventEmitter.emit("websocket:connected");
        console.log("[WebSocket] Connected successfully");

        // 恢复之前的订阅
        subscribedDialogsRef.current.forEach((dialogId) => {
          console.log(
            "[WebSocket] Restoring subscription to dialog:",
            dialogId,
          );
          ws.send(
            JSON.stringify({
              type: "subscribe_dialog",
              dialog_id: dialogId,
            }),
          );
        });
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log("[WebSocket] Message received:", message.type, message);

          globalEventEmitter.emit("websocket:message", message);
          globalEventEmitter.emit(`websocket:${message.type}`, message);

          switch (message.type) {
            case "stream_token":
              globalEventEmitter.emit(
                "stream:token",
                message as StreamTokenMessage,
              );
              break;
            case "message_added":
              console.log("[WebSocket] Emitting message:added");
              globalEventEmitter.emit(
                "message:added",
                message as MessageAddedEvent,
              );
              break;
            case "message_updated":
              console.log("[WebSocket] Emitting message:updated");
              globalEventEmitter.emit(
                "message:updated",
                message as MessageUpdatedEvent,
              );
              break;
            case "dialog_subscribed":
              console.log("[WebSocket] Dialog subscribed:", message);
              globalEventEmitter.emit(
                "dialog:subscribed",
                message as DialogSubscribedEvent,
              );
              break;
            case "dialog_created":
              globalEventEmitter.emit("dialog:created", message);
              break;
            case "dialog_deleted":
              globalEventEmitter.emit("dialog:deleted", message);
              break;
          }

          optionsRef.current.onMessage?.(message);
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err);
        }
      };

      ws.onclose = () => {
        isConnectingRef.current = false;
        setStatus("disconnected");
        wsRef.current = null;
        optionsRef.current.onDisconnect?.();
        globalEventEmitter.emit("websocket:disconnected");
        console.log("[WebSocket] Connection closed");

        if (
          autoReconnect &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current++;
          console.log(
            `[WebSocket] Reconnecting... attempt ${reconnectAttemptsRef.current}`,
          );
          reconnectTimerRef.current = setTimeout(() => {
            if (mountedRef.current) {
              connect();
            }
          }, reconnectInterval);
        }
      };

      ws.onerror = (err) => {
        isConnectingRef.current = false;
        setStatus("error");
        setError("WebSocket connection error");
        optionsRef.current.onError?.(err);
        globalEventEmitter.emit("websocket:error", err);
        console.error("[WebSocket] Error:", err);
      };
    } catch (err) {
      isConnectingRef.current = false;
      setStatus("error");
      setError("Failed to create WebSocket connection");
      console.error("[WebSocket] Failed to create connection:", err);
    }
  }, [url, autoReconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const subscribeToDialog = useCallback(
    (dialogId: string) => {
      console.log("[WebSocket] Subscribing to dialog:", dialogId);
      // 记录订阅，以便重连后恢复
      subscribedDialogsRef.current.add(dialogId);
      const result = send({
        type: "subscribe_dialog",
        dialog_id: dialogId,
      });
      console.log("[WebSocket] Subscribe message sent:", result);
      return result;
    },
    [send],
  );

  const unsubscribeFromDialog = useCallback(
    (dialogId: string) => {
      subscribedDialogsRef.current.delete(dialogId);
      return send({
        type: "unsubscribe_dialog",
        dialog_id: dialogId,
      });
    },
    [send],
  );

  const sendPing = useCallback(() => {
    return send({ type: "ping" });
  }, [send]);

  // 组件挂载时确保连接
  useEffect(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connect();
    }
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return {
    status,
    error,
    connect,
    disconnect,
    send,
    subscribeToDialog,
    unsubscribeFromDialog,
    sendPing,
    isConnected: status === "connected",
    isConnecting: status === "connecting",
  };
}
