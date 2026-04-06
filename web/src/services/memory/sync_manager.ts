/**
 * Sync Manager - 同步管理器
 *
 * 管理前后端记忆数据的同步协议：
 * - 离线/在线状态处理
 * - 批量同步操作
 * - 冲突检测（时间戳比较）
 * - 指数退避重试
 * - 定期同步支持
 */

import { api } from '../../lib/api';

// ============================================================================
// 类型定义
// ============================================================================

/** 记忆类型 */
export type MemoryType = 'user' | 'feedback' | 'project' | 'reference';

/** 记忆对象 */
export interface Memory {
  id: string;
  user_id: string;
  project_path: string;
  type: MemoryType;
  name: string;
  description: string;
  content: string;
  created_at: string;
  updated_at: string;
  source_dialog_id?: string;
  confidence?: number;
}

/** 同步操作类型 */
export type SyncOperationType = 'SAVE' | 'UPDATE' | 'DELETE';

/** 同步操作 */
export interface SyncOperation {
  id: string;
  type: SyncOperationType;
  memory: Memory;
  clientTimestamp: number;
}

/** 同步结果 */
export interface SyncResult {
  success: boolean;
  operationId: string;
  serverTimestamp?: number;
  conflict?: boolean;
  error?: string;
}

/** 批量同步请求 */
interface SyncBatchRequest {
  operations: SyncOperation[];
  clientTimestamp: number;
}

/** 批量同步响应 */
interface SyncBatchResponse {
  results: SyncResult[];
  serverTimestamp: number;
}

/** 同步队列项（存储用） */
interface SyncQueueItem {
  operation: SyncOperation;
  retryCount: number;
  lastAttempt?: number;
}

// ============================================================================
// 常量
// ============================================================================

const STORAGE_KEY = 'memory_sync_queue';
const DEFAULT_RETRY_DELAYS = [1000, 2000, 4000, 8000, 16000]; // 指数退避
const DEFAULT_SYNC_INTERVAL = 30000; // 30秒
const MAX_QUEUE_SIZE = 1000; // 最大队列长度

// ============================================================================
// SyncManager 类
// ============================================================================

export class SyncManager {
  private isOnline: boolean = typeof navigator !== 'undefined' ? navigator.onLine : true;
  private syncInterval: number | null = null;
  private retryDelays: number[];
  private syncIntervalMs: number;
  private isFlushing: boolean = false;
  private readonly maxQueueSize: number;

  constructor(options?: {
    retryDelays?: number[];
    syncIntervalMs?: number;
    maxQueueSize?: number;
  }) {
    this.retryDelays = options?.retryDelays ?? DEFAULT_RETRY_DELAYS;
    this.syncIntervalMs = options?.syncIntervalMs ?? DEFAULT_SYNC_INTERVAL;
    this.maxQueueSize = options?.maxQueueSize ?? MAX_QUEUE_SIZE;

    if (typeof window !== 'undefined') {
      this.setupNetworkListeners();
      this.loadQueueFromStorage();
    }
  }

  // ==========================================================================
  // 网络状态监听
  // ==========================================================================

  private setupNetworkListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.handleOnline();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.handleOffline();
    });
  }

  private handleOnline(): void {
    console.log('[SyncManager] 网络已恢复，开始同步队列');
    void this.flushQueue();
  }

  private handleOffline(): void {
    console.log('[SyncManager] 网络已断开，操作将加入队列');
  }

  // ==========================================================================
  // 队列操作
  // ==========================================================================

  /**
   * 将操作加入同步队列
   */
  async queueOperation(operation: SyncOperation): Promise<void> {
    const queue = this.getQueue();

    // 检查队列是否已满
    if (queue.length >= this.maxQueueSize) {
      // 移除最旧的未重试项
      const oldestIndex = queue.findIndex(item => item.retryCount === 0);
      if (oldestIndex >= 0) {
        queue.splice(oldestIndex, 1);
      } else {
        throw new Error('Sync queue is full');
      }
    }

    // 检查是否已存在相同记忆的操作，如果有则合并
    const existingIndex = queue.findIndex(
      item => item.operation.memory.id === operation.memory.id
    );

    if (existingIndex >= 0) {
      const existing = queue[existingIndex];

      // 合并规则：
      // - DELETE 优先级最高
      // - SAVE + UPDATE = SAVE（使用最新内容）
      // - UPDATE + UPDATE = UPDATE（使用最新内容）
      if (existing.operation.type === 'DELETE' || operation.type === 'DELETE') {
        // 保留 DELETE 操作
        queue[existingIndex] = {
          operation: { ...operation, type: 'DELETE' },
          retryCount: 0,
        };
      } else if (existing.operation.type === 'SAVE') {
        // SAVE + UPDATE = SAVE（更新内容）
        queue[existingIndex] = {
          operation: { ...existing.operation, memory: operation.memory },
          retryCount: 0,
        };
      } else {
        // UPDATE + UPDATE = UPDATE
        queue[existingIndex] = {
          operation,
          retryCount: 0,
        };
      }
    } else {
      queue.push({
        operation,
        retryCount: 0,
      });
    }

    this.saveQueueToStorage(queue);

    // 如果在线，立即尝试同步
    if (this.isOnline && !this.isFlushing) {
      void this.flushQueue();
    }
  }

  /**
   * 创建 SAVE 操作并入队
   */
  async queueSave(memory: Memory): Promise<void> {
    await this.queueOperation({
      id: this.generateId(),
      type: 'SAVE',
      memory,
      clientTimestamp: Date.now(),
    });
  }

  /**
   * 创建 UPDATE 操作并入队
   */
  async queueUpdate(memory: Memory): Promise<void> {
    await this.queueOperation({
      id: this.generateId(),
      type: 'UPDATE',
      memory,
      clientTimestamp: Date.now(),
    });
  }

  /**
   * 创建 DELETE 操作并入队
   */
  async queueDelete(memoryId: string, userId: string): Promise<void> {
    await this.queueOperation({
      id: this.generateId(),
      type: 'DELETE',
      memory: {
        id: memoryId,
        user_id: userId,
        project_path: '',
        type: 'reference',
        name: '',
        description: '',
        content: '',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      clientTimestamp: Date.now(),
    });
  }

  // ==========================================================================
  // 队列刷新（批量同步）
  // ==========================================================================

  /**
   * 刷新队列，将所有待同步操作发送到服务器
   */
  async flushQueue(): Promise<SyncResult[]> {
    if (this.isFlushing || !this.isOnline) {
      return [];
    }

    this.isFlushing = true;
    const results: SyncResult[] = [];

    try {
      const queue = this.getQueue();

      if (queue.length === 0) {
        return results;
      }

      // 提取待同步的操作（按添加顺序）
      const operations = queue.map(item => item.operation);

      // 发送批量请求
      const batchResults = await this.sendBatch(operations);

      // 处理结果
      const remainingQueue: SyncQueueItem[] = [];

      for (let i = 0; i < queue.length; i++) {
        const item = queue[i];
        const result = batchResults[i];

        if (result.success) {
          results.push(result);
        } else if (result.conflict) {
          // 冲突处理：保留服务器版本，通知调用方
          results.push(result);
          console.warn(`[SyncManager] 冲突 detected for operation ${item.operation.id}`);
        } else if (item.retryCount < this.retryDelays.length) {
          // 重试
          remainingQueue.push({
            ...item,
            retryCount: item.retryCount + 1,
            lastAttempt: Date.now(),
          });
        } else {
          // 重试次数用尽
          results.push({
            ...result,
            error: `Max retries exceeded: ${result.error}`,
          });
        }
      }

      this.saveQueueToStorage(remainingQueue);

      // 如果还有未完成的操作，安排重试
      if (remainingQueue.length > 0) {
        this.scheduleRetry();
      }
    } catch (error) {
      console.error('[SyncManager] Flush queue failed:', error);
    } finally {
      this.isFlushing = false;
    }

    return results;
  }

  /**
   * 发送批量同步请求
   */
  private async sendBatch(operations: SyncOperation[]): Promise<SyncResult[]> {
    const request: SyncBatchRequest = {
      operations,
      clientTimestamp: Date.now(),
    };

    try {
      const response = await fetch(`${this.getApiBase()}/api/memory/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        // 如果服务器返回错误，所有操作都标记为失败
        const errorText = await response.text();
        return operations.map(op => ({
          success: false,
          operationId: op.id,
          error: `HTTP ${response.status}: ${errorText}`,
        }));
      }

      const data = (await response.json()) as SyncBatchResponse;
      return data.results;
    } catch (error) {
      // 网络错误，所有操作都标记为失败以便重试
      return operations.map(op => ({
        success: false,
        operationId: op.id,
        error: error instanceof Error ? error.message : 'Network error',
      }));
    }
  }

  // ==========================================================================
  // 冲突检测
  // ==========================================================================

  /**
   * 检测冲突（基于时间戳比较）
   */
  detectConflict(operation: SyncOperation, serverMemory: Memory): boolean {
    const clientUpdateTime = new Date(operation.memory.updated_at).getTime();
    const serverUpdateTime = new Date(serverMemory.updated_at).getTime();

    // 如果服务器版本比客户端新，则存在冲突
    if (serverUpdateTime > clientUpdateTime) {
      return true;
    }

    // 如果时间戳相同但内容不同，也可能存在冲突
    if (serverUpdateTime === clientUpdateTime) {
      return serverMemory.content !== operation.memory.content;
    }

    return false;
  }

  /**
   * 解决冲突（服务器优先）
   */
  resolveConflict(clientMemory: Memory, serverMemory: Memory): Memory {
    // 策略：服务器优先
    return serverMemory;
  }

  // ==========================================================================
  // 重试机制
  // ==========================================================================

  private retryTimeout: number | null = null;

  private scheduleRetry(): void {
    if (this.retryTimeout !== null) {
      window.clearTimeout(this.retryTimeout);
    }

    const queue = this.getQueue();
    if (queue.length === 0) return;

    // 找到需要重试的项中最大的重试次数
    const maxRetries = Math.max(...queue.map(item => item.retryCount));
    const delay = this.retryDelays[Math.min(maxRetries, this.retryDelays.length - 1)];

    this.retryTimeout = window.setTimeout(() => {
      void this.flushQueue();
    }, delay);
  }

  /**
   * 带指数退避的重试
   */
  private async retryWithBackoff(
    operation: SyncOperation,
    attempt: number
  ): Promise<SyncResult> {
    const delay = this.retryDelays[Math.min(attempt, this.retryDelays.length - 1)];

    await new Promise(resolve => setTimeout(resolve, delay));

    const results = await this.sendBatch([operation]);
    return results[0] ?? {
      success: false,
      operationId: operation.id,
      error: 'No response from server',
    };
  }

  // ==========================================================================
  // 定期同步
  // ==========================================================================

  /**
   * 启动定期同步
   */
  startPeriodicSync(intervalMs?: number): void {
    this.stopPeriodicSync();

    const interval = intervalMs ?? this.syncIntervalMs;

    this.syncInterval = window.setInterval(() => {
      if (this.isOnline && !this.isFlushing) {
        void this.flushQueue();
      }
    }, interval);

    console.log(`[SyncManager] 定期同步已启动，间隔: ${interval}ms`);
  }

  /**
   * 停止定期同步
   */
  stopPeriodicSync(): void {
    if (this.syncInterval !== null) {
      window.clearInterval(this.syncInterval);
      this.syncInterval = null;
      console.log('[SyncManager] 定期同步已停止');
    }
  }

  // ==========================================================================
  // 存储管理（localStorage）
  // ==========================================================================

  private getQueue(): SyncQueueItem[] {
    if (typeof window === 'undefined') return [];

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? (JSON.parse(stored) as SyncQueueItem[]) : [];
    } catch {
      return [];
    }
  }

  private saveQueueToStorage(queue: SyncQueueItem[]): void {
    if (typeof window === 'undefined') return;

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
    } catch (error) {
      console.error('[SyncManager] 保存队列失败:', error);
    }
  }

  private loadQueueFromStorage(): void {
    // 页面加载时自动恢复队列
    const queue = this.getQueue();
    if (queue.length > 0) {
      console.log(`[SyncManager] 从存储恢复 ${queue.length} 个待同步操作`);
    }
  }

  // ==========================================================================
  // 工具方法
  // ==========================================================================

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private getApiBase(): string {
    return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8001';
  }

  /**
   * 获取当前队列长度
   */
  getQueueLength(): number {
    return this.getQueue().length;
  }

  /**
   * 清空队列（谨慎使用）
   */
  clearQueue(): void {
    this.saveQueueToStorage([]);
  }

  /**
   * 获取网络状态
   */
  getNetworkStatus(): boolean {
    return this.isOnline;
  }

  /**
   * 检查是否正在同步
   */
  isSyncing(): boolean {
    return this.isFlushing;
  }
}

// ============================================================================
// 单例导出
// ============================================================================

export const syncManager = new SyncManager();

// 默认导出
export default SyncManager;
