import type { Metadata } from "next";
import { cn } from "@/lib/utils";
import "../../globals.css";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  return {
    title: "Agent Workspace",
    description: "AI Agent Workspace",
  };
}

export default async function AgentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className={cn(
      "h-[calc(100vh-56px)]",
      "bg-[var(--color-bg)] text-[var(--color-text)]"
    )}>
      {children}
    </div>
  );
}
