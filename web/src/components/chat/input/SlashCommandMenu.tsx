"use client";

/** Slash Command Menu - 斜杠命令菜单组件 */

import { useEffect, useRef } from "react";
import type { SlashCommandMenuProps } from "./types";

export function SlashCommandMenu({
  isOpen,
  query,
  commands,
  onSelect,
  onClose,
}: SlashCommandMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  const filteredCommands = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(query.toLowerCase()) ||
    cmd.description.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || filteredCommands.length === 0) {
    return null;
  }

  return (
    <div
      ref={menuRef}
      className="absolute bottom-full left-0 mb-2 w-64 py-2 bg-popover border rounded-lg shadow-lg z-50"
    >
      <div className="px-3 py-1 text-xs text-muted-foreground border-b mb-1">
        可用命令
      </div>
      {filteredCommands.map((command) => (
        <button
          key={command.id}
          type="button"
          onClick={() => onSelect(command)}
          className="w-full px-3 py-2 text-left hover:bg-accent transition-colors"
        >
          <div className="flex items-center gap-2">
            {command.icon && <span>{command.icon}</span>}
            <span className="font-medium">/{command.label}</span>
          </div>
          <div className="text-xs text-muted-foreground pl-6">
            {command.description}
          </div>
        </button>
      ))}
    </div>
  );
}

export default SlashCommandMenu;
