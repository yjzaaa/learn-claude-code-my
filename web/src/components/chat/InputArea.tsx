"use client";

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type KeyboardEvent,
  type ClipboardEvent,
  type ChangeEvent,
} from "react";
import { Send, Square, Brain, Zap, Bot, ChevronDown, X } from "lucide-react";

// ---- Types ----

export type ThinkingLevel = "none" | "brief" | "full";

export interface SendOptions {
  thinkingLevel: ThinkingLevel;
  model: string;
  planMode: boolean;
}

export interface FileAttachment {
  name: string;
  mimeType: string;
  size: number;
  dataUrl?: string;
}

export interface InputAreaProps {
  dialogId: string;
  isStreaming?: boolean;
  onSend: (content: string, options: SendOptions) => Promise<void>;
  onStop?: () => void;
}

// ---- Constants ----

const SLASH_COMMANDS = [
  { name: "compact", description: "压缩对话上下文" },
  { name: "diary", description: "写今日日记" },
  { name: "think", description: "开启深度思考" },
  { name: "clear", description: "清除对话历史" },
  { name: "help", description: "查看可用命令" },
];

const MODELS = [
  { id: "claude-opus-4-6", label: "Opus 4.6" },
  { id: "claude-sonnet-4-6", label: "Sonnet 4.6" },
  { id: "claude-haiku-4-5-20251001", label: "Haiku 4.5" },
];

const THINKING_LABELS: Record<ThinkingLevel, string> = {
  none: "不思考",
  brief: "简单思考",
  full: "深度思考",
};

// ---- Component ----

export function InputArea({
  isStreaming = false,
  onSend,
  onStop,
}: InputAreaProps) {
  const [inputText, setInputText] = useState("");
  const [planMode, setPlanMode] = useState(false);
  const [thinkingLevel, setThinkingLevel] = useState<ThinkingLevel>("brief");
  const [model, setModel] = useState(MODELS[1].id);
  const [attachedFiles, setAttachedFiles] = useState<FileAttachment[]>([]);
  const [slashMenuOpen, setSlashMenuOpen] = useState(false);
  const [slashMenuIndex, setSlashMenuIndex] = useState(0);
  const [slashFilter, setSlashFilter] = useState("");
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [thinkMenuOpen, setThinkMenuOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [inputText]);

  const filteredCommands = SLASH_COMMANDS.filter((cmd) =>
    cmd.name.startsWith(slashFilter),
  );

  const handleInput = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInputText(val);

    const cursor = e.target.selectionStart ?? val.length;
    const textBeforeCursor = val.slice(0, cursor);
    const slashMatch = textBeforeCursor.match(/(?:^|\s)\/(\w*)$/);
    if (slashMatch) {
      setSlashFilter(slashMatch[1]);
      setSlashMenuOpen(true);
      setSlashMenuIndex(0);
    } else {
      setSlashMenuOpen(false);
    }
  }, []);

  const applySlashCommand = useCallback((cmdName: string) => {
    setInputText(`/${cmdName} `);
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
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (slashMenuOpen) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSlashMenuIndex((i) => Math.min(i + 1, filteredCommands.length - 1));
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setSlashMenuIndex((i) => Math.max(i - 1, 0));
          return;
        }
        if (e.key === "Tab" || e.key === "Enter") {
          e.preventDefault();
          if (filteredCommands[slashMenuIndex]) {
            applySlashCommand(filteredCommands[slashMenuIndex].name);
          }
          return;
        }
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
    [slashMenuOpen, slashMenuIndex, filteredCommands, applySlashCommand, handleSubmit],
  );

  const handlePaste = useCallback((e: ClipboardEvent<HTMLTextAreaElement>) => {
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

  const removeFile = useCallback((index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const currentModel = MODELS.find((m) => m.id === model) ?? MODELS[1];
  const isSendDisabled = !isStreaming && (!inputText.trim() || isSending);

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
      {slashMenuOpen && filteredCommands.length > 0 && (
        <div
          style={{
            position: "absolute",
            bottom: "100%",
            left: "var(--space-md)",
            right: "var(--space-md)",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            padding: "4px",
            marginBottom: "8px",
            boxShadow: "0 8px 24px var(--shadow)",
            zIndex: 100,
          }}
        >
          {filteredCommands.map((cmd, i) => (
            <button
              key={cmd.name}
              onMouseDown={(e) => {
                e.preventDefault();
                applySlashCommand(cmd.name);
              }}
              onMouseEnter={() => setSlashMenuIndex(i)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                width: "100%",
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                background:
                  i === slashMenuIndex
                    ? "var(--overlay-medium)"
                    : "transparent",
                border: "none",
                cursor: "pointer",
                textAlign: "left",
                color: "var(--text)",
              }}
            >
              <span
                style={{
                  color: "var(--accent)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "13px",
                  minWidth: "80px",
                }}
              >
                /{cmd.name}
              </span>
              <span style={{ color: "var(--text-light)", fontSize: "13px" }}>
                {cmd.description}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Attached files */}
      {attachedFiles.length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "6px",
            marginBottom: "8px",
          }}
        >
          {attachedFiles.map((file, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "4px 10px",
                background: "var(--overlay-medium)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                color: "var(--text-light)",
              }}
            >
              {file.dataUrl && (
                <img
                  src={file.dataUrl}
                  alt=""
                  style={{
                    width: 20,
                    height: 20,
                    objectFit: "cover",
                    borderRadius: 2,
                  }}
                />
              )}
              <span
                style={{
                  maxWidth: 120,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {file.name}
              </span>
              <button
                onClick={() => removeFile(i)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: 2,
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  color: "var(--text-muted)",
                  lineHeight: 1,
                }}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

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

          <div style={{ position: "relative" }}>
            <ToolBtn
              active={thinkingLevel !== "none"}
              onClick={() => {
                setThinkMenuOpen((o) => !o);
                setModelMenuOpen(false);
              }}
              title="推理深度"
            >
              <Brain size={13} />
              <span>{THINKING_LABELS[thinkingLevel]}</span>
              <ChevronDown size={10} />
            </ToolBtn>
            {thinkMenuOpen && (
              <PopupMenu
                onClose={() => setThinkMenuOpen(false)}
                align="left"
              >
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
            <ToolBtn
              onClick={() => {
                setModelMenuOpen((o) => !o);
                setThinkMenuOpen(false);
              }}
              title="选择模型"
            >
              <Zap size={13} />
              <span>{currentModel.label}</span>
              <ChevronDown size={10} />
            </ToolBtn>
            {modelMenuOpen && (
              <PopupMenu
                onClose={() => setModelMenuOpen(false)}
                align="right"
              >
                {MODELS.map((m) => (
                  <PopupItem
                    key={m.id}
                    active={model === m.id}
                    onClick={() => {
                      setModel(m.id);
                      setModelMenuOpen(false);
                    }}
                  >
                    {m.label}
                  </PopupItem>
                ))}
              </PopupMenu>
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
              transition:
                "opacity var(--duration) var(--ease-out), background var(--duration) var(--ease-out)",
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
        border: active
          ? "1px solid var(--accent)"
          : "1px solid var(--overlay-light)",
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
  onClose,
  align = "left",
}: {
  children: React.ReactNode;
  onClose: () => void;
  align?: "left" | "right";
}) {
  useEffect(() => {
    const handler = () => onClose();
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      onMouseDown={(e) => e.stopPropagation()}
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
        if (!active)
          (e.currentTarget as HTMLElement).style.background =
            "var(--overlay-medium)";
      }}
      onMouseLeave={(e) => {
        if (!active)
          (e.currentTarget as HTMLElement).style.background = "transparent";
      }}
    >
      {children}
    </button>
  );
}
