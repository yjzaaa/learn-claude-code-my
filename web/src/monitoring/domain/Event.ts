/**
 * MonitoringEvent - 监控事件领域模型
 *
 * 与后端 MonitoringEvent 对应，不可变值对象
 */

export enum EventPriority {
  CRITICAL = 0,
  HIGH = 1,
  NORMAL = 2,
  LOW = 3,
}

export enum EventType {
  // Agent 生命周期
  AGENT_STARTED = 'agent:started',
  AGENT_STOPPED = 'agent:stopped',
  AGENT_ERROR = 'agent:error',
  AGENT_PAUSED = 'agent:paused',
  AGENT_RESUMED = 'agent:resumed',

  // 消息流
  MESSAGE_START = 'message:start',
  MESSAGE_DELTA = 'message:delta',
  MESSAGE_COMPLETE = 'message:complete',
  REASONING_DELTA = 'reasoning:delta',

  // 工具调用
  TOOL_CALL_START = 'tool_call:start',
  TOOL_CALL_END = 'tool_call:end',
  TOOL_CALL_ERROR = 'tool_call:error',
  TOOL_RESULT = 'tool:result',

  // 子智能体
  SUBAGENT_SPAWNED = 'subagent:spawned',
  SUBAGENT_STARTED = 'subagent:started',
  SUBAGENT_PROGRESS = 'subagent:progress',
  SUBAGENT_COMPLETED = 'subagent:completed',
  SUBAGENT_FAILED = 'subagent:failed',

  // 后台任务
  BG_TASK_QUEUED = 'bg_task:queued',
  BG_TASK_STARTED = 'bg_task:started',
  BG_TASK_PROGRESS = 'bg_task:progress',
  BG_TASK_COMPLETED = 'bg_task:completed',
  BG_TASK_FAILED = 'bg_task:failed',

  // 状态机
  STATE_TRANSITION = 'state:transition',
  STATE_ENTER = 'state:enter',
  STATE_EXIT = 'state:exit',

  // 资源使用
  TOKEN_USAGE = 'metrics:tokens',
  MEMORY_USAGE = 'metrics:memory',
  LATENCY_METRIC = 'metrics:latency',

  // Todo
  TODO_CREATED = 'todo:created',
  TODO_UPDATED = 'todo:updated',
  TODO_COMPLETED = 'todo:completed',
}

export interface MonitoringEventData {
  id?: string;
  type: EventType;
  timestamp?: string;
  source: string;
  dialogId: string;
  contextId: string;
  parentId?: string;
  priority?: EventPriority;
  payload?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export class MonitoringEvent {
  private readonly _id: string;
  private readonly _type: EventType;
  private readonly _timestamp: Date;
  private readonly _source: string;
  private readonly _dialogId: string;
  private readonly _contextId: string;
  private readonly _parentId?: string;
  private readonly _priority: EventPriority;
  private readonly _payload: Record<string, unknown>;
  private readonly _metadata: Record<string, unknown>;

  constructor(params: MonitoringEventData) {
    this._id = params.id ?? crypto.randomUUID();
    this._type = params.type;
    this._timestamp = params.timestamp ? new Date(params.timestamp) : new Date();
    this._source = params.source;
    this._dialogId = params.dialogId;
    this._contextId = params.contextId;
    this._parentId = params.parentId;
    this._priority = params.priority ?? EventPriority.NORMAL;
    this._payload = params.payload ?? {};
    this._metadata = params.metadata ?? {};
  }

  // Getters
  get id(): string {
    return this._id;
  }

  get type(): EventType {
    return this._type;
  }

  get timestamp(): Date {
    return this._timestamp;
  }

  get source(): string {
    return this._source;
  }

  get dialogId(): string {
    return this._dialogId;
  }

  get contextId(): string {
    return this._contextId;
  }

  get parentId(): string | undefined {
    return this._parentId;
  }

  get priority(): EventPriority {
    return this._priority;
  }

  get payload(): Record<string, unknown> {
    return { ...this._payload };
  }

  get metadata(): Record<string, unknown> {
    return { ...this._metadata };
  }

  /**
   * 检查是否为指定事件的子事件
   */
  isChildOf(parent: MonitoringEvent): boolean {
    return this._parentId === parent.id;
  }

  /**
   * 计算自指定时间以来的毫秒数
   */
  getDurationMs(since: Date): number {
    return this._timestamp.getTime() - since.getTime();
  }

  /**
   * 序列化为 JSON
   */
  toJSON(): object {
    return {
      id: this._id,
      type: this._type,
      timestamp: this._timestamp.toISOString(),
      source: this._source,
      dialogId: this._dialogId,
      contextId: this._contextId,
      parentId: this._parentId,
      priority: this._priority,
      payload: this._payload,
      metadata: this._metadata,
    };
  }

  /**
   * 从 WebSocket 数据创建事件
   *
   * 后端会添加 `monitor:` 前缀到所有事件类型，这里需要移除前缀
   * 例如：`monitor:agent:started` -> `agent:started`
   */
  static fromWebSocket(data: unknown): MonitoringEvent {
    const parsed = data as Record<string, unknown>;

    // 移除 monitor: 前缀
    let eventTypeStr = parsed.type as string;
    if (eventTypeStr.startsWith('monitor:')) {
      eventTypeStr = eventTypeStr.slice(8); // 移除 'monitor:' 前缀
    }

    // 将字符串转换为 EventType 枚举值
    // 首先尝试直接匹配枚举值
    let eventType: EventType | undefined;

    // 遍历所有 EventType 枚举值，找到匹配的
    for (const [key, value] of Object.entries(EventType)) {
      if (value === eventTypeStr) {
        eventType = value as EventType;
        break;
      }
    }

    // 如果没找到匹配，使用字符串值（兼容未知事件类型）
    if (!eventType) {
      console.warn(`[MonitoringEvent] Unknown event type: ${eventTypeStr}`);
      eventType = eventTypeStr as EventType;
    }

    return new MonitoringEvent({
      id: parsed.id as string,
      type: eventType,
      timestamp: parsed.timestamp as string,
      source: parsed.source as string,
      dialogId: parsed.dialog_id as string,
      contextId: parsed.context_id as string,
      parentId: parsed.parent_id as string | undefined,
      priority: parsed.priority as EventPriority | undefined,
      payload: parsed.payload as Record<string, unknown> | undefined,
      metadata: parsed.metadata as Record<string, unknown> | undefined,
    });
  }

  /**
   * 创建子事件
   */
  static createChild(
    parent: MonitoringEvent,
    type: EventType,
    payload: Record<string, unknown>,
    priority: EventPriority = EventPriority.NORMAL,
    metadata?: Record<string, unknown>
  ): MonitoringEvent {
    return new MonitoringEvent({
      type,
      source: parent.source,
      dialogId: parent.dialogId,
      contextId: parent.contextId,
      parentId: parent.id,
      priority,
      payload,
      metadata,
    });
  }
}
