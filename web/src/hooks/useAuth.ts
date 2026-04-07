"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useUIStore } from "@/stores/ui";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// 存储键
const TOKEN_KEY = "hana_access_token";
const REFRESH_TOKEN_KEY = "hana_refresh_token";
const USER_KEY = "hana_user";
const CLIENT_ID_KEY = "hana_client_id";

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: string;
  created_at?: string;
  last_login?: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthState {
  user: User | null;
  tokens: Tokens | null;
  clientId: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    tokens: null,
    clientId: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  const { theme } = useUIStore();
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 从 localStorage 恢复会话
  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      const token = localStorage.getItem(TOKEN_KEY);
      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      const userJson = localStorage.getItem(USER_KEY);
      const clientId = localStorage.getItem(CLIENT_ID_KEY);

      if (token && userJson) {
        const user = JSON.parse(userJson);
        setState({
          user,
          tokens: {
            access_token: token,
            refresh_token: refreshToken || "",
            token_type: "bearer",
            expires_in: 86400,
          },
          clientId,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      } else {
        setState((s) => ({ ...s, isLoading: false }));
      }
    } catch (e) {
      console.error("[useAuth] Failed to restore session:", e);
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  // 保存会话到 localStorage
  const saveSession = useCallback((user: User, tokens: Tokens, clientId: string) => {
    if (typeof window === "undefined") return;

    localStorage.setItem(TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.setItem(CLIENT_ID_KEY, clientId);
  }, []);

  // 清除会话
  const clearSession = useCallback(() => {
    if (typeof window === "undefined") return;

    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(CLIENT_ID_KEY);

    setState({
      user: null,
      tokens: null,
      clientId: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  }, []);

  // 自动登录
  const autoLogin = useCallback(async (): Promise<boolean> => {
    setState((s) => ({ ...s, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/auto-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Auto-login failed");
      }

      const result = await response.json();

      if (!result.success || !result.data) {
        throw new Error("Invalid response from server");
      }

      const { user, tokens, client_id } = result.data;

      saveSession(user, tokens, client_id);

      setState({
        user,
        tokens,
        clientId: client_id,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      console.log("[useAuth] Auto-login success:", user.username);
      return true;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Auto-login failed";
      console.error("[useAuth] Auto-login error:", errorMsg);
      setState((s) => ({ ...s, isLoading: false, error: errorMsg }));
      return false;
    }
  }, [saveSession]);

  // 标准登录
  const login = useCallback(async (username: string, password: string): Promise<boolean> => {
    setState((s) => ({ ...s, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Login failed");
      }

      const result = await response.json();

      if (!result.success || !result.data) {
        throw new Error("Invalid response from server");
      }

      const { user, tokens, client_id } = result.data;

      saveSession(user, tokens, client_id);

      setState({
        user,
        tokens,
        clientId: client_id,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      return true;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Login failed";
      setState((s) => ({ ...s, isLoading: false, error: errorMsg }));
      return false;
    }
  }, [saveSession]);

  // 登出
  const logout = useCallback(async (): Promise<void> => {
    if (!state.clientId || !state.tokens?.access_token) {
      clearSession();
      return;
    }

    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${state.tokens.access_token}`,
          "X-Client-ID": state.clientId,
        },
      });
    } catch (e) {
      console.error("[useAuth] Logout error:", e);
    } finally {
      clearSession();
    }
  }, [state.clientId, state.tokens?.access_token, clearSession]);

  // 刷新 token
  const refreshToken = useCallback(async (): Promise<boolean> => {
    if (!state.tokens?.refresh_token) return false;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: state.tokens.refresh_token }),
      });

      if (!response.ok) {
        // 刷新失败，清除会话
        clearSession();
        return false;
      }

      const result = await response.json();

      if (!result.success || !result.data) {
        clearSession();
        return false;
      }

      const { access_token, refresh_token, expires_in } = result.data;

      const newTokens: Tokens = {
        access_token,
        refresh_token,
        token_type: "bearer",
        expires_in,
      };

      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);

      setState((s) => ({
        ...s,
        tokens: newTokens,
        isAuthenticated: true,
      }));

      return true;
    } catch (e) {
      console.error("[useAuth] Refresh token error:", e);
      clearSession();
      return false;
    }
  }, [state.tokens?.refresh_token, clearSession]);

  // 获取当前用户信息
  const fetchCurrentUser = useCallback(async (): Promise<User | null> => {
    if (!state.tokens?.access_token) return null;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: {
          "Authorization": `Bearer ${state.tokens.access_token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token 过期，尝试刷新
          const refreshed = await refreshToken();
          if (refreshed) {
            // 重新获取
            return fetchCurrentUser();
          }
        }
        return null;
      }

      const result = await response.json();

      if (result.success && result.data) {
        const user = result.data;
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        setState((s) => ({ ...s, user }));
        return user;
      }

      return null;
    } catch (e) {
      console.error("[useAuth] Fetch user error:", e);
      return null;
    }
  }, [state.tokens?.access_token, refreshToken]);

  return {
    ...state,
    autoLogin,
    login,
    logout,
    refreshToken,
    fetchCurrentUser,
    clearSession,
  };
}
