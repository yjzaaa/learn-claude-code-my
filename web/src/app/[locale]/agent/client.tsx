"use client";

import { useTranslations } from "@/lib/i18n";
import { EmbeddedDialog } from "@/components/realtime";

/**
 * Agent 实时对话页面客户端组件
 *
 * 功能：
 * - 提供与 AI Agent 的实时交互界面
 * - 展示嵌入式对话组件（EmbeddedDialog）
 * - 显示工作原理说明
 *
 * 使用 i18n 支持多语言（中文/英文/日文）
 */
export function AgentPageClient() {
  // 获取 agent 命名空间的翻译函数
  const t = useTranslations("agent");

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      {/* 页面标题区域 */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          {t("title")}
        </h1>
        <p className="mt-3 text-[var(--color-text-secondary)]">
          {t("subtitle")}
        </p>
      </div>

      {/* 嵌入式实时对话组件 */}
      <EmbeddedDialog className="h-[700px]" />

      {/* 工作原理说明卡片 */}
      <div className="mt-8 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-6">
        <h2 className="mb-4 text-lg font-semibold">{t("how_it_works")}</h2>
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>{t("description_1")}</p>
          <p>{t("description_2")}</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>{t("feature_1")}</li>
            <li>{t("feature_2")}</li>
            <li>{t("feature_3")}</li>
            <li>{t("feature_4")}</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
