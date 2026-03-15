/**
 * AgentNode - Agent 层级节点
 *
 * 用于构建 Agent 调用树，支持父子关系、状态管理和事件关联
 */

import { MonitoringEvent, EventType } from './Event';

export type AgentType = 'root' | 'subagent' | 'background_task';

export enum AgentState {
  IDLE = 'idle',
  INITIALIZING = 'initializing',
  THINKING = 'thinking',
  TOOL_CALLING = 'tool_calling',
  WAITING_FOR_TOOL = 'waiting_for_tool',
  SUBAGENT_RUNNING = 'subagent_running',
  BACKGROUND_TASKS = 'background_tasks',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  ERROR = 'error',
}

export interface PerformanceMetrics {
  tokenCount: { input: number; output: number };
  toolCalls: number;
  subagentCalls: number;
  latencyMs: number[];
  startTime?: Date;
  endTime?: Date;
}

export interface TreeNode<T> {
  data: T;
  children: TreeNode<T>[];
}

export interface AgentNodeData {
  id: string;
  name: string;
  type: AgentType;
  status?: AgentState;
  startTime: Date;
  parent?: AgentNode;
}

export class AgentNode {
  private _id: string;
  private _name: string;
  private _type: AgentType;
  private _status: AgentState;
  private _startTime: Date;
  private _endTime?: Date;
  private _metrics: PerformanceMetrics;
  private _parent?: AgentNode;
  private _children: AgentNode[];
  private _events: MonitoringEvent[];

  constructor(params: AgentNodeData) {
    this._id = params.id;
    this._name = params.name;
    this._type = params.type;
    this._status = params.status ?? AgentState.IDLE;
    this._startTime = params.startTime;
    this._parent = params.parent;
    this._children = [];
    this._events = [];
    this._metrics = {
      tokenCount: { input: 0, output: 0 },
      toolCalls: 0,
      subagentCalls: 0,
      latencyMs: [],
    };

    if (params.parent) {
      params.parent.addChild(this);
    }
  }

  // ========== 层级操作 ==========

  addChild(child: AgentNode): void {
    this._children.push(child);
    child._parent = this;
  }

  removeChild(childId: string): boolean {
    const index = this._children.findIndex((c) => c._id === childId);
    if (index >= 0) {
      this._children.splice(index, 1);
      return true;
    }
    return false;
  }

  findById(id: string): AgentNode | undefined {
    if (this._id === id) return this;
    for (const child of this._children) {
      const found = child.findById(id);
      if (found) return found;
    }
    return undefined;
  }

  findByPredicate(predicate: (node: AgentNode) => boolean): AgentNode | undefined {
    if (predicate(this)) return this;
    for (const child of this._children) {
      const found = child.findByPredicate(predicate);
      if (found) return found;
    }
    return undefined;
  }

  getDepth(): number {
    let depth = 0;
    let current: AgentNode | undefined = this._parent;
    while (current) {
      depth++;
      current = current._parent;
    }
    return depth;
  }

  getSiblings(): AgentNode[] {
    if (!this._parent) return [];
    return this._parent._children.filter((c) => c._id !== this._id);
  }

  getPath(): string[] {
    const path: string[] = [this._id];
    let current: AgentNode | undefined = this._parent;
    while (current) {
      path.unshift(current._id);
      current = current._parent;
    }
    return path;
  }

  // ========== 状态转换 ==========

  transitionState(newState: AgentState): void {
    this._status = newState;
  }

  complete(): void {
    this._status = AgentState.COMPLETED;
    this._endTime = new Date();
  }

  fail(error?: string): void {
    this._status = AgentState.ERROR;
    this._endTime = new Date();
    if (error) {
      this._metadata = { ...(this._metadata || {}), error };
    }
  }

  private _metadata?: Record<string, unknown>;

  // ========== 事件关联 ==========

  attachEvent(event: MonitoringEvent): void {
    this._events.push(event);
  }

  getEvents(type?: EventType): MonitoringEvent[] {
    if (!type) return [...this._events];
    return this._events.filter((e) => e.type === type);
  }

  getLatestEvent(): MonitoringEvent | undefined {
    return this._events[this._events.length - 1];
  }

  // ========== 序列化 ==========

  toTree(): TreeNode<AgentNode> {
    return {
      data: this,
      children: this._children.map((c) => c.toTree()),
    };
  }

  toFlatList(): AgentNode[] {
    const list: AgentNode[] = [this];
    for (const child of this._children) {
      list.push(...child.toFlatList());
    }
    return list;
  }

  // ========== Getters ==========

  get id(): string {
    return this._id;
  }

  get name(): string {
    return this._name;
  }

  get type(): AgentType {
    return this._type;
  }

  get status(): AgentState {
    return this._status;
  }

  get startTime(): Date {
    return this._startTime;
  }

  get endTime(): Date | undefined {
    return this._endTime;
  }

  get metrics(): PerformanceMetrics {
    return this._metrics;
  }

  get parent(): AgentNode | undefined {
    return this._parent;
  }

  get children(): AgentNode[] {
    return [...this._children];
  }

  // ========== 指标更新 ==========

  addTokens(type: 'input' | 'output', count: number): void {
    this._metrics.tokenCount[type] += count;
  }

  incrementToolCalls(): void {
    this._metrics.toolCalls++;
  }

  incrementSubagentCalls(): void {
    this._metrics.subagentCalls++;
  }

  recordLatency(ms: number): void {
    this._metrics.latencyMs.push(ms);
  }

  getTotalTokens(): number {
    return this._metrics.tokenCount.input + this._metrics.tokenCount.output;
  }

  getAverageLatency(): number {
    if (this._metrics.latencyMs.length === 0) return 0;
    const sum = this._metrics.latencyMs.reduce((a, b) => a + b, 0);
    return sum / this._metrics.latencyMs.length;
  }
}
