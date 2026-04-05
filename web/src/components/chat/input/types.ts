/** Input Component Types - 输入组件共享类型 */

import type { ChangeEvent, KeyboardEvent } from "react";

export interface ModelOption {
  id: string;
  label: string;
  provider: string;
}

export interface SlashCommand {
  id: string;
  label: string;
  description: string;
  icon?: string;
}

export interface FileAttachment {
  id: string;
  name: string;
  size: number;
  type: string;
  mimeType?: string;
  dataUrl?: string;
}

export type ThinkingLevel = "none" | "brief" | "full";

export interface SendOptions {
  thinkingLevel: ThinkingLevel;
  model: string;
  planMode: boolean;
}

export interface InputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  selectedModel?: string;
  onModelChange?: (modelId: string) => void;
  availableModels?: ModelOption[];
  attachedFiles?: FileAttachment[];
  onFileAttach?: (files: File[]) => void;
  onFileRemove?: (fileId: string) => void;
}

export interface ModelSelectorProps {
  selected: string;
  options: ModelOption[];
  onChange: (modelId: string) => void;
  disabled?: boolean;
}

export interface SlashCommandMenuProps {
  isOpen: boolean;
  query: string;
  commands: SlashCommand[];
  onSelect: (command: SlashCommand) => void;
  onClose: () => void;
}

export interface FileAttachmentProps {
  files: FileAttachment[];
  onRemove: (fileId: string) => void;
}
