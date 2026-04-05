/**
 * Status Store - 状态和错误管理
 *
 * 管理应用状态、连接状态、错误信息等。
 * 从 AgentStore 拆分出来，专注于状态相关逻辑。
 */

import { create } from "zustand";

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";
export type AppStatus = "idle" | "loading" | "streaming" | "error";

interface StatusStoreState {
  // Connection state
  connectionStatus: ConnectionStatus;
  connectionError: string | null;
  lastPingTime: number | null;

  // App state
  appStatus: AppStatus;
  globalError: string | null;

  // Actions
  setConnectionStatus: (status: ConnectionStatus) => void;
  setConnectionError: (error: string | null) => void;
  updateLastPing: () => void;
  setAppStatus: (status: AppStatus) => void;
  setGlobalError: (error: string | null) => void;
  clearAllErrors: () => void;
  reset: () => void;
}

const initialState = {
  connectionStatus: "disconnected" as ConnectionStatus,
  connectionError: null,
  lastPingTime: null,
  appStatus: "idle" as AppStatus,
  globalError: null,
};

export const useStatusStore = create<StatusStoreState>((set) => ({
  ...initialState,

  setConnectionStatus: (status: ConnectionStatus) => {
    set({ connectionStatus: status });
  },

  setConnectionError: (error: string | null) => {
    set({ connectionError: error });
  },

  updateLastPing: () => {
    set({ lastPingTime: Date.now() });
  },

  setAppStatus: (status: AppStatus) => {
    set({ appStatus: status });
  },

  setGlobalError: (error: string | null) => {
    set({ globalError: error });
  },

  clearAllErrors: () => {
    set({
      connectionError: null,
      globalError: null,
    });
  },

  reset: () => {
    set(initialState);
  },
}));
