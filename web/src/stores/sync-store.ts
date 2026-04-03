/**
 * Sync Store - 同步领域状态管理
 *
 * 管理 WebSocket 连接状态和同步状态
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export type ConnectionStatus =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'
  | 'error';

export interface SyncError {
  code: string;
  message: string;
  timestamp: number;
  dialogId?: string;
  messageId?: string;
}

export interface SyncState {
  // 连接状态
  connectionStatus: ConnectionStatus;
  reconnectAttempts: number;
  lastPingAt: number | null;

  // 同步状态
  pendingSyncs: number;
  isSyncing: boolean;
  lastSyncAt: number | null;

  // 错误状态
  syncErrors: SyncError[];

  // Actions
  setConnectionStatus: (status: ConnectionStatus) => void;
  incrementReconnectAttempt: () => void;
  resetReconnectAttempt: () => void;
  startSync: () => void;
  endSync: () => void;
  addSyncError: (error: SyncError) => void;
  clearSyncErrors: () => void;
  setLastPingAt: (timestamp: number) => void;
  setLastSyncAt: (timestamp: number) => void;
}

export const useSyncStore = create<SyncState>()(
  immer((set) => ({
    // 初始状态
    connectionStatus: 'disconnected',
    reconnectAttempts: 0,
    lastPingAt: null,
    pendingSyncs: 0,
    isSyncing: false,
    lastSyncAt: null,
    syncErrors: [],

    // Actions
    setConnectionStatus: (status) =>
      set((state) => {
        state.connectionStatus = status;
      }),

    incrementReconnectAttempt: () =>
      set((state) => {
        state.reconnectAttempts++;
      }),

    resetReconnectAttempt: () =>
      set((state) => {
        state.reconnectAttempts = 0;
      }),

    startSync: () =>
      set((state) => {
        state.pendingSyncs++;
        state.isSyncing = true;
      }),

    endSync: () =>
      set((state) => {
        state.pendingSyncs = Math.max(0, state.pendingSyncs - 1);
        state.isSyncing = state.pendingSyncs > 0;
      }),

    addSyncError: (error) =>
      set((state) => {
        state.syncErrors.push(error);
        // 只保留最近 10 条错误
        if (state.syncErrors.length > 10) {
          state.syncErrors.shift();
        }
      }),

    clearSyncErrors: () =>
      set((state) => {
        state.syncErrors = [];
      }),

    setLastPingAt: (timestamp) =>
      set((state) => {
        state.lastPingAt = timestamp;
      }),

    setLastSyncAt: (timestamp) =>
      set((state) => {
        state.lastSyncAt = timestamp;
      }),
  }))
);

// 选择器
export const selectSyncStatus = (state: SyncState) => ({
  connection: state.connectionStatus,
  isSyncing: state.isSyncing,
  pendingCount: state.pendingSyncs,
  hasErrors: state.syncErrors.length > 0,
  errors: state.syncErrors,
});

export const selectConnectionStatus = (state: SyncState) => ({
  status: state.connectionStatus,
  reconnectAttempts: state.reconnectAttempts,
  lastPingAt: state.lastPingAt,
});
