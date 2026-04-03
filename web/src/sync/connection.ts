/**
 * WebSocket Connection Manager
 *
 * 管理 WebSocket 连接生命周期、重连机制和心跳
 */

import { useSyncStore, type ConnectionStatus } from '@/stores/sync-store';
import type { ClientRequest, ServerResponse } from '@/types/sync';

type MessageHandler = (message: ServerResponse) => void;
type StatusChangeHandler = (previous: ConnectionStatus, current: ConnectionStatus) => void;
type ErrorHandler = (error: Error) => void;

interface ConnectionConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

export class ConnectionManager {
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = 'disconnected';
  private reconnectAttempts = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private config: Required<ConnectionConfig>;

  private messageHandlers: Set<MessageHandler> = new Set();
  private statusChangeHandlers: Set<StatusChangeHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();

  constructor(config: ConnectionConfig) {
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      ...config,
    };
  }

  // 事件监听
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatusChange(handler: StatusChangeHandler): () => void {
    this.statusChangeHandlers.add(handler);
    return () => this.statusChangeHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  // 连接管理
  connect(): void {
    if (this.status === 'connected' || this.status === 'connecting') return;

    this.setStatus('connecting');

    try {
      this.ws = new WebSocket(this.config.url);

      this.ws.onopen = () => {
        this.setStatus('connected');
        this.reconnectAttempts = 0;
        useSyncStore.getState().resetReconnectAttempt();
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerResponse;
          this.handleMessage(message);
        } catch (err) {
          this.emitError(err as Error);
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.setStatus('disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = () => {
        this.emitError(new Error('WebSocket error'));
      };
    } catch (err) {
      this.setStatus('error');
      this.emitError(err as Error);
    }
  }

  disconnect(): void {
    this.stopHeartbeat();
    this.ws?.close();
    this.ws = null;
    this.setStatus('disconnected');
  }

  send(message: ClientRequest): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  isConnected(): boolean {
    return this.status === 'connected';
  }

  // 私有方法
  private setStatus(status: ConnectionStatus): void {
    const previous = this.status;
    this.status = status;
    useSyncStore.getState().setConnectionStatus(status);

    for (const handler of this.statusChangeHandlers) {
      handler(previous, status);
    }
  }

  private handleMessage(message: ServerResponse): void {
    // 处理 pong
    if (message.type === 'pong') {
      useSyncStore.getState().setLastPingAt(Date.now());
      return;
    }

    for (const handler of this.messageHandlers) {
      handler(message);
    }
  }

  private emitError(error: Error): void {
    for (const handler of this.errorHandlers) {
      handler(error);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.setStatus('error');
      return;
    }

    this.setStatus('reconnecting');
    this.reconnectAttempts++;
    useSyncStore.getState().incrementReconnectAttempt();

    setTimeout(() => {
      this.connect();
    }, this.config.reconnectInterval * this.reconnectAttempts);
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' });
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

// 单例实例
let connectionManagerInstance: ConnectionManager | null = null;

export function getConnectionManager(config?: ConnectionConfig): ConnectionManager {
  if (!connectionManagerInstance && config) {
    connectionManagerInstance = new ConnectionManager(config);
  }
  if (!connectionManagerInstance) {
    throw new Error('ConnectionManager not initialized');
  }
  return connectionManagerInstance;
}

export function createConnectionManager(config: ConnectionConfig): ConnectionManager {
  connectionManagerInstance = new ConnectionManager(config);
  return connectionManagerInstance;
}
