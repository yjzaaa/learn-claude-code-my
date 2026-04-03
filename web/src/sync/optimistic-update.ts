/**
 * Optimistic Update Manager
 *
 * 管理乐观更新的生命周期：创建、确认、回滚
 */

import { useMessageStore, type PendingMessage, type Message } from '@/stores/message-store';

interface OptimisticUpdateConfig {
  onAdd?: (msg: PendingMessage) => void;
  onConfirm?: (clientId: string, serverMessage: Message) => void;
  onFail?: (clientId: string, error: Error) => void;
  onRollback?: (clientId: string) => void;
}

export class OptimisticUpdateManager {
  private pendingMessages = new Map<string, PendingMessage>();
  private orderCounter = 0;
  private config: OptimisticUpdateConfig;

  constructor(config: OptimisticUpdateConfig = {}) {
    this.config = config;
  }

  /**
   * 生成乐观序号
   */
  private generateOrder(): number {
    return ++this.orderCounter;
  }

  /**
   * 生成客户端 ID
   */
  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  }

  /**
   * 创建乐观消息
   */
  create(dialogId: string, content: string): PendingMessage {
    const clientId = this.generateClientId();
    const optimisticOrder = this.generateOrder();

    const pendingMessage: PendingMessage = {
      clientId,
      dialogId,
      content,
      optimisticOrder,
      status: 'pending',
      createdAt: Date.now(),
    };

    this.pendingMessages.set(clientId, pendingMessage);

    // 添加到 store
    useMessageStore.getState().addOptimisticMessage(dialogId, content, clientId, optimisticOrder);

    this.config.onAdd?.(pendingMessage);

    return pendingMessage;
  }

  /**
   * 确认消息成功
   */
  confirm(clientId: string, serverMessage: Message): void {
    const pending = this.pendingMessages.get(clientId);
    if (!pending) return;

    pending.status = 'confirmed';

    useMessageStore.getState().confirmMessage(clientId, serverMessage);
    this.pendingMessages.delete(clientId);

    this.config.onConfirm?.(clientId, serverMessage);
  }

  /**
   * 标记发送中
   */
  markSending(clientId: string): void {
    const pending = this.pendingMessages.get(clientId);
    if (pending) {
      pending.status = 'sending';
      useMessageStore.getState().updatePendingStatus(clientId, 'sending');
    }
  }

  /**
   * 标记失败
   */
  markFailed(clientId: string, error: Error): void {
    const pending = this.pendingMessages.get(clientId);
    if (!pending) return;

    pending.status = 'failed';
    useMessageStore.getState().updatePendingStatus(clientId, 'failed');

    this.config.onFail?.(clientId, error);
  }

  /**
   * 回滚乐观更新
   */
  rollback(clientId: string): void {
    const pending = this.pendingMessages.get(clientId);
    if (!pending) return;

    useMessageStore.getState().rollbackMessage(clientId);
    this.pendingMessages.delete(clientId);

    this.config.onRollback?.(clientId);
  }

  /**
   * 获取所有 pending 消息
   */
  getPending(): PendingMessage[] {
    return Array.from(this.pendingMessages.values());
  }

  /**
   * 获取指定 dialog 的 pending 消息
   */
  getPendingByDialog(dialogId: string): PendingMessage[] {
    return this.getPending().filter((m) => m.dialogId === dialogId);
  }

  /**
   * 清理已确认的消息
   */
  cleanup(): void {
    const now = Date.now();
    const timeout = 5 * 60 * 1000; // 5分钟

    for (const [clientId, message] of this.pendingMessages) {
      if (message.status === 'confirmed' && now - message.createdAt > timeout) {
        this.pendingMessages.delete(clientId);
      }
    }
  }
}

// 单例实例
let optimisticManagerInstance: OptimisticUpdateManager | null = null;

export function getOptimisticUpdateManager(config?: OptimisticUpdateConfig): OptimisticUpdateManager {
  if (!optimisticManagerInstance) {
    optimisticManagerInstance = new OptimisticUpdateManager(config);
  }
  return optimisticManagerInstance;
}

export function createOptimisticUpdateManager(config: OptimisticUpdateConfig): OptimisticUpdateManager {
  optimisticManagerInstance = new OptimisticUpdateManager(config);
  return optimisticManagerInstance;
}
