"use client";

/**
 * InputArea - 输入区域主组件 (重构版)
 *
 * 使用拆分后的子组件:
 * - ModelSelector: 模型选择器
 * - SlashCommandMenu: 斜杠命令菜单
 * - FileAttachment: 文件附件展示
 */

import {
  useState,
  useRef,
  useCallback,
  useEffect,
} from "react";
import { Send, Square, Brain, Zap, Bot, ChevronDown } from "lucide-react";
import { useAgentStore } from "@/agent/agent-store";
import { ModelSelector } from "./ModelSelector";
import { SlashCommandMenu } from "./SlashCommandMenu";
import { FileAttachment } from "./FileAttachment";
import type {
  ModelOption,
  SlashCommand,
  FileAttachment as FileAttachmentType,
  ThinkingLevel,
  SendOptions,
} from "./types";

// ---- Constants ----

const SLASH_COMMANDS: SlashCommand[] = [
  { id: "compact", label: "compact", description: "压缩对话上下文" },
  { id: "diary", label: "diary", description: "写今日日记" },
  { id: "think", label: "think", description: "开启深度思考" },
  { id: "clear", label: "clear", description: "清除对话历史" },
  { id: "help", label: "help", description: "查看可用命令" },
];

const THINKING_LABELS: Record<ThinkingLevel, string> = {
  none: "不思考",
  brief: "简单思考",
  full: "深度思考",
};

// ---- Component ----

export interface InputAreaProps {
  dialogId: string;
  isStreaming?: boolean;
  onSend: (content: string, options: SendOptions) => Promise<void>;
  onStop?: () => void;
}

export function InputArea({
  dialogId,
  isStreaming = false,
  onSend,
  onStop,
}: InputAreaProps) {
  const currentSnapshot = useAgentStore((s) =>
    s.currentSnapshot?.id === dialogId ? s.currentSnapshot : null
  );

  const [inputText, setInputText] = useState("");
  const [planMode, setPlanMode] = useState(false);
  const [thinkingLevel, setThinkingLevel] = useState<ThinkingLevel>("brief");
  const [model, setModel] = useState<string>("");
  const [models, setModels] = useState<ModelOption[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [activeModelLabel, setActiveModelLabel] = useState<string>("Loading...");
  const [attachedFiles, setAttachedFiles] = useState<FileAttachmentType[]>([]);
  const [slashMenuOpen, setSlashMenuOpen] = useState(false);
  const [slashFilter, setSlashFilter] = useState("");
  const [thinkMenuOpen, setThinkMenuOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isSwitchingModel, setIsSwitchingModel] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const thinkMenuRef = useRef<HTMLDivElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [inputText]);

  // Fetch available models from backend on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch("http://localhost:8001/api/config/models");
        if (!res.ok) throw new Error("Failed to fetch models");
        const result = await res.json();
        if (result.success && result.data?.available_models?.length > 0) {
          const availableModels: ModelOption[] = result.data.available_models.map(
            (m: { id: string; label: string; provider: string }) => ({
              id: m.id,
              label: m.label,
              provider: m.provider,
            })
          );
          setModels(availableModels);
          const currentActiveModel = result.data.model;
          const modelToUse = availableModels.find((m) => m.id === currentActiveModel)
            ? currentActiveModel
            : availableModels[0].id;
          setModel(modelToUse);
        } else {
          console.warn("[InputArea] No models available from backend");
          setModels([]);
          setModel("");
        }
      } catch (err) {
        console.error("[InputArea] Failed to fetch models:", err);
        setModels([]);
        setModel("");
      } finally {
        setModelsLoading(false);
      }
    };

    fetchModels();
  }, []);

  // Get model from dialog's selected_model_id
  useEffect(() => {
    const modelFromBackend = currentSnapshot?.selected_model_id || currentSnapshot?.metadata?.model;
    if (!modelFromBackend) return;

    setModel(modelFromBackend);

    const found = models.find((m) => m.id === modelFromBackend);
    if (found) {
      setActiveModelLabel(found.label);
    } else {
      const formatted = modelFromBackend
        .replace(/^[^/]+\//, "")
        .split("-")
        .slice(0, 3)
        .join("-");
      setActiveModelLabel(formatted);
    }
  }, [currentSnapshot?.selected_model_id, currentSnapshot?.metadata?.model, models]);

  // Click outside handler for think menu
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (thinkMenuRef.current && !thinkMenuRef.current.contains(e.target as Node)) {
        setThinkMenuOpen(false);
      }
    };
    if (thinkMenuOpen) {
      document.addEventListener("mousedown", handler);
    }
    return () => document.removeEventListener("mousedown", handler);
  }, [thinkMenuOpen]);

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInputText(val);

    const cursor = e.target.selectionStart ?? val.length;
    const textBeforeCursor = val.slice(0, cursor);
    const slashMatch = textBeforeCursor.match(/(?:^|\s)\/(\w*)$/);
    if (slashMatch) {
      setSlashFilter(slashMatch[1]);
      setSlashMenuOpen(true);
    } else {
      setSlashMenuOpen(false);
    }
  }, []);

  const applySlashCommand = useCallback((cmdLabel: string) => {
    setInputText(`/${cmdLabel} `);
    setSlashMenuOpen(false);
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = useCallback(async () => {
    if (isStreaming) {
      onStop?.();
      return;
    }
    const content = inputText.trim();
    if (!content || isSending) return;

    setIsSending(true);
    try {
      await onSend(content, { thinkingLevel, model, planMode });
      setInputText("");
      setAttachedFiles([]);
    } finally {
      setIsSending(false);
    }
  }, [isStreaming, inputText, isSending, onSend, onStop, thinkingLevel, model, planMode]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (slashMenuOpen) {
        if (e.key === "Escape") {
          setSlashMenuOpen(false);
          return;
        }
      }

      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [slashMenuOpen, handleSubmit]
  );

  const handlePaste = useCallback((e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData.items);
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (!file) continue;
        const reader = new FileReader();
        reader.onload = (ev) => {
          setAttachedFiles((prev) => [
            ...prev,
            {
              id: `img-${Date.now()}`,
              name: `image-${Date.now()}.png`,
              mimeType: file.type,
              size: file.size,
              dataUrl: ev.target?.result as string,
            },
          ]);
        };
        reader.readAsDataURL(file);
      }
    }
  }, []);

  const removeFile = useCallback((fileId: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  const handleModelChange = useCallback(
    async (modelId: string) => {
      if (modelId === model) return;

      setIsSwitchingModel(true);
      setModelError(null);
      try {
        const res = await fetch(`http://localhost:8001/api/dialogs/${dialogId}/model`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model_id: modelId }),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error?.message || "Failed to switch model");
        }
        setModel(modelId);
        const found = models.find((m) => m.id === modelId);
        if (found) setActiveModelLabel(found.label);
      } catch (err: any) {
        console.error("[InputArea] Failed to switch model:", err);
        setModelError(err.message || "Failed to switch model");
      } finally {
        setIsSwitchingModel(false);
      }
    },
    [dialogId, model, models]
  );

  const currentModel = models.find((m) => m.id === model);
  const displayLabel = modelsLoading
    ? "加载中..."
    : isSwitchingModel
    ? "切换中..."
    : currentModel?.label || activeModelLabel || model || "无可用模型";

  const isSendDisabled = !isStreaming && (!inputText.trim() || isSending || !model || isSwitchingModel);

  // Filter slash commands
  const filteredCommands = SLASH_COMMANDS.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(slashFilter.toLowerCase()) ||
      cmd.description.toLowerCase().includes(slashFilter.toLowerCase())
  );

  return (
    <div
      style={{
        position: "relative",
        background: "var(--bg-glass)",
        backdropFilter: "blur(20px)",
        borderTop: "1px solid var(--overlay-light)",
        padding: "var(--space-md)",
      }}
    >
      {/* Slash command popup */}
      <SlashCommandMenu
        isOpen={slashMenuOpen && filteredCommands.length > 0}
        query={slashFilter}
        commands={filteredCommands}
        onSelect={(cmd) => applySlashCommand(cmd.label)}
        onClose={() => setSlashMenuOpen(false)}
      />

      {/* Attached files */}
      <FileAttachment files={attachedFiles} onRemove={removeFile} />

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={inputText}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        placeholder="发消息… (/ 触发命令，Shift+Enter 换行)"
        rows={1}
        style={{
          width: "100%",
          minHeight: "44px",
          maxHeight: "200px",
          background: "var(--overlay-subtle)",
          border: "1px solid var(--overlay-light)",
          borderRadius: "var(--radius-md)",
          padding: "10px 14px",
          color: "var(--text)",
          fontSize: "15px",
          lineHeight: "1.7",
          resize: "none",
          outline: "none",
          fontFamily: "var(--font-ui)",
          transition: "border-color var(--duration) var(--ease-out)",
          boxSizing: "border-box",
          display: "block",
          overflowY: "auto",
        }}
        onFocus={(e) => {
          e.target.style.borderColor = "var(--accent)";
        }}
        onBlur={(e) => {
          e.target.style.borderColor = "var(--overlay-light)";
        }}
      />

      {/* Bottom toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: "8px",
          gap: "6px",
        }}
      >
        {/* Left: plan mode + thinking level */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <ToolBtn
            active={planMode}
            onClick={() => setPlanMode((p) => !p)}
            title="操作电脑模式"
          >
            <Bot size={13} />
            <span>计划模式</span>
          </ToolBtn>

          <div style={{ position: "relative" }} ref={thinkMenuRef}>
            <ToolBtn
              active={thinkingLevel !== "none"}
              onClick={() => setThinkMenuOpen((o) => !o)}
              title="推理深度"
            >
              <Brain size={13} />
              <span>{THINKING_LABELS[thinkingLevel]}</span>
              <ChevronDown size={10} />
            </ToolBtn>
            {thinkMenuOpen && (
              <PopupMenu align="left">
                {(["none", "brief", "full"] as ThinkingLevel[]).map((level) => (
                  <PopupItem
                    key={level}
                    active={thinkingLevel === level}
                    onClick={() => {
                      setThinkingLevel(level);
                      setThinkMenuOpen(false);
                    }}
                  >
                    {THINKING_LABELS[level]}
                  </PopupItem>
                ))}
              </PopupMenu>
            )}
          </div>
        </div>

        {/* Right: model selector + send */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <div style={{ position: "relative" }}>
            {modelError && (
              <div
                style={{
                  position: "absolute",
                  bottom: "calc(100% + 4px)",
                  right: 0,
                  background: "var(--danger)",
                  color: "#fff",
                  padding: "4px 8px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "12px",
                  whiteSpace: "nowrap",
                  zIndex: 101,
                }}
              >
                {modelError}
                <button
                  onClick={() => setModelError(null)}
                  style={{
                    marginLeft: "6px",
                    background: "transparent",
                    border: "none",
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  ×
                </button>
              </div>
            )}

            <ToolBtn
              onClick={() => {
                if (modelsLoading || models.length === 0 || isSwitchingModel) return;
                // Model selector is handled by ModelSelector component
              }}
              title={modelsLoading ? "加载中..." : models.length === 0 ? "无可用模型" : "选择模型"}
            >
              <Zap size={13} />
              <span>{displayLabel}</span>
              {!modelsLoading && !isSwitchingModel && models.length > 0 && <ChevronDown size={10} />}
              {isSwitchingModel && <span style={{ marginLeft: "4px", fontSize: "10px" }}>⏳</span>}
            </ToolBtn>

            {/* Model Selector Dropdown */}
            {!modelsLoading && models.length > 0 && (
              <ModelSelector
                selected={model}
                options={models}
                onChange={handleModelChange}
                disabled={isSwitchingModel}
              />
            )}
          </div>

          {/* Send / Stop */}
          <button
            onClick={handleSubmit}
            disabled={isSendDisabled}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 16px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              cursor: isSendDisabled ? "not-allowed" : "pointer",
              background: isStreaming ? "var(--danger)" : "var(--accent)",
              color: "#fff",
              fontSize: "13px",
              fontWeight: 500,
              opacity: isSendDisabled ? 0.45 : 1,
              transition: "opacity var(--duration) var(--ease-out), background var(--duration) var(--ease-out)",
            }}
          >
            {isStreaming ? (
              <>
                <Square size={13} />
                <span>停止</span>
              </>
            ) : (
              <>
                <Send size={13} />
                <span>发送</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Sub-components ----

function ToolBtn({
  children,
  active = false,
  onClick,
  title,
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        padding: "5px 9px",
        borderRadius: "var(--radius-sm)",
        border: active ? "1px solid var(--accent)" : "1px solid var(--overlay-light)",
        background: active ? "var(--accent-light)" : "transparent",
        color: active ? "var(--accent)" : "var(--text-light)",
        cursor: "pointer",
        fontSize: "12px",
        transition: "all var(--duration) var(--ease-out)",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </button>
  );
}

function PopupMenu({
  children,
  align = "left",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  return (
    <div
      style={{
        position: "absolute",
        bottom: "calc(100% + 6px)",
        ...(align === "right" ? { right: 0 } : { left: 0 }),
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: "4px",
        minWidth: "130px",
        boxShadow: "0 8px 24px var(--shadow)",
        zIndex: 100,
      }}
    >
      {children}
    </div>
  );
}

function PopupItem({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      onMouseDown={(e) => e.stopPropagation()}
      style={{
        display: "flex",
        alignItems: "center",
        width: "100%",
        padding: "7px 12px",
        borderRadius: "var(--radius-sm)",
        background: active ? "var(--accent-light)" : "transparent",
        border: "none",
        cursor: "pointer",
        textAlign: "left",
        color: active ? "var(--accent)" : "var(--text)",
        fontSize: "13px",
        transition: "background var(--duration) var(--ease-out)",
      }}
      onMouseEnter={(e) => {
        if (!active) (e.currentTarget as HTMLElement).style.background = "var(--overlay-medium)";
      }}
      onMouseLeave={(e) => {
        if (!active) (e.currentTarget as HTMLElement).style.background = "transparent";
      }}
    >
      {children}
    </button>
  );
}
