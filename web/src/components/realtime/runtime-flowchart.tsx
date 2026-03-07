"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Activity, GitBranch, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { globalEventEmitter } from "@/lib/event-emitter";
import type { RealtimeMessage } from "@/types/realtime-message";

// 运行时流程图节点定义
interface FlowNode {
  id: string;
  label: string;
  type: "start" | "process" | "decision" | "subprocess" | "end";
  x: number;
  y: number;
  description?: string;
}

interface FlowEdge {
  from: string;
  to: string;
  label?: string;
  animated?: boolean;
}

// Agent运行时流程定义
const RUNTIME_FLOW_NODES: FlowNode[] = [
  { id: "idle", label: "等待输入", type: "start", x: 200, y: 30, description: "等待用户消息" },
  { id: "receive", label: "接收消息", type: "process", x: 200, y: 90, description: "接收并解析用户输入" },
  { id: "planning", label: "任务规划", type: "process", x: 200, y: 150, description: "分析需求，制定执行计划" },
  { id: "llm_call", label: "LLM调用", type: "process", x: 200, y: 210, description: "调用大语言模型生成响应" },
  { id: "tool_check", label: "需要工具?", type: "decision", x: 200, y: 280, description: "判断是否需要调用工具" },
  { id: "tool_dispatch", label: "工具分发", type: "process", x: 80, y: 350, description: "选择合适的工具" },
  { id: "tool_execute", label: "执行工具", type: "subprocess", x: 80, y: 420, description: "执行工具调用" },
  { id: "subagent", label: "子代理", type: "subprocess", x: 320, y: 350, description: "委派给子代理执行" },
  { id: "result_process", label: "处理结果", type: "process", x: 200, y: 490, description: "处理工具返回结果" },
  { id: "stream_output", label: "流式输出", type: "process", x: 200, y: 560, description: "向用户展示结果" },
  { id: "complete", label: "完成", type: "end", x: 200, y: 630, description: "本轮对话结束" },
];

const RUNTIME_FLOW_EDGES: FlowEdge[] = [
  { from: "idle", to: "receive", animated: false },
  { from: "receive", to: "planning", animated: false },
  { from: "planning", to: "llm_call", animated: false },
  { from: "llm_call", to: "tool_check", animated: false },
  { from: "tool_check", to: "tool_dispatch", label: "是", animated: true },
  { from: "tool_check", to: "stream_output", label: "否", animated: false },
  { from: "tool_dispatch", to: "tool_execute", animated: true },
  { from: "tool_dispatch", to: "subagent", label: "委派", animated: true },
  { from: "tool_execute", to: "result_process", animated: false },
  { from: "subagent", to: "result_process", animated: false },
  { from: "result_process", to: "llm_call", animated: false },
  { from: "stream_output", to: "complete", animated: false },
];

// 节点状态类型
type NodeStatus = "idle" | "active" | "completed" | "error";

interface NodeState {
  status: NodeStatus;
  timestamp?: number;
  metadata?: Record<string, any>;
}

type RuntimeFlowState = Record<string, NodeState>;

// 根据消息类型映射到流程节点
function mapMessageToNode(message: RealtimeMessage): string | null {
  switch (message.type) {
    case "user_message":
      return "receive";
    case "assistant_thinking":
      return "planning";
    case "assistant_text":
      if (message.status === "streaming") {
        return "llm_call";
      }
      return "stream_output";
    case "tool_call":
      return "tool_dispatch";
    case "tool_result":
      return "result_process";
    default:
      return null;
  }
}

// 判断是否为子代理消息
function isSubagentMessage(message: RealtimeMessage): boolean {
  return message.agent_type?.startsWith("worker:") || false;
}

interface RuntimeFlowchartProps {
  isOpen: boolean;
  onClose: () => void;
  dialogId: string;
  className?: string;
}

export function RuntimeFlowchart({
  isOpen,
  onClose,
  dialogId,
  className,
}: RuntimeFlowchartProps) {
  const [nodeStates, setNodeStates] = useState<RuntimeFlowState>({});
  const [currentAgentType, setCurrentAgentType] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [roundCount, setRoundCount] = useState(0);

  // 更新节点状态
  const updateNodeState = useCallback((
    nodeId: string,
    status: NodeStatus,
    metadata?: Record<string, any>
  ) => {
    setNodeStates((prev) => ({
      ...prev,
      [nodeId]: {
        status,
        timestamp: Date.now(),
        metadata,
      },
    }));
  }, []);

  // 重置流程状态
  const resetFlow = useCallback(() => {
    setNodeStates({});
    setRoundCount(0);
    setCurrentAgentType(null);
  }, []);

  // 监听消息更新
  useEffect(() => {
    if (!isOpen || !dialogId) return;

    const handleMessageAdded = (event: { dialog_id: string; message: RealtimeMessage }) => {
      if (event.dialog_id !== dialogId) return;

      const message = event.message;
      const nodeId = mapMessageToNode(message);

      if (nodeId) {
        // 如果是流式消息，标记为活跃
        if (message.status === "streaming") {
          updateNodeState(nodeId, "active", {
            messageId: message.id,
            agentType: message.agent_type,
          });
          setIsRunning(true);
        } else if (message.status === "completed") {
          // 如果是完成状态，标记为已完成
          updateNodeState(nodeId, "completed", {
            messageId: message.id,
            agentType: message.agent_type,
          });
        }
      }

      // 更新代理类型
      if (message.agent_type) {
        setCurrentAgentType(message.agent_type);
      }

      // 检测是否为子代理
      if (isSubagentMessage(message)) {
        updateNodeState("subagent", message.status === "streaming" ? "active" : "completed", {
          workerType: message.agent_type?.replace("worker:", ""),
        });
      }
    };

    const handleMessageUpdated = (event: { dialog_id: string; message: RealtimeMessage }) => {
      if (event.dialog_id !== dialogId) return;

      const message = event.message;
      const nodeId = mapMessageToNode(message);

      if (nodeId) {
        if (message.status === "streaming") {
          updateNodeState(nodeId, "active");
          setIsRunning(true);
        } else if (message.status === "completed") {
          updateNodeState(nodeId, "completed");
          setIsRunning(false);
        }
      }
    };

    const handleNewDialog = () => {
      resetFlow();
    };

    // 订阅事件
    const unsubscribeAdded = globalEventEmitter.on("message:added", handleMessageAdded);
    const unsubscribeUpdated = globalEventEmitter.on("message:updated", handleMessageUpdated);
    const unsubscribeDialog = globalEventEmitter.on("dialog:created", handleNewDialog);

    // 初始状态
    updateNodeState("idle", "active");

    return () => {
      unsubscribeAdded();
      unsubscribeUpdated();
      unsubscribeDialog();
    };
  }, [isOpen, dialogId, updateNodeState, resetFlow]);

  // 获取节点状态颜色
  const getNodeColor = (nodeId: string) => {
    const state = nodeStates[nodeId];
    if (!state) return "var(--color-text-secondary)";

    switch (state.status) {
      case "active":
        return "#3B82F6"; // blue-500
      case "completed":
        return "#10B981"; // emerald-500
      case "error":
        return "#EF4444"; // red-500
      default:
        return "var(--color-text-secondary)";
    }
  };

  // 获取节点背景色
  const getNodeBgColor = (nodeId: string) => {
    const state = nodeStates[nodeId];
    if (!state) return "transparent";

    switch (state.status) {
      case "active":
        return "rgba(59, 130, 246, 0.1)";
      case "completed":
        return "rgba(16, 185, 129, 0.1)";
      case "error":
        return "rgba(239, 68, 68, 0.1)";
      default:
        return "transparent";
    }
  };

  // 渲染节点
  const renderNode = (node: FlowNode) => {
    const color = getNodeColor(node.id);
    const bgColor = getNodeBgColor(node.id);
    const state = nodeStates[node.id];
    const isActive = state?.status === "active";

    const baseClasses = "transition-all duration-300";
    const activeClasses = isActive ? "animate-pulse" : "";

    if (node.type === "decision") {
      const size = 40;
      return (
        <g key={node.id} className={cn(baseClasses, activeClasses)}>
          <motion.polygon
            points={`${node.x},${node.y - size} ${node.x + size},${node.y} ${node.x},${node.y + size} ${node.x - size},${node.y}`}
            fill={bgColor}
            stroke={color}
            strokeWidth={isActive ? 3 : 2}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3 }}
          />
          <text
            x={node.x}
            y={node.y - 5}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={10}
            fontWeight={600}
            fill={color}
          >
            {node.label}
          </text>
          {isActive && (
            <foreignObject x={node.x - 8} y={node.y + 5} width={16} height={16}>
              <Loader2 className="w-4 h-4 animate-spin" style={{ color }} />
            </foreignObject>
          )}
        </g>
      );
    }

    if (node.type === "start" || node.type === "end") {
      const width = 100;
      const height = 32;
      return (
        <g key={node.id} className={cn(baseClasses, activeClasses)}>
          <motion.rect
            x={node.x - width / 2}
            y={node.y - height / 2}
            width={width}
            height={height}
            rx={height / 2}
            fill={bgColor}
            stroke={color}
            strokeWidth={isActive ? 3 : 2}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3 }}
          />
          <text
            x={node.x}
            y={node.y}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={11}
            fontWeight={600}
            fill={color}
          >
            {node.label}
          </text>
        </g>
      );
    }

    const width = node.type === "subprocess" ? 110 : 100;
    const height = 36;
    return (
      <g key={node.id} className={cn(baseClasses, activeClasses)}>
        <motion.rect
          x={node.x - width / 2}
          y={node.y - height / 2}
          width={width}
          height={height}
          rx={4}
          fill={bgColor}
          stroke={color}
          strokeWidth={isActive ? 3 : 2}
          strokeDasharray={node.type === "subprocess" ? "5 3" : undefined}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.3 }}
        />
        <text
          x={node.x}
          y={node.y}
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={10}
          fontWeight={500}
          fill={color}
        >
          {node.label}
        </text>
        {isActive && node.id === "subagent" && (
          <foreignObject x={node.x + width / 2 - 10} y={node.y - 8} width={16} height={16}>
            <GitBranch className="w-4 h-4" style={{ color }} />
          </foreignObject>
        )}
      </g>
    );
  };

  // 渲染边
  const renderEdge = (edge: FlowEdge, index: number) => {
    const fromNode = RUNTIME_FLOW_NODES.find((n) => n.id === edge.from);
    const toNode = RUNTIME_FLOW_NODES.find((n) => n.id === edge.to);
    if (!fromNode || !toNode) return null;

    const isActive =
      nodeStates[edge.from]?.status === "active" ||
      nodeStates[edge.to]?.status === "active";

    const d = `M ${fromNode.x} ${fromNode.y + 20} L ${toNode.x} ${toNode.y - 20}`;

    return (
      <g key={`${edge.from}-${edge.to}`}>
        <motion.path
          d={d}
          fill="none"
          stroke={isActive ? "#3B82F6" : "var(--color-border)"}
          strokeWidth={isActive ? 2 : 1}
          markerEnd="url(#arrowhead-runtime)"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.5, delay: index * 0.1 }}
        />
        {edge.label && (
          <text
            x={(fromNode.x + toNode.x) / 2 + 5}
            y={(fromNode.y + toNode.y) / 2 - 5}
            fontSize={9}
            fill="var(--color-text-secondary)"
          >
            {edge.label}
          </text>
        )}
      </g>
    );
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "absolute top-14 left-4 right-4 z-50",
            "bg-white dark:bg-zinc-900",
            "rounded-xl border border-zinc-200 dark:border-zinc-700",
            "shadow-xl",
            className
          )}
        >
          {/* 头部 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-700">
            <div className="flex items-center gap-3">
              <Activity className={cn(
                "w-5 h-5",
                isRunning ? "text-blue-500 animate-pulse" : "text-zinc-500"
              )} />
              <div>
                <h3 className="font-semibold text-zinc-800 dark:text-zinc-200">
                  运行时流程图
                </h3>
                <p className="text-xs text-zinc-500">
                  {isRunning ? "运行中" : "等待中"}
                  {currentAgentType && ` · ${currentAgentType}`}
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

          {/* 流程图 */}
          <div className="p-4 overflow-x-auto">
            <svg
              viewBox="0 0 400 680"
              className="mx-auto w-full max-w-[400px]"
              style={{ minHeight: 400 }}
            >
              <defs>
                <marker
                  id="arrowhead-runtime"
                  markerWidth={8}
                  markerHeight={6}
                  refX={7}
                  refY={3}
                  orient="auto"
                >
                  <polygon
                    points="0 0, 8 3, 0 6"
                    fill="var(--color-text-secondary)"
                  />
                </marker>
              </defs>

              {/* 渲染边 */}
              {RUNTIME_FLOW_EDGES.map((edge, i) => renderEdge(edge, i))}

              {/* 渲染节点 */}
              {RUNTIME_FLOW_NODES.map((node) => renderNode(node))}
            </svg>
          </div>

          {/* 状态栏 */}
          <div className="px-4 py-3 border-t border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50 rounded-b-xl">
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  运行中
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  已完成
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-zinc-400" />
                  等待中
                </span>
              </div>
              {roundCount > 0 && (
                <span>已运行 {roundCount} 轮</span>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
