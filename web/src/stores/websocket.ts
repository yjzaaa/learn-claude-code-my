/**
 * WebSocket Store - WebSocket 连接状态管理
 * 处理与后端 Agent Engine 的实时通信
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export interface WSMessage {
  type: string;
  payload: unknown;
  timestamp?: string;
}

interface WSState {
  // 连接状态
  socket: WebSocket | null;
  isConnected: boolean;
  isConnecting: boolean;
  reconnectAttempts: number;
  lastError: string | null;
  
  // 消息队列（离线时缓存）
  messageQueue: WSMessage[];
  
  // 最后收到的消息
  lastMessage: WSMessage | null;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  send: (message: WSMessage) => void;
  reconnect: () => void;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

export const useWebSocketStore = create<WSState>()(
  immer((set, get) => ({
    socket: null,
    isConnected: false,
    isConnecting: false,
    reconnectAttempts: 0,
    lastError: null,
    messageQueue: [],
    lastMessage: null,

    connect: () => {
      const state = get();
      if (state.isConnected || state.isConnecting) return;

      set((s) => {
        s.isConnecting = true;
        s.lastError = null;
      });

      try {
        const socket = new WebSocket(WS_URL);

        socket.onopen = () => {
          set((s) => {
            s.socket = socket;
            s.isConnected = true;
            s.isConnecting = false;
            s.reconnectAttempts = 0;
          });

          // 发送队列中的消息
          const queue = get().messageQueue;
          queue.forEach((msg) => {
            socket.send(JSON.stringify(msg));
          });
          set((s) => {
            s.messageQueue = [];
          });
        };

        socket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WSMessage;
            set((s) => {
              s.lastMessage = message;
            });
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        socket.onclose = () => {
          set((s) => {
            s.socket = null;
            s.isConnected = false;
            s.isConnecting = false;
          });

          // 自动重连
          const attempts = get().reconnectAttempts;
          if (attempts < MAX_RECONNECT_ATTEMPTS) {
            setTimeout(() => {
              set((s) => {
                s.reconnectAttempts = attempts + 1;
              });
              get().connect();
            }, RECONNECT_DELAY * (attempts + 1));
          }
        };

        socket.onerror = (error) => {
          set((s) => {
            s.lastError = 'WebSocket connection error';
            s.isConnecting = false;
          });
        };
      } catch (err) {
        set((s) => {
          s.lastError = err instanceof Error ? err.message : 'Failed to connect';
          s.isConnecting = false;
        });
      }
    },

    disconnect: () => {
      const { socket } = get();
      if (socket) {
        socket.close();
      }
      set((s) => {
        s.socket = null;
        s.isConnected = false;
        s.isConnecting = false;
      });
    },

    send: (message) => {
      const { socket, isConnected } = get();
      
      if (isConnected && socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(message));
      } else {
        // 离线时缓存消息
        set((s) => {
          s.messageQueue.push(message);
        });
      }
    },

    reconnect: () => {
      get().disconnect();
      set((s) => {
        s.reconnectAttempts = 0;
      });
      get().connect();
    },
  }))
);
