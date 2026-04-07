"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useUIStore } from "@/stores/ui";

interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * AuthProvider - 认证上下文提供者
 *
 * 负责：
 * 1. 页面加载时自动尝试登录
 * 2. 管理认证状态
 * 3. 显示登录加载状态
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const { autoLogin, isAuthenticated, isLoading, error, user, tokens, clientId } = useAuth();
  const [hasAttemptedLogin, setHasAttemptedLogin] = useState(false);
  const { theme } = useUIStore();

  // 页面加载时自动登录
  useEffect(() => {
    if (hasAttemptedLogin || isAuthenticated) return;

    const attemptLogin = async () => {
      console.log("[AuthProvider] Attempting auto-login...");
      const success = await autoLogin();
      setHasAttemptedLogin(true);

      if (success) {
        console.log("[AuthProvider] Auto-login success");
      } else {
        console.error("[AuthProvider] Auto-login failed");
      }
    };

    attemptLogin();
  }, [autoLogin, isAuthenticated, hasAttemptedLogin]);

  // 显示加载状态
  if (isLoading) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg)",
          color: "var(--text)",
          fontFamily: "var(--font-ui)",
          zIndex: 9999,
        }}
        data-theme={theme}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: 40,
              height: 40,
              border: "3px solid var(--overlay-medium)",
              borderTopColor: "var(--accent)",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 16px",
            }}
          />
          <p style={{ fontSize: 14, color: "var(--text-light)" }}>
            正在登录...
          </p>
        </div>
      </div>
    );
  }

  // 显示错误状态（允许重试）
  if (error && !isAuthenticated) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--bg)",
          color: "var(--text)",
          fontFamily: "var(--font-ui)",
          zIndex: 9999,
        }}
        data-theme={theme}
      >
        <div style={{ textAlign: "center", maxWidth: 400, padding: 24 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
          <h2 style={{ fontSize: 18, marginBottom: 8 }}>登录失败</h2>
          <p style={{ fontSize: 14, color: "var(--text-light)", marginBottom: 24 }}>
            {error}
          </p>
          <button
            onClick={() => {
              setHasAttemptedLogin(false);
            }}
            style={{
              padding: "10px 24px",
              background: "var(--accent)",
              color: "#fff",
              border: "none",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  // 认证成功后渲染子组件
  return (
    <>
      {children}
      {/* 调试信息（开发环境） */}
      {process.env.NODE_ENV === "development" && user && (
        <div
          style={{
            position: "fixed",
            bottom: 8,
            right: 8,
            padding: "4px 8px",
            background: "var(--accent-light)",
            color: "var(--accent)",
            fontSize: 11,
            borderRadius: "var(--radius-sm)",
            zIndex: 9999,
          }}
        >
          {user.username} ({user.role}) | {clientId?.slice(0, 8)}...
        </div>
      )}
    </>
  );
}

// 导出认证信息给子组件使用
export { useAuth };
