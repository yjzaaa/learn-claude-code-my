"use client";

/** File Attachment - 文件附件组件 */

import type { FileAttachmentProps } from "./types";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileAttachment({ files, onRemove }: FileAttachmentProps) {
  if (files.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "6px",
        marginBottom: "8px",
      }}
    >
      {files.map((file) => (
        <div
          key={file.id}
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
          {!file.dataUrl && (
            <svg
              style={{ width: 16, height: 16, color: "var(--text-muted)" }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
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
            onClick={() => onRemove(file.id)}
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
            <svg
              style={{ width: 12, height: 12 }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}

export default FileAttachment;
