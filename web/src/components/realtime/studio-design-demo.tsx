"use client";

import { useMemo } from "react";
import type { ChatMessage } from "@/types/openai";
import {
  buildDemoMessages,
  buildStudioConversationViewModel,
} from "@/lib/realtime/studio-view-model";
import { cn } from "@/lib/utils";

interface StudioDesignDemoProps {
  messages?: ChatMessage[];
  className?: string;
}

function SchemaCard() {
  const schemaPreview = `type StudioTimelineItem = {
  id: string
  kind: \"user\" | \"assistant\" | \"tool-bundle\" | \"tool-result\" | \"system\"
  title: string
  body: string
  timestampLabel: string
  tools?: ToolInvocationViewModel[]
  attachedAssistantNote?: string
}`;

  return (
    <section className="rounded-2xl border border-[#d7dde8] bg-white/90 p-5 shadow-sm backdrop-blur-sm">
      <p className="text-[11px] uppercase tracking-[0.18em] text-[#6b7280]">
        Step 1
      </p>
      <h2
        className="mt-2 text-2xl font-semibold leading-tight text-[#111827]"
        style={{ fontFamily: '"Space Grotesk", "Noto Sans SC", sans-serif' }}
      >
        Data Structure First
      </h2>
      <p className="mt-2 text-sm leading-6 text-[#4b5563]">
        UI rendering is now based on a single view model instead of raw mixed
        messages. Each timeline block has stable semantics, so tools, assistant
        notes, and user turns can be styled independently.
      </p>
      <pre
        className="mt-4 overflow-x-auto rounded-xl border border-[#d8dee9] bg-[#f7f9fc] p-4 text-xs leading-6 text-[#1f2937]"
        style={{ fontFamily: '"IBM Plex Mono", monospace' }}
      >
        {schemaPreview}
      </pre>
    </section>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[#d4dae6] bg-white px-3 py-2 shadow-sm">
      <p className="text-[11px] uppercase tracking-widest text-[#6b7280]">
        {label}
      </p>
      <p
        className="mt-1 text-xl font-semibold text-[#111827]"
        style={{ fontFamily: '"Space Grotesk", "Noto Sans SC", sans-serif' }}
      >
        {value}
      </p>
    </div>
  );
}

function TimelineChip({ kind }: { kind: string }) {
  const theme =
    kind === "user"
      ? "bg-[#eef2ff] text-[#3730a3] border-[#c7d2fe]"
      : kind === "assistant"
        ? "bg-[#ecfeff] text-[#155e75] border-[#a5f3fc]"
        : kind === "tool-bundle"
          ? "bg-[#fff7ed] text-[#9a3412] border-[#fed7aa]"
          : kind === "tool-result"
            ? "bg-[#f0fdf4] text-[#166534] border-[#bbf7d0]"
            : "bg-[#f3f4f6] text-[#374151] border-[#d1d5db]";

  return (
    <span
      className={cn(
        "rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.12em]",
        theme,
      )}
    >
      {kind}
    </span>
  );
}

function TimelineBoard({ messages }: { messages?: ChatMessage[] }) {
  const sourceMessages =
    messages && messages.length > 0 ? messages : buildDemoMessages();
  const viewModel = useMemo(
    () =>
      buildStudioConversationViewModel(sourceMessages, {
        title: "Agent Runboard",
        subtitle:
          "Card-based timeline with grouped tool execution and attached assistant notes.",
      }),
    [sourceMessages],
  );

  return (
    <section className="rounded-2xl border border-[#d7dde8] bg-white/90 p-5 shadow-sm backdrop-blur-sm">
      <p className="text-[11px] uppercase tracking-[0.18em] text-[#6b7280]">
        Step 2
      </p>
      <div className="mt-2 flex items-end justify-between gap-4">
        <div>
          <h2
            className="text-2xl font-semibold leading-tight text-[#111827]"
            style={{
              fontFamily: '"Space Grotesk", "Noto Sans SC", sans-serif',
            }}
          >
            Design Demo
          </h2>
          <p className="mt-1 text-sm text-[#4b5563]">{viewModel.subtitle}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        {viewModel.metrics.map((metric) => (
          <MetricPill
            key={metric.label}
            label={metric.label}
            value={metric.value}
          />
        ))}
      </div>

      <div className="mt-5 grid gap-3">
        {viewModel.items.map((item, idx) => (
          <article
            key={item.id}
            className="relative overflow-hidden rounded-xl border border-[#d8dee9] bg-gradient-to-br from-white to-[#f8fbff] p-4"
          >
            <div className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-[#0ea5e9] to-[#14b8a6]" />
            <div className="ml-2">
              <div className="flex flex-wrap items-center gap-2">
                <TimelineChip kind={item.kind} />
                <span className="text-[11px] uppercase tracking-[0.14em] text-[#6b7280]">
                  {item.timestampLabel}
                </span>
                <span className="text-[11px] text-[#9ca3af]">#{idx + 1}</span>
              </div>

              <h3
                className="mt-2 text-base font-semibold text-[#111827]"
                style={{
                  fontFamily: '"Space Grotesk", "Noto Sans SC", sans-serif',
                }}
              >
                {item.title}
              </h3>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-[#374151]">
                {item.body || "(empty)"}
              </p>

              {item.tools && item.tools.length > 0 && (
                <div className="mt-3 grid gap-2">
                  {item.tools.map((tool) => (
                    <div
                      key={tool.id}
                      className="rounded-lg border border-[#f0d7b0] bg-[#fffaf2] p-3"
                    >
                      <p className="text-xs font-semibold text-[#9a3412]">
                        {tool.name}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-[#7c2d12]">
                        Args: {tool.argsPreview}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-[#7c2d12]">
                        Result: {tool.resultPreview}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {item.attachedAssistantNote && (
                <div className="mt-3 rounded-lg border border-[#bfdbfe] bg-[#eff6ff] p-3">
                  <p className="text-[11px] uppercase tracking-widest text-[#1d4ed8]">
                    Attached Assistant Note
                  </p>
                  <p className="mt-1 text-sm leading-6 text-[#1e3a8a]">
                    {item.attachedAssistantNote}
                  </p>
                </div>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function StudioDesignDemo({
  messages,
  className,
}: StudioDesignDemoProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-3xl border border-[#d4dae6] p-4 md:p-6",
        "bg-[radial-gradient(circle_at_top_left,_#f0f9ff_0%,_#f8fafc_48%,_#eef2ff_100%)]",
        className,
      )}
    >
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-[#93c5fd]/25 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-12 left-1/4 h-40 w-40 rounded-full bg-[#67e8f9]/30 blur-3xl" />

      <header className="relative mb-4 rounded-2xl border border-[#d7dde8] bg-white/85 p-5 backdrop-blur-sm">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[#6b7280]">
          Realtime Experience Redesign
        </p>
        <h1
          className="mt-2 text-3xl font-semibold leading-tight text-[#0f172a]"
          style={{ fontFamily: '"Space Grotesk", "Noto Sans SC", sans-serif' }}
        >
          Structured Agent Chat Studio
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[#475569]">
          This demo separates conversation data modeling from visual rendering.
          The result is a cleaner timeline, predictable tool grouping, and
          easier UI evolution.
        </p>
      </header>

      <div className="relative grid gap-4">
        <SchemaCard />
        <TimelineBoard messages={messages} />
      </div>
    </div>
  );
}
