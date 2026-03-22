/**
 * MonitoringStore - 监控状态管理
 *
 * 核心 Store 类，管理所有监控状态
 */

import {
  MonitoringEvent,
  EventType,
  AgentNode,
  AgentState,
  TreeNode,
} from '../domain';
import {
  EventDispatcher,
  UIStateMachine,
  MetricsCollector,
  WebSocketEventAdapter,
} from '../services';

export type StateSelector<T> = (store: MonitoringStore) => T;

export interface StoreSubscriber {
  selector: StateSelector<unknown>;
  callback: (current: unknown, previous: unknown) => void;
  lastValue: unknown;
}

export interface StoreServices {
  dispatcher: EventDispatcher;
  stateMachine: UIStateMachine;
  metricsCollector: MetricsCollector;
  wsAdapter: WebSocketEventAdapter;
}

export class MonitoringStore {
  // 依赖的服务
  private _dispatcher: EventDispatcher;
  private _stateMachine: UIStateMachine;
  private _metricsCollector: MetricsCollector;
  private _wsAdapter: WebSocketEventAdapter;

  // 状态数据
  private _rootAgent: AgentNode | null = null;
  private _activeAgentId: string | null = null;
  private _events: Map<string, MonitoringEvent> = new Map();
  private _streamingContent: string = '';
  private _streamingReasoning: string = '';
  private _subscribers: Set<StoreSubscriber> = new Set();

  // 缓存的快照（用于 useSyncExternalStore）
  private _snapshots: Map<StateSelector<unknown>, unknown> = new Map();

  constructor(services: StoreServices) {
    this._dispatcher = services.dispatcher;
    this._stateMachine = services.stateMachine;
    this._metricsCollector = services.metricsCollector;
    this._wsAdapter = services.wsAdapter;

    this._setupEventHandlers();
  }

  /**
   * 设置事件处理器
   */
  private _setupEventHandlers(): void {
    this._dispatcher.subscribe({
      onEvent: (event: MonitoringEvent) => this._handleEvent(event),
    });
  }

  /**
   * 处理事件
   */
  private _handleEvent(event: MonitoringEvent): void {
    // 调试日志
    console.log('[MonitoringStore] Handling event:', event.type, 'type value:', EventType.SUBAGENT_STARTED, event);

    // 保存事件
    this._events.set(event.id, event);
    console.log('[MonitoringStore] Event saved, total events:', this._events.size);

    // 根据类型路由 - 使用字符串比较确保匹配
    const eventType = event.type as string;

    if (eventType === EventType.AGENT_STARTED) {
      console.log('[MonitoringStore] Routing to _handleAgentStarted');
      this._handleAgentStarted(event);
    } else if (eventType === EventType.SUBAGENT_SPAWNED || eventType === EventType.SUBAGENT_STARTED) {
      console.log('[MonitoringStore] Routing to _handleSubagentSpawned');
      this._handleSubagentSpawned(event);
    } else if (eventType === EventType.MESSAGE_DELTA) {
      this._handleMessageDelta(event);
    } else if (eventType === EventType.REASONING_DELTA) {
      this._handleReasoningDelta(event);
    } else if (eventType === EventType.STATE_TRANSITION) {
      this._handleStateTransition(event);
    } else if (eventType === EventType.SUBAGENT_COMPLETED) {
      console.log('[MonitoringStore] Routing to _handleSubagentCompleted');
      this._handleSubagentCompleted(event);
    } else if (eventType === EventType.SUBAGENT_FAILED) {
      console.log('[MonitoringStore] Routing to _handleSubagentFailed');
      this._handleSubagentFailed(event);
    } else if (eventType === EventType.TOOL_CALL_START) {
      this._handleToolCallStart(event);
    } else if (eventType === EventType.TOKEN_USAGE) {
      this._handleTokenUsage(event);
    } else if (eventType === EventType.BG_TASK_QUEUED || eventType === EventType.BG_TASK_STARTED ||
               eventType === EventType.BG_TASK_PROGRESS || eventType === EventType.BG_TASK_COMPLETED ||
               eventType === EventType.BG_TASK_FAILED) {
      this._handleBgTaskEvent(event);
    } else {
      console.log('[MonitoringStore] Unknown event type:', eventType);
    }

    // 通知订阅者
    this._notifySubscribers(event);
    console.log('[MonitoringStore] Subscribers notified');
  }

  private _handleAgentStarted(event: MonitoringEvent): void {
    // 后端使用蛇形命名 (agent_name, bridge_id)
    const payload = event.payload as {
      agent_name?: string;
      bridge_id?: string;
      agentName?: string;
      bridgeId?: string;
    };

    const agentName = payload.agent_name || payload.agentName || 'Unknown Agent';
    const bridgeId = payload.bridge_id || payload.bridgeId || 'unknown';

    this._rootAgent = new AgentNode({
      id: bridgeId,
      name: agentName,
      type: 'root',
      startTime: event.timestamp,
    });
    this._activeAgentId = bridgeId;
    this._stateMachine.transition(AgentState.INITIALIZING);
    this._metricsCollector.start();
  }

  private _handleSubagentSpawned(event: MonitoringEvent): void {
    // 后端使用蛇形命名
    const payload = event.payload as {
      subagent_id?: string;
      subagent_name?: string;
      subagent_type?: string;
      parent_bridge_id?: string;
      subagentId?: string;
      subagentName?: string;
      subagentType?: string;
      parentBridgeId?: string;
    };

    // 子智能体 ID：优先使用 subagent_name，因为它在项目中应该是唯一的
    const subagentId = payload.subagent_name || payload.subagentName || payload.subagent_id || payload.subagentId || 'unknown';
    const subagentName = payload.subagent_name || payload.subagentName || 'Unknown Subagent';
    const subagentType = payload.subagent_type || payload.subagentType || 'Unknown';

    // source 字段格式为 "Subagent:Type:Name"，可以用来识别父级上下文
    // 但子智能体应该直接挂到根 Agent 下
    const parent = this._rootAgent;
    if (!parent) {
      console.warn('[MonitoringStore] Root agent not found when creating subagent:', subagentName);
      return;
    }

    // 检查是否已存在同名的子智能体
    const existingSubagent = parent.findById(subagentId);
    if (existingSubagent) {
      console.log('[MonitoringStore] Subagent already exists:', subagentId);
      this._activeAgentId = subagentId;
      return;
    }

    const child = new AgentNode({
      id: subagentId,
      name: `${subagentType}: ${subagentName}`,
      type: 'subagent',
      parent,
      startTime: event.timestamp,
    });

    console.log('[MonitoringStore] Subagent created:', subagentId, subagentName, subagentType);
    this._activeAgentId = subagentId;
  }

  private _handleMessageDelta(event: MonitoringEvent): void {
    const { delta } = event.payload as { delta: string };

    // 安全处理：如果 delta 不存在或不是字符串，则跳过
    if (typeof delta !== 'string') {
      return;
    }

    this._streamingContent += delta;

    // 更新指标
    const tokenCount = Math.ceil(delta.length / 4); // 粗略估算
    this._metricsCollector.addTokens('output', tokenCount);
  }

  private _handleReasoningDelta(event: MonitoringEvent): void {
    const { delta } = event.payload as { delta: string };

    // 安全处理：如果 delta 不存在或不是字符串，则跳过
    if (typeof delta !== 'string') {
      return;
    }

    this._streamingReasoning += delta;
  }

  private _handleStateTransition(event: MonitoringEvent): void {
    // 后端使用蛇形命名 to_state
    const payload = event.payload as { to_state?: AgentState; toState?: AgentState };
    const toState = payload.to_state || payload.toState;
    if (toState) {
      this._stateMachine.transition(toState);
    }
  }

  private _handleSubagentCompleted(event: MonitoringEvent): void {
    // 后端使用蛇形命名 subagent_id 或 subagent_name
    const payload = event.payload as { subagent_id?: string; subagentId?: string; subagent_name?: string };
    const subagentId = payload.subagent_id || payload.subagentId || payload.subagent_name;
    if (!subagentId) {
      console.warn('[MonitoringStore] SUBAGENT_COMPLETED missing subagent identifier:', event);
      return;
    }

    // 尝试通过 ID 或名称查找子智能体
    let subagent = this._rootAgent?.findById(subagentId);
    if (!subagent && this._rootAgent) {
      // 尝试在子节点中通过名称查找
      const flatList = this._rootAgent.toFlatList();
      subagent = flatList.find(a => a.name === subagentId || a.id === subagentId);
    }

    if (subagent) {
      subagent.complete();
      console.log('[MonitoringStore] Subagent completed:', subagentId);
    } else {
      console.warn('[MonitoringStore] Subagent not found for completion:', subagentId);
    }

    if (this._activeAgentId === subagentId) {
      this._activeAgentId = this._rootAgent?.id ?? null;
    }
  }

  private _handleSubagentFailed(event: MonitoringEvent): void {
    // 后端使用蛇形命名 subagent_id 或 subagent_name
    const payload = event.payload as { subagent_id?: string; subagentId?: string; subagent_name?: string; error?: string };
    const subagentId = payload.subagent_id || payload.subagentId || payload.subagent_name;
    if (!subagentId) {
      console.warn('[MonitoringStore] SUBAGENT_FAILED missing subagent identifier:', event);
      return;
    }

    // 尝试通过 ID 或名称查找子智能体
    let subagent = this._rootAgent?.findById(subagentId);
    if (!subagent && this._rootAgent) {
      const flatList = this._rootAgent.toFlatList();
      subagent = flatList.find(a => a.name === subagentId || a.id === subagentId);
    }

    if (subagent) {
      subagent.fail(payload.error || 'Unknown error');
      console.log('[MonitoringStore] Subagent failed:', subagentId, payload.error);
    } else {
      console.warn('[MonitoringStore] Subagent not found for failure:', subagentId);
    }

    if (this._activeAgentId === subagentId) {
      this._activeAgentId = this._rootAgent?.id ?? null;
    }
  }

  private _handleToolCallStart(event: MonitoringEvent): void {
    this._metricsCollector.incrementToolCalls();
  }

  private _handleTokenUsage(event: MonitoringEvent): void {
    // 后端可能使用蛇形命名 prompt_tokens, completion_tokens, total_tokens
    const payload = event.payload as {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
      token_count?: { input: number; output: number };
      tokenCount?: { input: number; output: number };
    };

    // 尝试从后端格式转换
    const tokenCount = payload.token_count || payload.tokenCount || {
      input: payload.prompt_tokens || 0,
      output: payload.completion_tokens || 0,
    };

    this._metricsCollector.syncFromBackend({
      tokenCount,
      toolCalls: 0,
      subagentCalls: 0,
    });
  }

  private _handleBgTaskEvent(event: MonitoringEvent): void {
    // 处理后台任务事件
    const payload = event.payload as {
      task_id?: string;
      command?: string;
      status?: string;
      output?: string;
      error?: string;
      exit_code?: number;
      duration_ms?: number;
    };

    const taskId = payload.task_id || 'unknown';
    console.log(`[MonitoringStore] Background task event: ${event.type}, task: ${taskId}`);

    // 后台任务事件已经保存在 _events 中，可以在 UI 中显示
    // 这里可以添加更多的处理逻辑，比如更新后台任务列表等
  }

  private _notifySubscribers(event: MonitoringEvent): void {
    // 清除快照缓存，因为状态已变化
    this._snapshots.clear();

    for (const subscriber of this._subscribers) {
      const currentValue = subscriber.selector(this);
      if (currentValue !== subscriber.lastValue) {
        subscriber.callback(currentValue, subscriber.lastValue);
        subscriber.lastValue = currentValue;
      }
    }
  }

  // ========== 公共 API ==========

  /**
   * 获取 Agent 层级
   */
  getAgentHierarchy(): TreeNode<AgentNode> | null {
    return this._rootAgent?.toTree() ?? null;
  }

  /**
   * 获取流式内容
   */
  getStreamingContent(): { content: string; reasoning: string } {
    return {
      content: this._streamingContent,
      reasoning: this._streamingReasoning,
    };
  }

  /**
   * 获取当前 Agent 状态
   */
  getAgentState(): AgentState {
    return this._stateMachine.getCurrentState();
  }

  /**
   * 获取活动 Agent ID
   */
  getActiveAgentId(): string | null {
    return this._activeAgentId;
  }

  /**
   * 获取根 Agent
   */
  getRootAgent(): AgentNode | null {
    return this._rootAgent;
  }

  /**
   * 获取所有活动 Agent
   */
  getActiveAgents(): AgentNode[] {
    if (!this._rootAgent) return [];
    return this._rootAgent
      .toFlatList()
      .filter((a) => a.status !== AgentState.COMPLETED && a.status !== AgentState.ERROR);
  }

  /**
   * 通过 ID 获取事件
   */
  getEventById(id: string): MonitoringEvent | undefined {
    return this._events.get(id);
  }

  /**
   * 获取所有事件
   */
  getAllEvents(): MonitoringEvent[] {
    return Array.from(this._events.values());
  }

  /**
   * 获取指标报告
   */
  getMetricsReport() {
    return this._metricsCollector.getReport();
  }

  /**
   * 订阅状态变化
   */
  subscribe<T>(
    selector: StateSelector<T>,
    callback: (current: T, previous: T) => void
  ): () => void {
    const subscriber: StoreSubscriber = {
      selector: selector as StateSelector<unknown>,
      callback: callback as (current: unknown, previous: unknown) => void,
      lastValue: undefined,
    };
    this._subscribers.add(subscriber);
    return () => this._subscribers.delete(subscriber);
  }

  /**
   * 连接 WebSocket 并订阅对话
   */
  async connect(dialogId?: string): Promise<void> {
    await this._wsAdapter.connect();
    // 订阅特定对话或所有对话（使用通配符）
    this._wsAdapter.subscribe(dialogId || '*');
  }

  /**
   * 订阅特定对话
   */
  subscribeToDialog(dialogId: string): void {
    this._wsAdapter.subscribe(dialogId);
  }

  /**
   * 直接分发事件到 store
   * 用于从外部（如 useWebSocket）接收事件
   */
  dispatchEvent(event: MonitoringEvent): void {
    this._handleEvent(event);
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this._wsAdapter.disconnect();
  }

  /**
   * 清理
   */
  destroy(): void {
    this.disconnect();
    this._subscribers.clear();
    this._events.clear();
    this._snapshots.clear();
  }

  /**
   * 获取缓存的快照（用于 useSyncExternalStore）
   * 确保相同的 selector 在状态未变化时返回相同的引用
   */
  getSnapshot<T>(selector: StateSelector<T>): T {
    if (!this._snapshots.has(selector)) {
      this._snapshots.set(selector, selector(this));
    }
    return this._snapshots.get(selector) as T;
  }
}
