/**
 * Client-side IndexedDB memory cache manager
 * Implements cache-first strategy with sync queue for offline support
 */

export interface Memory {
  id: string;
  user_id: string;
  project_path: string;
  type: 'user' | 'feedback' | 'project' | 'reference';
  name: string;
  description: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface SyncQueueItem {
  id: string;
  operation: 'SAVE' | 'UPDATE' | 'DELETE';
  memory: Memory;
  timestamp: number;
  retry_count: number;
}

export class ClientMemoryManager {
  private db: IDBDatabase | null = null;
  private readonly DB_NAME = 'ClaudeCodeMemory';
  private readonly DB_VERSION = 1;
  private readonly MAX_CACHED = 20;
  private readonly STORE_MEMORIES = 'memories';
  private readonly STORE_SYNC_QUEUE = 'sync_queue';

  /**
   * Initialize IndexedDB database
   */
  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

      request.onerror = () => {
        reject(new Error(`Failed to open IndexedDB: ${request.error?.message}`));
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Create memories store with id as key
        if (!db.objectStoreNames.contains(this.STORE_MEMORIES)) {
          const memoryStore = db.createObjectStore(this.STORE_MEMORIES, {
            keyPath: 'id',
          });
          // Create index for updated_at to support sorting
          memoryStore.createIndex('updated_at', 'updated_at', { unique: false });
          // Create index for type to support filtering
          memoryStore.createIndex('type', 'type', { unique: false });
        }

        // Create sync queue store
        if (!db.objectStoreNames.contains(this.STORE_SYNC_QUEUE)) {
          const queueStore = db.createObjectStore(this.STORE_SYNC_QUEUE, {
            keyPath: 'id',
          });
          queueStore.createIndex('timestamp', 'timestamp', { unique: false });
        }
      };
    });
  }

  /**
   * Ensure database is initialized
   */
  private ensureDb(): IDBDatabase {
    if (!this.db) {
      throw new Error('ClientMemoryManager not initialized. Call init() first.');
    }
    return this.db;
  }

  /**
   * Get memory by ID - cache-first strategy
   */
  async getMemory(id: string): Promise<Memory | null> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_MEMORIES], 'readonly');
      const store = transaction.objectStore(this.STORE_MEMORIES);
      const request = store.get(id);

      request.onsuccess = () => {
        resolve(request.result || null);
      };

      request.onerror = () => {
        reject(new Error(`Failed to get memory: ${request.error?.message}`));
      };
    });
  }

  /**
   * Save memory to IndexedDB and add to sync queue
   */
  async saveMemory(memory: Memory): Promise<void> {
    const db = this.ensureDb();

    // Check if memory already exists to determine operation
    const existing = await this.getMemory(memory.id);
    const operation: SyncQueueItem['operation'] = existing ? 'UPDATE' : 'SAVE';

    // Update timestamp
    const memoryWithTimestamp = {
      ...memory,
      updated_at: new Date().toISOString(),
    };

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(
        [this.STORE_MEMORIES, this.STORE_SYNC_QUEUE],
        'readwrite'
      );

      transaction.onerror = () => {
        reject(new Error(`Transaction failed: ${transaction.error?.message}`));
      };

      transaction.oncomplete = () => {
        // Evict old memories after successful save
        this.evictOldMemories().catch(console.error);
        resolve();
      };

      // Save to memories store
      const memoryStore = transaction.objectStore(this.STORE_MEMORIES);
      memoryStore.put(memoryWithTimestamp);

      // Add to sync queue
      const queueStore = transaction.objectStore(this.STORE_SYNC_QUEUE);
      const queueItem: SyncQueueItem = {
        id: `${memory.id}_${Date.now()}`,
        operation,
        memory: memoryWithTimestamp,
        timestamp: Date.now(),
        retry_count: 0,
      };
      queueStore.put(queueItem);
    });
  }

  /**
   * Get recent memories from IndexedDB, sorted by updated_at desc
   */
  async getRecentMemories(limit: number = this.MAX_CACHED): Promise<Memory[]> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_MEMORIES], 'readonly');
      const store = transaction.objectStore(this.STORE_MEMORIES);
      const index = store.index('updated_at');

      // Open cursor in descending order
      const request = index.openCursor(null, 'prev');
      const memories: Memory[] = [];

      request.onsuccess = () => {
        const cursor = request.result;
        if (cursor && memories.length < limit) {
          memories.push(cursor.value);
          cursor.continue();
        } else {
          resolve(memories);
        }
      };

      request.onerror = () => {
        reject(new Error(`Failed to get memories: ${request.error?.message}`));
      };
    });
  }

  /**
   * Delete memory - marks for deletion and adds to sync queue
   */
  async deleteMemory(id: string): Promise<void> {
    const db = this.ensureDb();

    // Get memory before deleting for sync queue
    const memory = await this.getMemory(id);
    if (!memory) {
      return; // Memory doesn't exist, nothing to delete
    }

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(
        [this.STORE_MEMORIES, this.STORE_SYNC_QUEUE],
        'readwrite'
      );

      transaction.onerror = () => {
        reject(new Error(`Transaction failed: ${transaction.error?.message}`));
      };

      transaction.oncomplete = () => {
        resolve();
      };

      // Delete from memories store
      const memoryStore = transaction.objectStore(this.STORE_MEMORIES);
      memoryStore.delete(id);

      // Add to sync queue
      const queueStore = transaction.objectStore(this.STORE_SYNC_QUEUE);
      const queueItem: SyncQueueItem = {
        id: `${id}_${Date.now()}`,
        operation: 'DELETE',
        memory,
        timestamp: Date.now(),
        retry_count: 0,
      };
      queueStore.put(queueItem);
    });
  }

  /**
   * Get all pending sync queue items
   */
  async getSyncQueue(): Promise<SyncQueueItem[]> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_SYNC_QUEUE], 'readonly');
      const store = transaction.objectStore(this.STORE_SYNC_QUEUE);
      const request = store.getAll();

      request.onsuccess = () => {
        const items = request.result as SyncQueueItem[];
        // Sort by timestamp ascending (oldest first)
        items.sort((a, b) => a.timestamp - b.timestamp);
        resolve(items);
      };

      request.onerror = () => {
        reject(new Error(`Failed to get sync queue: ${request.error?.message}`));
      };
    });
  }

  /**
   * Remove item from sync queue after successful sync
   */
  async removeFromSyncQueue(id: string): Promise<void> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_SYNC_QUEUE], 'readwrite');
      const store = transaction.objectStore(this.STORE_SYNC_QUEUE);
      const request = store.delete(id);

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        reject(new Error(`Failed to remove from sync queue: ${request.error?.message}`));
      };
    });
  }

  /**
   * Update retry count for a sync queue item
   */
  async incrementRetryCount(id: string): Promise<void> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_SYNC_QUEUE], 'readwrite');
      const store = transaction.objectStore(this.STORE_SYNC_QUEUE);
      const getRequest = store.get(id);

      getRequest.onsuccess = () => {
        const item = getRequest.result as SyncQueueItem | undefined;
        if (item) {
          item.retry_count += 1;
          const putRequest = store.put(item);
          putRequest.onsuccess = () => resolve();
          putRequest.onerror = () =>
            reject(new Error(`Failed to update retry count: ${putRequest.error?.message}`));
        } else {
          resolve();
        }
      };

      getRequest.onerror = () => {
        reject(new Error(`Failed to get queue item: ${getRequest.error?.message}`));
      };
    });
  }

  /**
   * Clear all data (for testing or logout)
   */
  async clearAll(): Promise<void> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(
        [this.STORE_MEMORIES, this.STORE_SYNC_QUEUE],
        'readwrite'
      );

      transaction.onerror = () => {
        reject(new Error(`Transaction failed: ${transaction.error?.message}`));
      };

      transaction.oncomplete = () => {
        resolve();
      };

      transaction.objectStore(this.STORE_MEMORIES).clear();
      transaction.objectStore(this.STORE_SYNC_QUEUE).clear();
    });
  }

  /**
   * Evict old memories, keeping only the most recent MAX_CACHED
   */
  private async evictOldMemories(): Promise<void> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_MEMORIES], 'readwrite');
      const store = transaction.objectStore(this.STORE_MEMORIES);
      const index = store.index('updated_at');

      // Open cursor in ascending order (oldest first)
      const request = index.openCursor(null, 'next');
      const idsToDelete: string[] = [];
      let count = 0;

      request.onsuccess = () => {
        const cursor = request.result;
        if (cursor) {
          count++;
          if (count > this.MAX_CACHED) {
            idsToDelete.push(cursor.value.id);
          }
          cursor.continue();
        } else {
          // Delete excess memories
          idsToDelete.forEach((id) => {
            store.delete(id);
          });
          resolve();
        }
      };

      request.onerror = () => {
        reject(new Error(`Failed to evict old memories: ${request.error?.message}`));
      };
    });
  }

  /**
   * Get memory count
   */
  async getMemoryCount(): Promise<number> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_MEMORIES], 'readonly');
      const store = transaction.objectStore(this.STORE_MEMORIES);
      const request = store.count();

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(new Error(`Failed to count memories: ${request.error?.message}`));
      };
    });
  }

  /**
   * Get memories by type
   */
  async getMemoriesByType(type: Memory['type']): Promise<Memory[]> {
    const db = this.ensureDb();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.STORE_MEMORIES], 'readonly');
      const store = transaction.objectStore(this.STORE_MEMORIES);
      const index = store.index('type');
      const request = index.getAll(type);

      request.onsuccess = () => {
        const memories = request.result as Memory[];
        // Sort by updated_at desc
        memories.sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
        resolve(memories);
      };

      request.onerror = () => {
        reject(new Error(`Failed to get memories by type: ${request.error?.message}`));
      };
    });
  }
}

// Export singleton instance
export const memoryManager = new ClientMemoryManager();
