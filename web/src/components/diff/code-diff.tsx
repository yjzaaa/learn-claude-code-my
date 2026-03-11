"use client";

import {
  useMemo,
  useState,
  useCallback,
  useRef,
  useEffect,
  type WheelEvent,
  type MouseEvent,
} from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import { diffLines } from "diff";
import { cn } from "@/lib/utils";

interface CodeDiffProps {
  oldSource: string;
  newSource: string;
  oldLabel: string;
  newLabel: string;
}

function detectFileKind(label: string): string {
  const lower = label.toLowerCase();
  if (lower.endsWith(".md")) return "Markdown";
  if (lower.endsWith(".py")) return "Python";
  if (lower.endsWith(".ts")) return "TypeScript";
  if (lower.endsWith(".tsx")) return "TSX";
  if (lower.endsWith(".js")) return "JavaScript";
  if (lower.endsWith(".json")) return "JSON";
  if (lower.endsWith(".yaml") || lower.endsWith(".yml")) return "YAML";
  if (lower.endsWith(".css")) return "CSS";
  if (lower.endsWith(".html")) return "HTML";
  return "Text";
}

export function CodeDiff({
  oldSource,
  newSource,
  oldLabel,
  newLabel,
}: CodeDiffProps) {
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");
  const [showDiffOnly, setShowDiffOnly] = useState(true);
  const [enableWordDiff, setEnableWordDiff] = useState(true);
  const [contextLines, setContextLines] = useState(3);
  const [isDragging, setIsDragging] = useState(false);
  const styles = useMemo(
    () => ({
      variables: {
        light: {
          diffViewerBackground: "#ffffff",
          diffViewerColor: "#18181b",
          addedBackground: "#dcfce7",
          removedBackground: "#fee2e2",
          addedColor: "#14532d",
          removedColor: "#7f1d1d",
          wordAddedBackground: "#86efac",
          wordRemovedBackground: "#fca5a5",
          gutterBackground: "#f4f4f5",
          gutterBackgroundDark: "#f4f4f5",
          highlightBackground: "#fef9c3",
          highlightGutterBackground: "#fef08a",
          codeFoldGutterBackground: "#f4f4f5",
          codeFoldBackground: "#fafafa",
          emptyLineBackground: "#fafafa",
        },
        dark: {
          diffViewerBackground: "#09090b",
          diffViewerColor: "#f4f4f5",
          addedBackground: "#052e16",
          removedBackground: "#450a0a",
          addedColor: "#86efac",
          removedColor: "#fca5a5",
          wordAddedBackground: "#166534",
          wordRemovedBackground: "#991b1b",
          gutterBackground: "#18181b",
          gutterBackgroundDark: "#18181b",
          highlightBackground: "#713f12",
          highlightGutterBackground: "#854d0e",
          codeFoldGutterBackground: "#18181b",
          codeFoldBackground: "#0a0a0a",
          emptyLineBackground: "#0a0a0a",
        },
      },
      diffContainer: {
        borderRadius: "0.75rem",
        border: "1px solid rgb(228 228 231)",
        overflow: "hidden",
      },
      marker: {
        minWidth: "2rem",
      },
      lineNumber: {
        minWidth: "2.5rem",
      },
      contentText: {
        fontFamily:
          "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace",
        fontSize: "12px",
        lineHeight: "1.45",
        whiteSpace: "pre",
      },
      titleBlock: {
        whiteSpace: "pre",
      },
    }),
    [],
  );

  const oldTitle = useMemo(() => `OLD  ${oldLabel}`, [oldLabel]);
  const newTitle = useMemo(() => `NEW  ${newLabel}`, [newLabel]);
  const fileKind = useMemo(
    () => detectFileKind(newLabel || oldLabel),
    [newLabel, oldLabel],
  );
  const diffStats = useMemo(() => {
    const changes = diffLines(oldSource, newSource);
    let added = 0;
    let removed = 0;

    for (const change of changes) {
      // Ignore trailing empty line produced by split in some cases.
      const lines = change.value.split("\n");
      const lineCount =
        lines[lines.length - 1] === "" ? lines.length - 1 : lines.length;
      if (change.added) {
        added += lineCount;
      } else if (change.removed) {
        removed += lineCount;
      }
    }

    return { added, removed };
  }, [oldSource, newSource]);
  const longestLineLength = useMemo(() => {
    const allLines = `${oldSource}\n${newSource}`.split("\n");
    let maxLen = 0;
    for (const line of allLines) {
      if (line.length > maxLen) maxLen = line.length;
    }
    return maxLen;
  }, [oldSource, newSource]);

  const diffMinWidthPx = useMemo(() => {
    const charWidth = 7;
    const basePadding = viewMode === "split" ? 520 : 300;
    const estimated = longestLineLength * charWidth + basePadding;
    return Math.max(900, Math.min(6000, estimated));
  }, [longestLineLength, viewMode]);

  const hasChanges = diffStats.added > 0 || diffStats.removed > 0;
  const scrollRef = useRef<HTMLDivElement>(null);
  const dragStateRef = useRef<{
    startX: number;
    startY: number;
    scrollLeft: number;
    scrollTop: number;
    isDragging: boolean;
  } | null>(null);

  const handleDiffWheel = useCallback((e: WheelEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth) {
      e.stopPropagation();
    }
  }, []);

  const handleMouseDown = useCallback((e: MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    const el = scrollRef.current;
    if (!el) return;
    e.preventDefault();

    if (
      el.scrollWidth <= el.clientWidth &&
      el.scrollHeight <= el.clientHeight
    ) {
      return;
    }

    dragStateRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      scrollLeft: el.scrollLeft,
      scrollTop: el.scrollTop,
      isDragging: false,
    };
  }, []);

  useEffect(() => {
    const handleWindowMouseMove = (e: globalThis.MouseEvent) => {
      const el = scrollRef.current;
      const drag = dragStateRef.current;
      if (!el || !drag) return;

      const dx = e.clientX - drag.startX;
      const dy = e.clientY - drag.startY;
      if (!drag.isDragging && Math.abs(dx) + Math.abs(dy) < 4) {
        return;
      }

      drag.isDragging = true;
      setIsDragging(true);
      e.preventDefault();
      el.scrollLeft = drag.scrollLeft - dx;
      // Keep slight vertical panning support but prioritize horizontal movement.
      el.scrollTop = drag.scrollTop - dy * 0.35;
    };

    const handleWindowMouseUp = () => {
      if (!dragStateRef.current) return;
      dragStateRef.current = null;
      setIsDragging(false);
    };

    window.addEventListener("mousemove", handleWindowMouseMove);
    window.addEventListener("mouseup", handleWindowMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleWindowMouseMove);
      window.removeEventListener("mouseup", handleWindowMouseUp);
    };
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (!dragStateRef.current) return;
    if (!dragStateRef.current.isDragging) return;
    setIsDragging(false);
  }, []);

  return (
    <div>
      <div className="mb-3 space-y-3 rounded-lg bg-white dark:bg-zinc-950/70">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-full border border-zinc-300 bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                {fileKind}
              </span>
              <span className="inline-flex items-center rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
                +{diffStats.added}
              </span>
              <span className="inline-flex items-center rounded-full border border-red-300 bg-red-50 px-2 py-0.5 text-[11px] font-medium text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
                -{diffStats.removed}
              </span>
            </div>
            <div className="min-w-0 truncate text-sm text-zinc-500 dark:text-zinc-400">
              <span className="font-medium text-zinc-700 dark:text-zinc-300">
                {oldLabel}
              </span>
              {" -> "}
              <span className="font-medium text-zinc-700 dark:text-zinc-300">
                {newLabel}
              </span>
            </div>
          </div>
          <div className="flex shrink-0 rounded-lg border border-zinc-200 dark:border-zinc-700">
            <button
              onClick={() => setViewMode("unified")}
              className={cn(
                "min-h-[36px] px-3 text-xs font-medium transition-colors",
                viewMode === "unified"
                  ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                  : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400",
              )}
            >
              Unified
            </button>
            <button
              onClick={() => setViewMode("split")}
              className={cn(
                "min-h-[36px] px-3 text-xs font-medium transition-colors sm:inline-flex hidden",
                viewMode === "split"
                  ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                  : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400",
              )}
            >
              Split
            </button>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs dark:border-zinc-700 dark:bg-zinc-900/40">
          <span className="inline-flex items-center rounded-md border border-zinc-300 bg-white px-2 py-0.5 font-medium text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
            status: {hasChanges ? "modified" : "unchanged"}
          </span>

          <label className="inline-flex cursor-pointer items-center gap-1.5 text-zinc-600 dark:text-zinc-300">
            <input
              type="checkbox"
              className="h-3.5 w-3.5 rounded border-zinc-300"
              checked={showDiffOnly}
              onChange={(e) => setShowDiffOnly(e.target.checked)}
            />
            Show changes only
          </label>

          <label className="inline-flex cursor-pointer items-center gap-1.5 text-zinc-600 dark:text-zinc-300">
            <input
              type="checkbox"
              className="h-3.5 w-3.5 rounded border-zinc-300"
              checked={enableWordDiff}
              onChange={(e) => setEnableWordDiff(e.target.checked)}
            />
            Word diff
          </label>
          <label className="inline-flex items-center gap-1.5 text-zinc-600 dark:text-zinc-300">
            Context
            <select
              className="rounded border border-zinc-300 bg-white px-1.5 py-0.5 text-xs text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
              value={contextLines}
              onChange={(e) => setContextLines(Number(e.target.value))}
              disabled={!showDiffOnly}
            >
              <option value={1}>1 line</option>
              <option value={3}>3 lines</option>
              <option value={5}>5 lines</option>
              <option value={10}>10 lines</option>
            </select>
          </label>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 dark:border-zinc-700">
        <div
          ref={scrollRef}
          onWheel={handleDiffWheel}
          onMouseDown={handleMouseDown}
          onMouseLeave={handleMouseLeave}
          className="max-h-[460px] overflow-x-auto overflow-y-auto overscroll-contain touch-pan-x"
          style={{ cursor: isDragging ? "grabbing" : "grab" }}
        >
          <div
            className="min-w-max diff-drag-surface"
            style={{ minWidth: `${diffMinWidthPx}px` }}
          >
            <ReactDiffViewer
              oldValue={oldSource}
              newValue={newSource}
              splitView={viewMode === "split"}
              compareMethod={DiffMethod.WORDS}
              showDiffOnly={showDiffOnly}
              hideLineNumbers={false}
              disableWordDiff={!enableWordDiff}
              leftTitle={oldTitle}
              rightTitle={newTitle}
              useDarkTheme={false}
              styles={styles}
              extraLinesSurroundingDiff={contextLines}
            />
          </div>
          <style jsx global>{`
            .diff-drag-surface table {
              width: max-content !important;
              min-width: 100% !important;
            }

            .diff-drag-surface th,
            .diff-drag-surface td {
              white-space: pre !important;
            }
          `}</style>
        </div>
      </div>
    </div>
  );
}
