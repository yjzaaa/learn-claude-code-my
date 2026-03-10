"use client";

import { useState, useEffect } from "react";
import { RealtimeDialog } from "@/components/realtime";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAgentApi } from "@/hooks/useAgentApi";
import type { Dialog } from "@/hooks/useAgentApi";
import { MessageStoreProvider, useMessageStore } from "@/hooks/useMessageStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Wifi,
  WifiOff,
  MessageSquare,
  Loader2,
  Plus,
  Trash2,
  RefreshCw,
} from "lucide-react";

export function RealtimeDemoClient() {
  return (
    <MessageStoreProvider>
      <RealtimeDemoClientContent />
    </MessageStoreProvider>
  );
}

function RealtimeDemoClientContent() {
  const [dialogs, setDialogs] = useState<Dialog[]>([]);
  const [selectedDialogId, setSelectedDialogId] = useState<string | null>(null);
  const [newDialogTitle, setNewDialogTitle] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);

  const {
    isLoading,
    getDialogs,
    createDialog,
    deleteDialog,
    getDialog,
    sendMessage,
  } = useAgentApi();
  const { isConnected: wsConnected, subscribeToDialog } = useWebSocket();
  const { currentDialog, setCurrentDialog } = useMessageStore();

  const loadDialogs = async () => {
    const result = await getDialogs();
    if (result.success && result.data) {
      setDialogs(result.data);
    }
  };

  useEffect(() => {
    loadDialogs();
  }, []);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 p-8">
      <div className="max-w-6xl mx-auto">
        <h1>FastAPI 实时消息系统</h1>
      </div>
    </div>
  );
}
