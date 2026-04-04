"use client";

import {
  createElement,
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import type { ChatMessage } from "@/types/openai";
import type { AgentStreamState } from "@/types/agent-event";

export interface ChatSession {
  id: string;
  title?: string;
  messages: ChatMessage[];
  model?: string;
  created_at: number;
  updated_at: number;
}

interface MessageStoreState {
  dialogs: ChatSession[];
  currentDialog: ChatSession | null;
  isLoading: boolean;
  error: string | null;
  streamState: AgentStreamState;
}

function useMessageStoreInstance() {
  const [state, setState] = useState<MessageStoreState>({
    dialogs: [],
    currentDialog: null,
    isLoading: false,
    error: null,
    streamState: {
      isStreaming: false,
      currentMessageId: null,
      accumulatedContent: "",
      accumulatedReasoning: "",
      toolCalls: [],
      showReasoning: false,
      hookStats: null,
      runReport: null,
      todos: null,
      roundsSinceTodo: 0,
      showTodoReminder: false,
    },
  });

  const currentDialogRef = useRef<ChatSession | null>(null);

  // 设置当前对话框
  const setCurrentDialog = useCallback((dialog: ChatSession | null) => {
    setState((prev) => {
      if (!dialog) {
        return {
          ...prev,
          currentDialog: null,
        };
      }

      const existingDialog = prev.dialogs.find((d) => d.id === dialog.id);
      const existingMessages = existingDialog?.messages || [];
      const dialogMessages = (dialog as ChatSession).messages || [];
      const dialogToSet = existingDialog
        ? { ...dialog, messages: existingMessages }
        : { ...dialog, messages: dialogMessages };

      const updatedDialogs = prev.dialogs.some((d) => d.id === dialog.id)
        ? prev.dialogs.map((d) => (d.id === dialog.id ? dialogToSet : d))
        : [...prev.dialogs, dialogToSet];

      return {
        ...prev,
        currentDialog: dialogToSet,
        dialogs: updatedDialogs,
      };
    });
  }, []);

  // 重置并设置新对话框
  const resetAndSetDialog = useCallback((dialog: ChatSession | null) => {
    setState((prev) => {
      if (!dialog) {
        return {
          ...prev,
          currentDialog: null,
          streamState: {
            isStreaming: false,
            currentMessageId: null,
            accumulatedContent: "",
            accumulatedReasoning: "",
            toolCalls: [],
            showReasoning: false,
            hookStats: null,
            runReport: null,
            todos: null,
            roundsSinceTodo: 0,
            showTodoReminder: false,
          },
        };
      }

      let updatedDialogs = [...prev.dialogs];
      if (
        prev.currentDialog &&
        !updatedDialogs.some((d) => d.id === prev.currentDialog!.id)
      ) {
        updatedDialogs.push(prev.currentDialog);
      }

      if (!updatedDialogs.some((d) => d.id === dialog.id)) {
        updatedDialogs.push(dialog);
      } else {
        updatedDialogs = updatedDialogs.map((d) =>
          d.id === dialog.id ? dialog : d,
        );
      }

      return {
        ...prev,
        currentDialog: dialog,
        dialogs: updatedDialogs,
        streamState: {
          isStreaming: false,
          currentMessageId: null,
          accumulatedContent: "",
          accumulatedReasoning: "",
          toolCalls: [],
          showReasoning: false,
          hookStats: null,
          runReport: null,
          todos: null,
          roundsSinceTodo: 0,
          showTodoReminder: false,
        },
      };
    });
  }, []);

  // 添加本地消息
  const addLocalMessage = useCallback((message: ChatMessage) => {
    setState((prev) => {
      if (!prev.currentDialog) return prev;

      const updatedDialog = {
        ...prev.currentDialog,
        messages: [...prev.currentDialog.messages, message],
        updated_at: Date.now(),
      };

      return {
        ...prev,
        currentDialog: updatedDialog,
        dialogs: prev.dialogs.map((d) =>
          d.id === updatedDialog.id ? updatedDialog : d,
        ),
      };
    });
  }, []);

  // 获取工具调用
  const getToolCalls = useCallback(
    (parentContent: string) => {
      return (
        state.currentDialog?.messages.filter(
          (m) =>
            m.role === "assistant" &&
            m.tool_calls &&
            m.tool_calls.length > 0 &&
            m.content === parentContent,
        ) || []
      );
    },
    [state.currentDialog],
  );

  // 获取工具结果
  const getToolResults = useCallback(
    (toolCallId: string) => {
      return (
        state.currentDialog?.messages.filter(
          (m) => m.role === "tool" && m.tool_call_id === toolCallId,
        ) || []
      );
    },
    [state.currentDialog],
  );

  return {
    ...state,
    setCurrentDialog,
    resetAndSetDialog,
    addLocalMessage,
    getToolCalls,
    getToolResults,
    messages: state.currentDialog?.messages || [],
    streamingContent: state.streamState.accumulatedContent,
    streamingReasoning: state.streamState.accumulatedReasoning,
    currentStreamingMessageId: state.streamState.currentMessageId,
    isStreaming: state.streamState.isStreaming,
  };
}

type MessageStoreApi = ReturnType<typeof useMessageStoreInstance>;

const MessageStoreContext = createContext<MessageStoreApi | null>(null);

export function MessageStoreProvider({ children }: { children: ReactNode }) {
  const store = useMessageStoreInstance();
  return createElement(
    MessageStoreContext.Provider,
    { value: store },
    children,
  );
}

export function useMessageStore(): MessageStoreApi {
  const store = useContext(MessageStoreContext);
  if (!store) {
    throw new Error("useMessageStore must be used within MessageStoreProvider");
  }
  return store;
}
