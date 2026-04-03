"use client";

import { AlertTriangle, RefreshCw, X } from "lucide-react";
import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { cn } from "@/lib/utils";

interface TruncatedNoticeProps {
  /** 截断原因 */
  reason?: string;
  /** 消息内容预览 */
  preview?: string;
  /** 恢复回调 */
  onResume?: () => void;
  /** 关闭回调 */
  onClose?: () => void;
  /** 自定义类名 */
  className?: string;
  /** 变体样式 */
  variant?: "inline" | "banner" | "toast";
}

/**
 * TruncatedNotice - 流式消息截断提示组件
 *
 * 当流式消息因网络中断等原因被截断时显示
 * 提供一键恢复按钮
 */
export function TruncatedNotice({
  reason = "网络中断",
  preview,
  onResume,
  onClose,
  className,
  variant = "inline",
}: TruncatedNoticeProps) {
  const [isResuming, setIsResuming] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  // 处理恢复
  const handleResume = useCallback(async () => {
    setIsResuming(true);
    try {
      await onResume?.();
    } finally {
      setIsResuming(false);
    }
  }, [onResume]);

  // 处理关闭
  const handleDismiss = useCallback(() => {
    setIsDismissed(true);
    onClose?.();
  }, [onClose]);

  if (isDismissed) {
    return null;
  }

  // 根据变体选择样式
  const variantStyles = {
    inline: "border-l-4 border-l-warning",
    banner: "rounded-none border-x-0 border-t-0",
    toast: "shadow-lg",
  };

  return (
    <Alert
      variant="warning"
      className={cn(
        "relative",
        variantStyles[variant],
        className
      )}
    >
      <AlertTriangle className="h-4 w-4 text-warning" />

      <AlertTitle className="flex items-center gap-2">
        <span>消息被截断</span>
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            className="h-4 w-4 -mr-1 ml-auto opacity-50 hover:opacity-100"
            onClick={handleDismiss}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </AlertTitle>

      <AlertDescription className="mt-2 space-y-3">
        <p className="text-sm">
          此消息因<span className="font-medium">{reason}</span>被截断。
          {preview && (
            <span className="block mt-1 text-muted-foreground">
              已接收内容: {preview.slice(0, 100)}
              {preview.length > 100 ? "..." : ""}
            </span>
          )}
        </p>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleResume}
            disabled={isResuming}
            className="gap-1.5"
          >
            {isResuming ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                恢复中...
              </>
            ) : (
              <>
                <RefreshCw className="h-3.5 w-3.5" />
                继续生成
              </>
            )}
          </Button>

          {onClose && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleDismiss}
              disabled={isResuming}
            >
              忽略
            </Button>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}

/**
 * TruncatedNoticeList - 批量截断消息提示
 */
interface TruncatedNoticeListProps {
  /** 截断消息列表 */
  truncatedMessages: Array<{
    id: string;
    reason?: string;
    preview?: string;
  }>;
  /** 恢复单个消息 */
  onResumeOne?: (id: string) => void;
  /** 恢复所有消息 */
  onResumeAll?: () => void;
  /** 关闭 */
  onClose?: () => void;
  className?: string;
}

export function TruncatedNoticeList({
  truncatedMessages,
  onResumeOne,
  onResumeAll,
  onClose,
  className,
}: TruncatedNoticeListProps) {
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [isResumingAll, setIsResumingAll] = useState(false);

  if (truncatedMessages.length === 0) {
    return null;
  }

  // 过滤已关闭的消息
  const visibleMessages = truncatedMessages.filter(
    (m) => !dismissedIds.has(m.id)
  );

  if (visibleMessages.length === 0) {
    return null;
  }

  const handleDismissOne = (id: string) => {
    setDismissedIds((prev) => new Set(prev).add(id));
  };

  const handleResumeAll = async () => {
    setIsResumingAll(true);
    try {
      await onResumeAll?.();
    } finally {
      setIsResumingAll(false);
    }
  };

  // 单条消息直接显示 TruncatedNotice
  if (visibleMessages.length === 1) {
    const msg = visibleMessages[0];
    return (
      <TruncatedNotice
        reason={msg.reason}
        preview={msg.preview}
        onResume={() => onResumeOne?.(msg.id)}
        onClose={() => handleDismissOne(msg.id)}
        className={className}
      />
    );
  }

  // 多条消息显示汇总提示
  return (
    <Alert variant="warning" className={cn("relative", className)}>
      <AlertTriangle className="h-4 w-4 text-warning" />

      <AlertTitle className="flex items-center justify-between">
        <span>多条消息被截断</span>
        {onClose && (
          <Button
            variant="ghost"
            size="icon"
            className="h-4 w-4 -mr-1 opacity-50 hover:opacity-100"
            onClick={onClose}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </AlertTitle>

      <AlertDescription className="mt-2 space-y-3">
        <p className="text-sm">
          有 <span className="font-medium">{visibleMessages.length}</span> 条消息因网络问题被截断。
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleResumeAll}
            disabled={isResumingAll}
            className="gap-1.5"
          >
            {isResumingAll ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                恢复中...
              </>
            ) : (
              <>
                <RefreshCw className="h-3.5 w-3.5" />
                全部继续
              </>
            )}
          </Button>

          {visibleMessages.slice(0, 3).map((msg) => (
            <Button
              key={msg.id}
              size="sm"
              variant="ghost"
              onClick={() => onResumeOne?.(msg.id)}
              className="text-xs"
            >
              恢复 #{msg.id.slice(-4)}
            </Button>
          ))}

          {visibleMessages.length > 3 && (
            <span className="text-xs text-muted-foreground">
              +{visibleMessages.length - 3} 更多
            </span>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}
