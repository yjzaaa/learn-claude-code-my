"use client";

import Link from "next/link";
import { useTranslations, useLocale } from "@/lib/i18n";
import { LEARNING_PATH, VERSION_META, LAYERS } from "@/lib/constants";
import { LayerBadge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import versionsData from "@/data/generated/versions.json";
import { MessageFlow } from "@/components/architecture/message-flow";
import { EmbeddedDialog } from "@/components/realtime";

const LAYER_BORDER_COLORS = {
  tools: "border-blue-500/30 hover:border-blue-500/60",
  planning: "border-emerald-500/30 hover:border-emerald-500/60",
  memory: "border-purple-500/30 hover:border-purple-500/60",
  concurrency: "border-amber-500/30 hover:border-amber-500/60",
  collaboration: "border-red-500/30 hover:border-red-500/60",
};

const LAYER_BAR_COLORS = {
  tools: "bg-blue-500",
  planning: "bg-emerald-500",
  memory: "bg-purple-500",
  concurrency: "bg-amber-500",
  collaboration: "bg-red-500",
};

function getVersionData(id: string) {
  return versionsData.versions.find((v) => v.id === id);
}

export function HomeClient() {
  const t = useTranslations("home");
  const locale = useLocale();

  return (
    <div className="flex flex-col gap-20 pb-16">
      <section className="flex flex-col items-center px-2 pt-8 text-center sm:pt-20">
        <h1 className="text-3xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          {t("hero_title")}
        </h1>
        <p className="mt-4 max-w-2xl text-base text-[var(--color-text-secondary)] sm:text-xl">
          {t("hero_subtitle")}
        </p>
        <div className="mt-8">
          <Link
            href={`/${locale}/timeline`}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {t("start")}
            <span aria-hidden="true">&rarr;</span>
          </Link>
        </div>
      </section>

      <section>
        <div className="mb-6 text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">
            {t("core_pattern")}
          </h2>
          <p className="mt-2 text-[var(--color-text-secondary)]">
            {t("core_pattern_desc")}
          </p>
        </div>
      </section>

      <section>
        <div className="mb-6 text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">
            {t("learning_path")}
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {LEARNING_PATH.map((versionId) => {
            const meta = VERSION_META[versionId];
            const data = getVersionData(versionId);
            if (!meta || !data) return null;
            return (
              <Link
                key={versionId}
                href={`/${locale}/${versionId}`}
                className="group block"
              >
                <Card>{meta.title}</Card>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
