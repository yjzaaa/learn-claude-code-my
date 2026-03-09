import type { ChatMessage } from "./openai";

export type StudioItemKind =
  | "user"
  | "assistant"
  | "tool-bundle"
  | "tool-result"
  | "system";

export interface StudioMetric {
  label: string;
  value: string;
}

export interface ToolInvocationViewModel {
  id: string;
  name: string;
  argsPreview: string;
  resultPreview: string;
  hasResult: boolean;
}

export interface StudioTimelineItem {
  id: string;
  kind: StudioItemKind;
  role: ChatMessage["role"];
  title: string;
  body: string;
  timestampLabel: string;
  tools?: ToolInvocationViewModel[];
  attachedAssistantNote?: string;
}

export interface StudioConversationViewModel {
  title: string;
  subtitle: string;
  items: StudioTimelineItem[];
  metrics: StudioMetric[];
}

export interface StudioMessageRenderItem {
  index: number;
  message: ChatMessage;
  toolResults: ChatMessage[];
  attachedAssistant: ChatMessage | null;
}
