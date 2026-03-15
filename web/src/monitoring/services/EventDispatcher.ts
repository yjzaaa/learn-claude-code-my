/**
 * EventDispatcher - 事件分发器
 *
 * 前端事件分发服务，类似于后端的 EventBus
 */

import { MonitoringEvent, EventType } from '../domain/Event';

export interface EventObserver {
  onEvent(event: MonitoringEvent): void;
}

export interface EventHandler {
  canHandle(event: MonitoringEvent): boolean;
  handle(event: MonitoringEvent): void;
}

export class EventDispatcher {
  private _observers: Map<string, EventObserver[]>;
  private _globalObservers: EventObserver[];
  private _handlers: EventHandler[];

  constructor() {
    this._observers = new Map();
    this._globalObservers = [];
    this._handlers = [];
  }

  /**
   * 分发事件
   */
  dispatch(event: MonitoringEvent): void {
    // 1. 特定类型的观察者
    const typeObservers = this._observers.get(event.type);
    if (typeObservers) {
      for (const observer of typeObservers) {
        try {
          observer.onEvent(event);
        } catch (error) {
          console.error('[EventDispatcher] Observer error:', error);
        }
      }
    }

    // 2. 全局观察者
    for (const observer of this._globalObservers) {
      try {
        observer.onEvent(event);
      } catch (error) {
        console.error('[EventDispatcher] Global observer error:', error);
      }
    }

    // 3. 处理器路由
    for (const handler of this._handlers) {
      try {
        if (handler.canHandle(event)) {
          handler.handle(event);
        }
      } catch (error) {
        console.error('[EventDispatcher] Handler error:', error);
      }
    }
  }

  /**
   * 订阅事件
   */
  subscribe(observer: EventObserver, eventType?: EventType): void {
    if (eventType) {
      if (!this._observers.has(eventType)) {
        this._observers.set(eventType, []);
      }
      this._observers.get(eventType)!.push(observer);
    } else {
      this._globalObservers.push(observer);
    }
  }

  /**
   * 取消订阅
   */
  unsubscribe(observer: EventObserver, eventType?: EventType): boolean {
    if (eventType) {
      const observers = this._observers.get(eventType);
      if (observers) {
        const index = observers.indexOf(observer);
        if (index >= 0) {
          observers.splice(index, 1);
          return true;
        }
      }
    } else {
      const index = this._globalObservers.indexOf(observer);
      if (index >= 0) {
        this._globalObservers.splice(index, 1);
        return true;
      }
    }
    return false;
  }

  /**
   * 添加处理器
   */
  addHandler(handler: EventHandler): void {
    this._handlers.push(handler);
  }

  /**
   * 移除处理器
   */
  removeHandler(handler: EventHandler): boolean {
    const index = this._handlers.indexOf(handler);
    if (index >= 0) {
      this._handlers.splice(index, 1);
      return true;
    }
    return false;
  }

  /**
   * 获取统计信息
   */
  getStats(): {
    typedObservers: Record<string, number>;
    globalObservers: number;
    handlers: number;
  } {
    const typedObservers: Record<string, number> = {};
    this._observers.forEach((observers, type) => {
      typedObservers[type] = observers.length;
    });

    return {
      typedObservers,
      globalObservers: this._globalObservers.length,
      handlers: this._handlers.length,
    };
  }
}
