"use client";

import { useState, useCallback } from "react";
import type { MemoryType } from "@/hooks/useMemory";

export interface MemoryFormData {
  name: string;
  description: string;
  type: MemoryType;
  content: string;
}

export interface MemoryDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: MemoryFormData) => Promise<void>;
  isLoading?: boolean;
}

const MEMORY_TYPES: { value: MemoryType; label: string; color: string }[] = [
  { value: "user", label: "用户", color: "#4CAF50" },
  { value: "project", label: "项目", color: "#2196F3" },
  { value: "reference", label: "参考", color: "#9C27B0" },
  { value: "feedback", label: "反馈", color: "#FF9800" },
];

export function MemoryDialog({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}: MemoryDialogProps) {
  const [formData, setFormData] = useState<MemoryFormData>({
    name: "",
    description: "",
    type: "user",
    content: "",
  });

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!formData.name.trim() || !formData.content.trim()) return;
      await onSubmit(formData);
      setFormData({ name: "", description: "", type: "user", content: "" });
      onClose();
    },
    [formData, onSubmit, onClose],
  );

  const handleChange = useCallback(
    (field: keyof MemoryFormData, value: string) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0, 0, 0, 0.5)",
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: "480px",
          maxWidth: "90vw",
          maxHeight: "90vh",
          overflow: "auto",
          background: "var(--bg-card)",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border)",
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.15)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: "var(--space-md) var(--space-lg)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: "var(--text)",
            }}
          >
            添加记忆
          </span>
          <button
            onClick={onClose}
            style={{
              width: 28,
              height: 28,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "none",
              background: "transparent",
              color: "var(--text-light)",
              cursor: "pointer",
              borderRadius: "var(--radius-sm)",
            }}
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div
            style={{
              padding: "var(--space-lg)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-md)",
            }}
          >
            {/* Name */}
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 500,
                  color: "var(--text)",
                  marginBottom: "var(--space-xs)",
                }}
              >
                名称 <span style={{ color: "#ff4444" }}>*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange("name", e.target.value)}
                placeholder="输入记忆名称"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  fontSize: 14,
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  color: "var(--text)",
                  outline: "none",
                }}
                required
              />
            </div>

            {/* Type */}
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 500,
                  color: "var(--text)",
                  marginBottom: "var(--space-xs)",
                }}
              >
                类型
              </label>
              <div style={{ display: "flex", gap: "var(--space-sm)" }}>
                {MEMORY_TYPES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => handleChange("type", t.value)}
                    style={{
                      padding: "6px 12px",
                      fontSize: 12,
                      border: "1px solid",
                      borderColor:
                        formData.type === t.value
                          ? t.color
                          : "var(--border)",
                      borderRadius: "var(--radius-sm)",
                      background:
                        formData.type === t.value
                          ? `${t.color}20`
                          : "var(--bg)",
                      color:
                        formData.type === t.value ? t.color : "var(--text-light)",
                      cursor: "pointer",
                      transition: "all var(--duration) var(--ease-out)",
                    }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Description */}
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 500,
                  color: "var(--text)",
                  marginBottom: "var(--space-xs)",
                }}
              >
                描述
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => handleChange("description", e.target.value)}
                placeholder="简短描述这条记忆"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  fontSize: 14,
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  color: "var(--text)",
                  outline: "none",
                }}
              />
            </div>

            {/* Content */}
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 500,
                  color: "var(--text)",
                  marginBottom: "var(--space-xs)",
                }}
              >
                内容 <span style={{ color: "#ff4444" }}>*</span>
              </label>
              <textarea
                value={formData.content}
                onChange={(e) => handleChange("content", e.target.value)}
                placeholder="输入记忆内容"
                rows={6}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  fontSize: 14,
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  color: "var(--text)",
                  outline: "none",
                  resize: "vertical",
                  fontFamily: "inherit",
                  lineHeight: 1.5,
                }}
                required
              />
            </div>
          </div>

          {/* Actions */}
          <div
            style={{
              padding: "var(--space-md) var(--space-lg)",
              borderTop: "1px solid var(--border)",
              display: "flex",
              justifyContent: "flex-end",
              gap: "var(--space-sm)",
            }}
          >
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "8px 16px",
                fontSize: 13,
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                background: "var(--bg)",
                color: "var(--text-light)",
                cursor: "pointer",
              }}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={
                isLoading ||
                !formData.name.trim() ||
                !formData.content.trim()
              }
              style={{
                padding: "8px 16px",
                fontSize: 13,
                border: "none",
                borderRadius: "var(--radius-sm)",
                background: "var(--accent)",
                color: "#fff",
                cursor:
                  isLoading || !formData.name.trim() || !formData.content.trim()
                    ? "not-allowed"
                    : "pointer",
                opacity:
                  isLoading || !formData.name.trim() || !formData.content.trim()
                    ? 0.6
                    : 1,
              }}
            >
              {isLoading ? "保存中..." : "保存"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
