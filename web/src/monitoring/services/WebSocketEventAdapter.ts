/**
 * WebSocketEventAdapter - WebSocket 事件适配器
 *
 * 将 WebSocket 消息转换为 MonitoringEvent 并分发
 */

import { MonitoringEvent, EventType } from '../domain/Event';
import { EventDispatcher } from './EventDispatcher';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketEventAdapterOptions {
  url: string;
  dispatcher: EventDispatcher;
  onStatusChange?: (status: ConnectionStatus) => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class WebSocketEventAdapter {
  private _url: string;
  private _dispatcher: EventDispatcher;
  private _ws: WebSocket | null;
  private _status: ConnectionStatus;
  private _onStatusChange?: (status: ConnectionStatus) => void;
  private _onError?: (error: Event) => void;
  private _reconnectInterval: number;
  private _maxReconnectAttempts: number;
  private _reconnectAttempts: number;
  private _reconnectTimer?: number;

  constructor(options: WebSocketEventAdapterOptions) {
    this._url = options.url;
    this._dispatcher = options.dispatcher;
    this._ws = null;
    this._status = 'disconnected';
    this._onStatusChange = options.onStatusChange;
    this._onError = options.onError;
    this._reconnectInterval = options.reconnectInterval ?? 3000;
    this._maxReconnectAttempts = options.maxReconnectAttempts ?? 5;
    this._reconnectAttempts = 0;
  }

  /**
   * 获取连接状态
   */
  getStatus(): ConnectionStatus {
    return this._status;
  }

  /**
   * 连接 WebSocket
   */
  connect(): Promise<void> {
    // 如果 URL 为空，跳过连接
    if (!this._url) {
      console.log('[WebSocketEventAdapter] Empty URL, skipping connection');
      this._setStatus('disconnected');
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      try {
        this._setStatus('connecting');
        this._ws = new WebSocket(this._url);

        this._ws.onopen = () => {
          this._setStatus('connected');
          this._reconnectAttempts = 0;
          resolve();
        };

        this._ws.onmessage = (event) => {
          this._handleMessage(event.data);
        };

        this._ws.onclose = () => {
          this._setStatus('disconnected');
          this._attemptReconnect();
        };

        this._ws.onerror = (error) => {
          this._setStatus('error');
          this._onError?.(error);
          reject(error);
        };
      } catch (error) {
        this._setStatus('error');
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this._reconnectTimer) {
      window.clearTimeout(this._reconnectTimer);
      this._reconnectTimer = undefined;
    }

    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }

    this._setStatus('disconnected');
  }

  /**
   * 发送消息
   */
  send(message: unknown): void {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocketEventAdapter] WebSocket is not open');
    }
  }

  /**
   * 订阅对话事件
   */
  subscribe(dialogId: string): void {
    this.send({
      type: 'subscribe',
      dialog_id: dialogId,
    });
    console.log(`[WebSocketEventAdapter] Subscribed to dialog: ${dialogId}`);
  }

  /**
   * 处理消息
   */
  private _handleMessage(data: string): void {
    try {
      const parsed = JSON.parse(data);

      // 调试日志：显示所有收到的消息类型
      console.log('[WebSocketEventAdapter] Received:', parsed.type, parsed);

      // 只处理监控相关事件
      if (parsed.type?.startsWith('monitor:') ||
          parsed.type?.startsWith('agent:') ||
          parsed.type?.startsWith('todo:') ||
          parsed.type?.startsWith('bg_task:') ||
          parsed.type?.startsWith('subagent:') ||
          parsed.type === 'dialog:snapshot') {
        console.log('[WebSocketEventAdapter] Processing monitoring event:', parsed.type);
        const event = MonitoringEvent.fromWebSocket(parsed);
        this._dispatcher.dispatch(event);
      }
    } catch (error) {
      console.error('[WebSocketEventAdapter] Failed to parse message:', error);
    }
  }

  /**
   * 尝试重连
   */
  private _attemptReconnect(): void {
    if (this._reconnectAttempts >= this._maxReconnectAttempts) {
      console.warn('[WebSocketEventAdapter] Max reconnect attempts reached');
      return;
    }

    this._reconnectAttempts++;

    this._reconnectTimer = window.setTimeout(() => {
      console.log(`[WebSocketEventAdapter] Reconnecting... (attempt ${this._reconnectAttempts})`);
      this.connect().catch(() => {
        // 重连失败，继续尝试
      });
    }, this._reconnectInterval);
  }

  /**
   * 设置状态
   */
  private _setStatus(status: ConnectionStatus): void {
    this._status = status;
    this._onStatusChange?.(status);
  }
}
