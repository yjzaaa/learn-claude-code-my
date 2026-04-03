"use client";

import { useEffect, useState } from "react";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { useMessageSync } from "@/hooks/useMessageSync";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface ChatInitializerProps {
  /** 对话 ID */
  dialogId: string;
  /** 初始化完成回调 */
  onReady?: () => void;
  /** 子组件（渲染在加载完成后） */
  children: React.ReactNode;
}

/**
 * ChatInitializer - 对话初始化组件
 *
 * 职责：
 * - 从 IndexedDB 加载历史消息
 * - 显示加载状态
 * - 处理加载错误
 * - 初始化完成后渲染子组件
 */
export function ChatInitializer({
  dialogId,
  onReady,
  children,
}: ChatInitializerProps) {
  const { messages, isLoading, error, connectionStatus, reloadMessages } =
    useMessageSync(dialogId);
  const [initError, setInitError] = useState<string | null>(null);

  // 通知父组件初始化完成
  useEffect(() => {
    if (!isLoading && connectionStatus === "connected") {
      onReady?.();
    }
  }, [isLoading, connectionStatus, onReady]);

  // 处理加载错误
  useEffect(() => {
    if (error) {
      setInitError(error);
    }
  }, [error]);

  // 重试加载
  const handleRetry = async () => {
    setInitError(null);
    try {
      await reloadMessages();
    } catch (err) {
      setInitError(err instanceof Error ? err.message : "重试失败");
    }
  };

  // 显示加载状态
  if (isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-sm font-medium">加载对话中...</p>
          <p className="text-xs text-muted-foreground">
            从本地存储恢复消息历史
          </p>
        </div>
      </div>
    );
  }

  // 显示连接状态
  if (connectionStatus === "disconnected" || connectionStatus === "error") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <div className="text-center">
          <p className="text-sm font-medium">连接断开</p>
          <p className="text-xs text-muted-foreground">
            正在尝试重新连接服务器...
          </p>
        </div>
      </div>
    );
  }

  if (connectionStatus === "reconnecting") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <Loader2 className="h-8 w-8 animate-spin text-warning" />
        <div className="text-center">
          <p className="text-sm font-medium">重新连接中...</p>
          <p className="text-xs text-muted-foreground">正在恢复与服务器的连接</p>
        </div>
      </div>
    );
  }

  // 显示错误
  if (initError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>加载失败</AlertTitle>
          <AlertDescription>{initError}</AlertDescription>
        </Alert>
        <Button variant="outline" size="sm" onClick={handleRetry}>
          <RefreshCw className="mr-2 h-4 w-4" />
          重试
        </Button>
      </div>
    );
  }

  // 渲染子组件
  return <>{children}</>;
}

/**
 * ChatInitializerSkeleton - 加载占位组件
 */
export function ChatInitializerSkeleton() {
  return (
    <div className="flex h-full flex-col gap-4 p-4">
      {/* 消息骨架 */}
      <div className="space-y-4">
        <div className="flex gap-3">
          <div className="h-8 w-8 rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-24 rounded bg-muted" />
            <div className="h-20 rounded-lg bg-muted" />
          </div>
        </div>
        <div className="flex gap-3 justify-end">
          <div className="flex-1 space-y-2">
            <div className="h-16 rounded-lg bg-muted" />
          </div>
          <div className="h-8 w-8 rounded-full bg-muted" />
        </div>
        <div className="flex gap-3">
          <div className="h-8 w-8 rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-24 rounded bg-muted" />
            <div className="h-32 rounded-lg bg-muted" />
          </div>
        </div>
      </div>
    </div>
  );
}
