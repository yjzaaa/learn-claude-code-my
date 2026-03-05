/**
 * 事件发射器 - 实现发布订阅模式 (Observer Pattern)
 *
 * 用于前端组件间的解耦通信
 */

type EventCallback<T = any> = (data: T) => void;

interface EventSubscription {
  event: string;
  callback: EventCallback;
}

export class EventEmitter {
  private subscribers: Map<string, Set<EventCallback>> = new Map();

  /**
   * 订阅事件
   * @param event 事件名称
   * @param callback 回调函数
   * @returns 取消订阅函数
   */
  on<T = any>(event: string, callback: EventCallback<T>): () => void {
    if (!this.subscribers.has(event)) {
      this.subscribers.set(event, new Set());
    }
    this.subscribers.get(event)!.add(callback);

    // 返回取消订阅函数
    return () => {
      this.off(event, callback);
    };
  }

  /**
   * 订阅一次性事件
   * @param event 事件名称
   * @param callback 回调函数
   */
  once<T = any>(event: string, callback: EventCallback<T>): void {
    const onceCallback = (data: T) => {
      this.off(event, onceCallback);
      callback(data);
    };
    this.on(event, onceCallback);
  }

  /**
   * 取消订阅
   * @param event 事件名称
   * @param callback 回调函数
   */
  off<T = any>(event: string, callback: EventCallback<T>): void {
    const callbacks = this.subscribers.get(event);
    if (callbacks) {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.subscribers.delete(event);
      }
    }
  }

  /**
   * 发射事件
   * @param event 事件名称
   * @param data 事件数据
   */
  emit<T = any>(event: string, data?: T): void {
    const callbacks = this.subscribers.get(event);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * 获取订阅数量
   * @param event 事件名称
   */
  listenerCount(event: string): number {
    return this.subscribers.get(event)?.size || 0;
  }

  /**
   * 清除所有订阅
   */
  clear(): void {
    this.subscribers.clear();
  }
}

// 全局事件发射器实例
export const globalEventEmitter = new EventEmitter();
