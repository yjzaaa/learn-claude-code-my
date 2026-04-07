"use client";

import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const WS_BASE_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws/client-1"
    : "ws://localhost:8001/ws/client-1";

// ==================== 类型定义 ====================

export type MemoryType = "user" | "feedback" | "project" | "reference";

export interface Memory {
  id: string;
  user_id: string;
  name: string;
  description: string;
  type: MemoryType;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  items: Memory[];
  total: number;
  page: number;
  page_size: number;
}

export interface MemorySearchResult {
  memory: Memory;
  score: number;
}

export interface MemorySearchResponse {
  results: MemorySearchResult[];
  query: string;
}

export interface CreateMemoryRequest {
  user_id: string;
  name: string;
  description: string;
  type: MemoryType;
  content: string;
}

export interface UpdateMemoryRequest {
  name?: string;
  description?: string;
  type?: MemoryType;
  content?: string;
}

export interface MemoryListParams {
  userId: string;
  type?: MemoryType;
  page?: number;
  pageSize?: number;
}

export interface MemorySearchParams {
  userId: string;
  query: string;
  limit?: number;
}

// ==================== API 函数 ====================

async function fetchMemoryList(
  params: MemoryListParams,
): Promise<MemoryListResponse> {
  const { userId, type, page = 1, pageSize = 20 } = params;
  const searchParams = new URLSearchParams();
  if (type) searchParams.append("type", type);
  searchParams.append("page", String(page));
  searchParams.append("page_size", String(pageSize));

  const response = await fetch(
    `${API_BASE_URL}/api/memory/list/${userId}?${searchParams.toString()}`,
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch memory list: ${response.statusText}`);
  }
  const json = await response.json();

  // 处理后端直接返回数组的情况
  if (Array.isArray(json)) {
    return {
      items: json,
      total: json.length,
      page: page,
      page_size: pageSize,
    };
  }

  // 处理包装对象格式
  const data = json?.data ?? json;
  if (Array.isArray(data)) {
    return {
      items: data,
      total: data.length,
      page: page,
      page_size: pageSize,
    };
  }

  return data as MemoryListResponse;
}

async function searchMemories(
  params: MemorySearchParams,
): Promise<MemorySearchResponse> {
  const { userId, query, limit = 10 } = params;
  const response = await fetch(`${API_BASE_URL}/api/memory/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, query, limit }),
  });
  if (!response.ok) {
    throw new Error(`Failed to search memories: ${response.statusText}`);
  }
  const json = await response.json();
  return json?.data ?? json;
}

async function createMemoryApi(request: CreateMemoryRequest): Promise<Memory> {
  const response = await fetch(`${API_BASE_URL}/api/memory/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to create memory: ${response.statusText}`);
  }
  const json = await response.json();
  return json?.data ?? json;
}

async function updateMemoryApi(
  memoryId: string,
  request: UpdateMemoryRequest,
): Promise<Memory> {
  const response = await fetch(`${API_BASE_URL}/api/memory/update/${memoryId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to update memory: ${response.statusText}`);
  }
  const json = await response.json();
  return json?.data ?? json;
}

async function deleteMemoryApi(memoryId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/memory/delete/${memoryId}`,
    {
      method: "DELETE",
    },
  );
  if (!response.ok) {
    throw new Error(`Failed to delete memory: ${response.statusText}`);
  }
}

// ==================== Hook: useMemoryList ====================

export interface UseMemoryListReturn {
  memories: Memory[];
  total: number;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
  page: number;
  setPage: (page: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
}

export function useMemoryList(
  params: MemoryListParams,
): UseMemoryListReturn {
  const [page, setPage] = useState(params.page ?? 1);
  const [pageSize, setPageSize] = useState(params.pageSize ?? 20);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!params.userId) return;

    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const response = await fetchMemoryList({
        userId: params.userId,
        type: params.type,
        page,
        pageSize,
      });
      setMemories(response.items);
      setTotal(response.total);
    } catch (e) {
      setIsError(true);
      setError(e instanceof Error ? e : new Error("Unknown error"));
    } finally {
      setIsLoading(false);
    }
  }, [params.userId, params.type, page, pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 自动刷新机制 - 每30秒刷新一次
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return {
    memories,
    total,
    isLoading,
    isError,
    error,
    refetch: fetchData,
    page,
    setPage,
    pageSize,
    setPageSize,
  };
}

// ==================== Hook: useMemorySearch ====================

export interface UseMemorySearchReturn {
  results: MemorySearchResult[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  search: (query: string) => void;
  debouncedSearch: (query: string) => void;
}

export function useMemorySearch(
  params: Omit<MemorySearchParams, "query">,
): UseMemorySearchReturn {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState<MemorySearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const performSearch = useCallback(async (query: string) => {
    if (!params.userId || query.length === 0) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const response = await searchMemories({
        userId: params.userId,
        query,
        limit: params.limit,
      });
      setResults(response.results);
    } catch (e) {
      setIsError(true);
      setError(e instanceof Error ? e : new Error("Unknown error"));
    } finally {
      setIsLoading(false);
    }
  }, [params.userId, params.limit]);

  useEffect(() => {
    performSearch(searchQuery);
  }, [searchQuery, performSearch]);

  const search = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  const debouncedSearch = useCallback(
    (query: string) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        setSearchQuery(query);
      }, 300);
    },
    [],
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return {
    results,
    isLoading,
    isError,
    error,
    search,
    debouncedSearch,
  };
}

// ==================== Hook: useMemoryRealtime ====================

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface UseMemoryRealtimeReturn {
  memories: Memory[];
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  error: Error | null;
}

export function useMemoryRealtime(userId: string): UseMemoryRealtimeReturn {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("disconnected");
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!userId) return;

    const connect = () => {
      setConnectionStatus("connecting");
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setConnectionStatus("connected");
          setError(null);
          ws.send(
            JSON.stringify({
              type: "subscribe",
              channel: "memory",
              user_id: userId,
            }),
          );
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "memory:snapshot") {
              setMemories(msg.data?.memories ?? []);
            } else if (msg.type === "memory:created") {
              setMemories((prev) => [msg.data, ...prev]);
            } else if (msg.type === "memory:updated") {
              setMemories((prev) =>
                prev.map((m) => (m.id === msg.data.id ? msg.data : m)),
              );
            } else if (msg.type === "memory:deleted") {
              setMemories((prev) => prev.filter((m) => m.id !== msg.data.id));
            }
          } catch (e) {
            console.error("[useMemoryRealtime] Failed to parse message:", e);
          }
        };

        ws.onclose = () => {
          setConnectionStatus("disconnected");
          wsRef.current = null;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        };

        ws.onerror = (e) => {
          setConnectionStatus("error");
          setError(new Error("WebSocket connection error"));
        };
      } catch (e) {
        setConnectionStatus("error");
        setError(e instanceof Error ? e : new Error("Unknown error"));
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [userId]);

  return {
    memories,
    isConnected: connectionStatus === "connected",
    connectionStatus,
    error,
  };
}

// ==================== Hook: useMemoryOperations ====================

export interface UseMemoryOperationsReturn {
  createMemory: (data: CreateMemoryRequest) => Promise<Memory>;
  updateMemory: (id: string, data: UpdateMemoryRequest) => Promise<Memory>;
  deleteMemory: (id: string) => Promise<void>;
  isCreating: boolean;
  isUpdating: boolean;
  isDeleting: boolean;
  createError: Error | null;
  updateError: Error | null;
  deleteError: Error | null;
}

export function useMemoryOperations(): UseMemoryOperationsReturn {
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [createError, setCreateError] = useState<Error | null>(null);
  const [updateError, setUpdateError] = useState<Error | null>(null);
  const [deleteError, setDeleteError] = useState<Error | null>(null);

  const createMemory = useCallback(async (data: CreateMemoryRequest): Promise<Memory> => {
    setIsCreating(true);
    setCreateError(null);
    try {
      const result = await createMemoryApi(data);
      return result;
    } catch (e) {
      const error = e instanceof Error ? e : new Error("Failed to create memory");
      setCreateError(error);
      throw error;
    } finally {
      setIsCreating(false);
    }
  }, []);

  const updateMemory = useCallback(async (id: string, data: UpdateMemoryRequest): Promise<Memory> => {
    setIsUpdating(true);
    setUpdateError(null);
    try {
      const result = await updateMemoryApi(id, data);
      return result;
    } catch (e) {
      const error = e instanceof Error ? e : new Error("Failed to update memory");
      setUpdateError(error);
      throw error;
    } finally {
      setIsUpdating(false);
    }
  }, []);

  const deleteMemory = useCallback(async (id: string): Promise<void> => {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteMemoryApi(id);
    } catch (e) {
      const error = e instanceof Error ? e : new Error("Failed to delete memory");
      setDeleteError(error);
      throw error;
    } finally {
      setIsDeleting(false);
    }
  }, []);

  return {
    createMemory,
    updateMemory,
    deleteMemory,
    isCreating,
    isUpdating,
    isDeleting,
    createError,
    updateError,
    deleteError,
  };
}
