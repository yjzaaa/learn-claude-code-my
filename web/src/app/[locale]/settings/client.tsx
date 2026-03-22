"use client";

import "@/styles/globals.css";
import "@/styles/themes/index.css";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Check } from "lucide-react";
import { useUIStore, type Theme, type FontMode } from "@/stores/ui";

// ---- Theme definitions ----

interface ThemeDef {
  id: Theme;
  label: string;
  bg: string;
  accent: string;
}

const THEMES: ThemeDef[] = [
  { id: "midnight",   label: "青夜",   bg: "#2D4356", accent: "#A76F6F" },
  { id: "ocean",      label: "深海",   bg: "#1E3A4C", accent: "#6BA3B8" },
  { id: "forest",     label: "森绿",   bg: "#2C3E30", accent: "#8FA88F" },
  { id: "charcoal",   label: "墨炭",   bg: "#1a1a1a", accent: "#888888" },
  { id: "lavender",   label: "薰衣草", bg: "#3D3856", accent: "#B8A9C9" },
  { id: "sakura",     label: "樱粉",   bg: "#4A3A40", accent: "#E8A8B8" },
  { id: "warm-paper", label: "暖纸",   bg: "#F5F0E8", accent: "#B85C4F" },
];

// ---- Component ----

export function SettingsClient() {
  const params = useParams();
  const locale = (params?.locale as string) || "zh";
  const { theme, setTheme, fontMode, setFontMode } = useUIStore();

  return (
    <div
      data-theme={theme}
      style={{
        minHeight: "100vh",
        background: "var(--bg)",
        color: "var(--text)",
        fontFamily: "var(--font-ui)",
      }}
    >
      {/* Header */}
      <div
        style={{
          height: "var(--titlebar-height)",
          display: "flex",
          alignItems: "center",
          gap: "var(--space-md)",
          padding: "0 var(--space-lg)",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-glass)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <Link
          href={`/${locale}/chat`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            color: "var(--text-light)",
            textDecoration: "none",
            fontSize: 13,
            transition: "color var(--duration) var(--ease-out)",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.color = "var(--text)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.color = "var(--text-light)";
          }}
        >
          <ArrowLeft size={14} />
          返回对话
        </Link>

        <span
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: "var(--text)",
            marginLeft: "var(--space-sm)",
          }}
        >
          设置
        </span>
      </div>

      {/* Content */}
      <div
        style={{
          maxWidth: 640,
          margin: "0 auto",
          padding: "var(--space-xl) var(--space-lg)",
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-xl)",
        }}
      >
        {/* Theme section */}
        <SettingSection title="外观主题">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(100px, 1fr))",
              gap: "var(--space-sm)",
            }}
          >
            {THEMES.map((t) => (
              <ThemeSwatch
                key={t.id}
                def={t}
                active={theme === t.id}
                onSelect={() => setTheme(t.id)}
              />
            ))}
          </div>
        </SettingSection>

        {/* Font mode section */}
        <SettingSection title="字体风格">
          <div style={{ display: "flex", gap: "var(--space-sm)" }}>
            {(["serif", "sans"] as FontMode[]).map((mode) => (
              <ToggleButton
                key={mode}
                active={fontMode === mode}
                onClick={() => setFontMode(mode)}
              >
                <span
                  style={{
                    fontFamily:
                      mode === "serif"
                        ? "var(--font-serif)"
                        : "var(--font-ui)",
                    fontSize: 15,
                    marginRight: 6,
                  }}
                >
                  Aa
                </span>
                {mode === "serif" ? "衬线体" : "无衬线"}
              </ToggleButton>
            ))}
          </div>
        </SettingSection>

        {/* About section */}
        <SettingSection title="关于">
          <div
            style={{
              fontSize: 13,
              color: "var(--text-muted)",
              lineHeight: 1.8,
            }}
          >
            <div>Hana Chat · 基于 OpenHanako 设计系统</div>
            <div>前端框架: Next.js 15 + React 19 + Zustand 5</div>
          </div>
        </SettingSection>
      </div>
    </div>
  );
}

// ---- Sub-components ----

function SettingSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h2
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
          marginBottom: "var(--space-md)",
        }}
      >
        {title}
      </h2>
      {children}
    </div>
  );
}

function ThemeSwatch({
  def,
  active,
  onSelect,
}: {
  def: ThemeDef;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "8px",
        padding: "12px 8px",
        borderRadius: "var(--radius-md)",
        border: active
          ? `2px solid ${def.accent}`
          : "2px solid transparent",
        background: active ? "var(--overlay-medium)" : "var(--overlay-subtle)",
        cursor: "pointer",
        transition: "all var(--duration) var(--ease-out)",
        position: "relative",
      }}
      onMouseEnter={(e) => {
        if (!active)
          (e.currentTarget as HTMLElement).style.background =
            "var(--overlay-light)";
      }}
      onMouseLeave={(e) => {
        if (!active)
          (e.currentTarget as HTMLElement).style.background =
            "var(--overlay-subtle)";
      }}
    >
      {/* Color preview circle */}
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: "50%",
          background: def.bg,
          border: `3px solid ${def.accent}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        {active && <Check size={16} color={def.accent} strokeWidth={2.5} />}
      </div>

      <span
        style={{
          fontSize: 12,
          color: active ? "var(--text)" : "var(--text-light)",
          whiteSpace: "nowrap",
        }}
      >
        {def.label}
      </span>
    </button>
  );
}

function ToggleButton({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        padding: "10px 20px",
        borderRadius: "var(--radius-md)",
        border: active
          ? "2px solid var(--accent)"
          : "2px solid var(--overlay-light)",
        background: active ? "var(--accent-light)" : "var(--overlay-subtle)",
        color: active ? "var(--accent)" : "var(--text-light)",
        cursor: "pointer",
        fontSize: 14,
        fontWeight: active ? 500 : 400,
        transition: "all var(--duration) var(--ease-out)",
      }}
    >
      {children}
    </button>
  );
}
