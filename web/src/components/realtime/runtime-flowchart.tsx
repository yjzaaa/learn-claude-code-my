"use client";

import { useMemo, useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Activity, Loader2, Bot, Play, Square, Hand } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage, ChatRole } from "@/types/openai";

interface RuntimeFlowchartProps {
  isOpen: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  className?: string;
}

// 流程节点类型
type NodeType = "start" | "agent" | "end";

interface FlowNode {
  id: string;
  type: NodeType;
  // 归一化位置 (0-1)
  nx: number;
  ny: number;
  data: {
    label: string;
    displayName: string;
    role?: ChatRole;
    status: "idle" | "running" | "completed" | "error";
    activeMsgType?: string;
  };
}

interface FlowEdge {
  from: string;
  to: string;
  animated?: boolean;
}

// 画布尺寸配置
const CANVAS_WIDTH = 520;
const CANVAS_HEIGHT = 280;
const NODE_WIDTH = 100;
const NODE_HEIGHT = 56;

// 从 role 提取显示名称
function getRoleDisplayName(role?: ChatRole): { className: string; displayName: string } {
  const roleMap: Record<ChatRole, { className: string; displayName: string }> = {
    system: { className: "System", displayName: "系统" },
    user: { className: "User", displayName: "用户" },
    assistant: { className: "Assistant", displayName: "助手" },
    tool: { className: "Tool", displayName: "工具" },
  };

  return role ? roleMap[role] : { className: "Unknown", displayName: "未知" };
}

// 获取节点颜色
function getNodeColor(role?: ChatRole): { bg: string; border: string; text: string } {
  const colors: Record<ChatRole, { bg: string; border: string; text: string }> = {
    system: { bg: "#F3F4F6", border: "#9CA3AF", text: "#4B5563" },
    user: { bg: "#DBEAFE", border: "#60A5FA", text: "#2563EB" },
    assistant: { bg: "#E0E7FF", border: "#818CF8", text: "#4F46E5" },
    tool: { bg: "#CFFAFE", border: "#22D3EE", text: "#0891B2" },
  };

  return role ? colors[role] : { bg: "#F3F4F6", border: "#9CA3AF", text: "#4B5563" };
}

export function RuntimeFlowchart({ isOpen, onClose, messages, className }: RuntimeFlowchartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  // 计算流程图 - 使用归一化坐标确保在单屏内
  const { nodes, edges, activeNodeId } = useMemo(() => {
    const flowNodes: FlowNode[] = [];
    const flowEdges: FlowEdge[] = [];

    if (messages.length === 0) {
      return { nodes: [], edges: [], activeNodeId: null };
    }

    // 收集所有唯一的角色类型
    const uniqueRoles = new Set<ChatRole>();
    messages.forEach((msg) => {
      if (msg.role) {
        uniqueRoles.add(msg.role);
      }
    });

    const roleList = Array.from(uniqueRoles);
    const totalNodes = roleList.length + 2; // +2 for start and end

    // 添加开始节点（左侧）
    flowNodes.push({
      id: "start",
      type: "start",
      nx: 0.05,
      ny: 0.5,
      data: { label: "Start", displayName: "开始", status: "completed" },
    });

    // 添加角色节点（均匀分布）
    roleList.forEach((role, index) => {
      const nodeId = `role-${role}`;
      const { className, displayName } = getRoleDisplayName(role);
      // 在 0.15 到 0.85 之间均匀分布
      const nx = 0.15 + (index + 1) * (0.7 / (totalNodes - 1));

      flowNodes.push({
        id: nodeId,
        type: "agent",
        nx,
        ny: 0.5,
        data: {
          label: className,
          displayName: displayName,
          role,
          status: "idle",
        },
      });
    });

    // 添加结束节点（右侧）
    flowNodes.push({
      id: "end",
      type: "end",
      nx: 0.95,
      ny: 0.5,
      data: { label: "End", displayName: "结束", status: "completed" },
    });

    // 创建连线
    for (let i = 0; i < flowNodes.length - 1; i++) {
      flowEdges.push({
        from: flowNodes[i].id,
        to: flowNodes[i + 1].id,
      });
    }

    // 确定活跃节点（最后一条消息的角色）
    let activeId: string | null = null;
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.role) {
      activeId = `role-${lastMessage.role}`;
      const node = flowNodes.find(n => n.id === activeId);
      if (node) {
        node.data.status = "running";
      }
      const edge = flowEdges.find(e => e.to === activeId);
      if (edge) edge.animated = true;
    }

    return { nodes: flowNodes, edges: flowEdges, activeNodeId: activeId };
  }, [messages]);

  const hasRunning = useMemo(() => {
    const lastMessage = messages[messages.length - 1];
    return lastMessage?.role === "assistant";
  }, [messages]);

  // 将归一化坐标转为实际像素
  const toPixelX = (nx: number) => nx * CANVAS_WIDTH;
  const toPixelY = (ny: number) => ny * CANVAS_HEIGHT;

  // 生成连线路径
  const getPath = (edge: FlowEdge) => {
    const from = nodes.find((n) => n.id === edge.from);
    const to = nodes.find((n) => n.id === edge.to);
    if (!from || !to) return "";

    const startX = toPixelX(from.nx) + NODE_WIDTH / 2;
    const startY = toPixelY(from.ny);
    const endX = toPixelX(to.nx) - NODE_WIDTH / 2;
    const endY = toPixelY(to.ny);

    // 水平直线
    return `M ${startX} ${startY} L ${endX} ${endY}`;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, x: 50, width: 0 }}
          animate={{ opacity: 1, x: 0, width: "100%", maxWidth: "560px" }}
          exit={{ opacity: 0, x: 50, width: 0 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          className={cn(
            "relative h-full shrink-0 overflow-hidden flex flex-col",
            "bg-zinc-50 dark:bg-zinc-950",
            "border-l border-zinc-200 dark:border-zinc-700",
            className
          )}
        >
          {/* 头部 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shrink-0">
            <div className="flex items-center gap-2">
              <Activity className={cn("w-5 h-5", hasRunning ? "text-blue-500 animate-pulse" : "text-zinc-500")} />
              <div>
                <h3 className="font-semibold text-sm">对话流程</h3>
                <p className="text-[10px] text-zinc-500">
                  {nodes.filter(n => n.type === "agent").length} 个角色
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            >
              <X className="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          {/* 流程图区域 - 固定尺寸 */}
          <div className="flex-1 overflow-hidden p-4 flex items-center justify-center bg-zinc-100 dark:bg-zinc-900">
            {nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center text-zinc-400">
                <Activity className="w-12 h-12 mb-3 opacity-30" />
                <p className="text-sm">等待消息...</p>
              </div>
            ) : (
              <div
                className="relative bg-white dark:bg-zinc-900 rounded-lg shadow-sm border border-zinc-200 dark:border-zinc-700"
                style={{ width: CANVAS_WIDTH, height: CANVAS_HEIGHT }}
              >
                <svg
                  width={CANVAS_WIDTH}
                  height={CANVAS_HEIGHT}
                  className="absolute inset-0"
                >
                  <defs>
                    <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                      <polygon points="0 0, 8 3, 0 6" fill="#9CA3AF" />
                    </marker>
                    <marker id="arrow-active" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                      <polygon points="0 0, 8 3, 0 6" fill="#3B82F6" />
                    </marker>
                  </defs>

                  {/* 连线 */}
                  {edges.map((edge) => {
                    const path = getPath(edge);
                    const isActive = edge.animated;

                    return (
                      <g key={`${edge.from}-${edge.to}`}>
                        <motion.path
                          d={path}
                          fill="none"
                          stroke={isActive ? "#3B82F6" : "#D1D5DB"}
                          strokeWidth={isActive ? 3 : 2}
                          markerEnd={isActive ? "url(#arrow-active)" : "url(#arrow)"}
                          initial={{ pathLength: 0 }}
                          animate={{ pathLength: 1 }}
                          transition={{ duration: 0.5 }}
                        />
                      </g>
                    );
                  })}

                  {/* 节点 */}
                  {nodes.map((node, idx) => (
                    <foreignObject
                      key={node.id}
                      x={toPixelX(node.nx) - NODE_WIDTH / 2}
                      y={toPixelY(node.ny) - NODE_HEIGHT / 2}
                      width={NODE_WIDTH}
                      height={NODE_HEIGHT}
                      style={{ pointerEvents: "none" }}
                    >
                      <NodeCard node={node} index={idx} />
                    </foreignObject>
                  ))}
                </svg>

                {/* 活跃指示器 */}
                {activeNodeId && (
                  <div className="absolute bottom-2 left-2 right-2 text-center">
                    <span className="text-[10px] px-2 py-1 rounded-full bg-blue-500 text-white animate-pulse">
                      运行中: {nodes.find(n => n.id === activeNodeId)?.data.label}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 底部消息列表 */}
          <div className="px-4 py-2 border-t border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shrink-0 max-h-[140px] overflow-y-auto">
            <div className="text-[10px] text-zinc-400 mb-1.5 font-mono">最近消息</div>
            <div className="space-y-1">
              {[...messages]
                .slice(-5)
                .reverse()
                .map((msg, idx) => {
                  const { className } = getRoleDisplayName(msg.role);
                  const isStreaming = msg.role === "assistant" && idx === 0;
                  const color = getNodeColor(msg.role);

                  return (
                    <div
                      key={idx}
                      className={cn(
                        "flex items-center gap-2 px-2 py-1 rounded text-[10px] border",
                        isStreaming && "ring-1 ring-blue-400"
                      )}
                      style={{
                        backgroundColor: color.bg,
                        borderColor: color.border,
                      }}
                    >
                      <span className="font-semibold truncate" style={{ color: color.text }}>
                        {className}
                      </span>
                      {isStreaming && <Loader2 className="w-3 h-3 animate-spin shrink-0" style={{ color: color.text }} />}
                      <span className="text-zinc-600 dark:text-zinc-400 truncate flex-1">
                        {msg.role}
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// 节点卡片
function NodeCard({ node, index }: { node: FlowNode; index: number }) {
  const isRunning = node.data.status === "running";
  const isError = node.data.status === "error";

  const color = node.data.role
    ? getNodeColor(node.data.role)
    : {
        bg: isRunning ? "#DBEAFE" : isError ? "#FEE2E2" : "#DCFCE7",
        border: isRunning ? "#3B82F6" : isError ? "#EF4444" : "#22C55E",
        text: isRunning ? "#2563EB" : isError ? "#DC2626" : "#16A34A",
      };

  const Icon = node.type === "start" ? Play : node.type === "end" ? Square : Bot;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      className={cn(
        "w-full h-full rounded-lg border-2 flex flex-col items-center justify-center gap-0.5 p-1",
        "shadow-sm transition-all duration-300",
        isRunning && "ring-2 ring-blue-400 ring-offset-1 shadow-md"
      )}
      style={{
        backgroundColor: color.bg,
        borderColor: color.border,
      }}
    >
      <Icon className="w-3.5 h-3.5" style={{ color: color.text }} />
      <span
        className="text-[9px] font-bold text-center truncate w-full leading-tight"
        style={{ color: color.text }}
        title={node.data.label}
      >
        {node.data.label}
      </span>
      {isRunning && node.data.activeMsgType && (
        <span className="text-[7px] px-1 rounded bg-blue-500 text-white">
          {node.data.activeMsgType.split('_')[0]}
        </span>
      )}
    </motion.div>
  );
}
