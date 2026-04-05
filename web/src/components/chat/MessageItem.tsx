"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Message } from "@/types/dialog";

// ---- Types ----

export interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
}

// ---- Main component ----

export function MessageItem({ message, isStreaming }: MessageItemProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const isTool = message.role === "tool";

  const content =
    typeof message.content === "string" ? message.content : "";

  // System messages are hidden from the chat bubble view
  if (isSystem) return null;

  // Tool output — compact monospace block
  if (isTool) {
    return (
      <div
        style={{
          margin: "2px var(--space-md)",
          padding: "6px 12px",
          background: "var(--overlay-subtle)",
          borderLeft: "2px solid var(--overlay-strong)",
          borderRadius: "0 var(--radius-sm) var(--radius-sm) 0",
          fontSize: "12px",
          color: "var(--text-muted)",
          fontFamily: "var(--font-mono)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
        }}
      >
        {content}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start",
        padding: "6px var(--space-md)",
        gap: "4px",
      }}
    >
      {/* Label */}
      <span
        style={{
          fontSize: "11px",
          color: "var(--text-muted)",
          fontFamily: "var(--font-ui)",
          userSelect: "none",
        }}
      >
        {isUser ? "你" : "Hana"}
      </span>

      {/* Bubble */}
      <div
        style={{
          maxWidth: "82%",
          padding: "10px 14px",
          borderRadius: isUser
            ? "var(--radius-lg) var(--radius-md) var(--radius-sm) var(--radius-lg)"
            : "var(--radius-md) var(--radius-lg) var(--radius-lg) var(--radius-sm)",
          background: isUser ? "var(--accent)" : "var(--bg-card)",
          color: isUser ? "#fff" : "var(--text)",
          border: isUser ? "none" : "1px solid var(--overlay-light)",
          fontSize: "14px",
          lineHeight: "1.7",
          wordBreak: "break-word",
          overflowWrap: "break-word",
        }}
      >
        {/* Reasoning content (thinking process) */}
        {!isUser && message.reasoning_content && (
          <ReasoningContent content={message.reasoning_content} />
        )}

        {isUser ? (
          <span style={{ whiteSpace: "pre-wrap" }}>{content}</span>
        ) : (
          <MarkdownContent content={content} isStreaming={isStreaming} />
        )}

        {/* Model info footer for assistant messages */}
        {!isUser && (message.model || message.provider) && (
          <ModelInfoFooter
            model={message.model}
            provider={message.provider}
            usage={message.usage}
          />
        )}
      </div>
    </div>
  );
}

// ---- Markdown renderer ----

function MarkdownContent({
  content,
  isStreaming,
}: {
  content: string;
  isStreaming?: boolean;
}) {
  return (
    <div>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          code: ({ node, inline, className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";
            const code = String(children).replace(/\n$/, "");

            if (inline || !language) {
              return (
                <code
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.875em",
                    padding: "1px 5px",
                    borderRadius: "4px",
                    background: "var(--overlay-medium)",
                    color: "var(--coral)",
                  }}
                  {...props}
                >
                  {children}
                </code>
              );
            }

            return <CodeBlock code={code} language={language} />;
          },
          pre: ({ children }) => <>{children}</>,
          p: ({ children }) => (
            <p style={{ margin: "0 0 8px 0" }}>{children}</p>
          ),
          ul: ({ children }) => (
            <ul style={{ margin: "4px 0", paddingLeft: "20px" }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: "4px 0", paddingLeft: "20px" }}>{children}</ol>
          ),
          li: ({ children }) => (
            <li style={{ margin: "2px 0" }}>{children}</li>
          ),
          strong: ({ children }) => (
            <strong style={{ fontWeight: 600, color: "var(--text)" }}>
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em style={{ fontStyle: "italic", color: "var(--text-light)" }}>
              {children}
            </em>
          ),
          blockquote: ({ children }) => (
            <blockquote
              style={{
                borderLeft: "3px solid var(--accent)",
                paddingLeft: "12px",
                margin: "8px 0",
                color: "var(--text-light)",
                fontStyle: "italic",
              }}
            >
              {children}
            </blockquote>
          ),
          h1: ({ children }) => (
            <h1
              style={{
                fontSize: "18px",
                fontWeight: 600,
                margin: "12px 0 6px",
                color: "var(--text)",
                borderBottom: "1px solid var(--border)",
                paddingBottom: "4px",
              }}
            >
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2
              style={{
                fontSize: "16px",
                fontWeight: 600,
                margin: "10px 0 5px",
                color: "var(--text)",
              }}
            >
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3
              style={{
                fontSize: "15px",
                fontWeight: 600,
                margin: "8px 0 4px",
                color: "var(--text)",
              }}
            >
              {children}
            </h3>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--accent)", textDecoration: "underline" }}
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div
              style={{
                overflowX: "auto",
                margin: "8px 0",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border)",
              }}
            >
              <table
                style={{
                  borderCollapse: "collapse",
                  width: "100%",
                  fontSize: "13px",
                }}
              >
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th
              style={{
                border: "1px solid var(--border)",
                padding: "6px 10px",
                background: "var(--overlay-medium)",
                fontWeight: 600,
                textAlign: "left",
              }}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              style={{
                border: "1px solid var(--border)",
                padding: "6px 10px",
              }}
            >
              {children}
            </td>
          ),
          hr: () => (
            <hr
              style={{
                border: "none",
                borderTop: "1px solid var(--border)",
                margin: "12px 0",
              }}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>

      {/* Streaming cursor */}
      {isStreaming && (
        <span
          style={{
            display: "inline-block",
            width: "2px",
            height: "16px",
            background: "var(--accent)",
            marginLeft: "2px",
            verticalAlign: "middle",
            borderRadius: "1px",
            animation: "hana-blink 1s step-end infinite",
          }}
        />
      )}
    </div>
  );
}

// ---- Model info footer ----

function ModelInfoFooter({
  model,
  provider,
  usage,
}: {
  model?: string;
  provider?: string;
  usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
}) {
  // Format model name for display
  const modelDisplay = model
    ? model.replace(/^[^/]+\//, "").split("-").slice(0, 3).join("-")
    : null;

  const total = usage?.total_tokens ?? ((usage?.input_tokens ?? 0) + (usage?.output_tokens ?? 0));
  const input = usage?.input_tokens;
  const output = usage?.output_tokens;

  return (
    <div
      style={{
        marginTop: "12px",
        paddingTop: "8px",
        borderTop: "1px solid var(--overlay-light)",
        display: "flex",
        alignItems: "center",
        gap: "12px",
        fontSize: "11px",
        color: "var(--text-muted)",
        fontFamily: "var(--font-ui)",
        flexWrap: "wrap",
      }}
    >
      {/* Model info */}
      {modelDisplay && (
        <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
            <rect x="1" y="4" width="10" height="6" rx="1" stroke="currentColor" strokeWidth="1" />
            <path d="M3 4V2.5A1.5 1.5 0 0 1 4.5 1h3A1.5 1.5 0 0 1 9 2.5V4" stroke="currentColor" strokeWidth="1" />
          </svg>
          {modelDisplay}
        </span>
      )}

      {/* Provider */}
      {provider && (
        <span
          style={{
            textTransform: "uppercase",
            fontSize: "10px",
            padding: "1px 4px",
            background: "var(--overlay-light)",
            borderRadius: "3px",
          }}
        >
          {provider}
        </span>
      )}

      {/* Token usage */}
      {(input !== undefined || output !== undefined || total > 0) && (
        <span style={{ display: "flex", alignItems: "center", gap: "4px", marginLeft: "auto" }}>
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1" />
            <path d="M6 3v3l2 2" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
          </svg>
          {input !== undefined && output !== undefined ? (
            <>
              {input.toLocaleString()} → {output.toLocaleString()}
              <span style={{ opacity: 0.6 }}>({total.toLocaleString()})</span>
            </>
          ) : (
            <>{total.toLocaleString()} tokens</>
          )}
        </span>
      )}
    </div>
  );
}

// ---- Reasoning content (thinking process) ----

function ReasoningContent({ content }: { content: string }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!content.trim()) return null;

  return (
    <div
      style={{
        marginBottom: "12px",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--overlay-medium)",
        background: "var(--overlay-subtle)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          width: "100%",
          padding: "8px 12px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          fontSize: "12px",
          color: "var(--text-muted)",
          fontFamily: "var(--font-ui)",
          textAlign: "left",
          transition: "background var(--duration) var(--ease-out)",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLElement).style.background = "var(--overlay-light)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.background = "transparent";
        }}
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          style={{
            transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
            transition: "transform var(--duration) var(--ease-out)",
          }}
        >
          <path
            d="M4.5 2.5L8 6L4.5 9.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span>思考过程</span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: "11px",
            opacity: 0.7,
          }}
        >
          {isExpanded ? "收起" : "展开"}
        </span>
      </button>

      {/* Content */}
      {isExpanded && (
        <div
          style={{
            padding: "10px 12px",
            fontSize: "13px",
            lineHeight: "1.6",
            color: "var(--text-light)",
            fontFamily: "var(--font-mono)",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            borderTop: "1px solid var(--overlay-medium)",
            maxHeight: "300px",
            overflowY: "auto",
          }}
        >
          {content}
        </div>
      )}
    </div>
  );
}

// ---- Code block with copy button ----

function CodeBlock({ code, language }: { code: string; language: string }) {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      /* ignore */
    }
  };

  return (
    <div
      style={{
        margin: "8px 0",
        borderRadius: "var(--radius-sm)",
        overflow: "hidden",
        border: "1px solid var(--overlay-medium)",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 12px",
          background: "rgba(0,0,0,0.4)",
          borderBottom: "1px solid var(--overlay-medium)",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            color: "var(--text-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {language || "text"}
        </span>
        <button
          onClick={handleCopy}
          style={{
            fontSize: "11px",
            color: "var(--text-muted)",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: "2px 6px",
            borderRadius: "3px",
            transition: "color var(--duration) var(--ease-out)",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.color = "var(--text)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
          }}
        >
          复制
        </button>
      </div>

      <SyntaxHighlighter
        language={language || "text"}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: "14px",
          fontSize: "13px",
          lineHeight: "1.6",
          background: "rgba(0,0,0,0.35)",
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
