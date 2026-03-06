import { cn } from "@/lib/utils";

const LAYER_COLORS = {
  tools: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  planning:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  memory:
    "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  concurrency:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  collaboration: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
} as const;

interface BadgeProps {
  layer: keyof typeof LAYER_COLORS;
  children: React.ReactNode;
  className?: string;
}

interface PlainBadgeProps {
  children: React.ReactNode;
  className?: string;
}

export function Badge({ children, className }: PlainBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-zinc-300 bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function LayerBadge({ layer, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        LAYER_COLORS[layer],
        className,
      )}
    >
      {children}
    </span>
  );
}
