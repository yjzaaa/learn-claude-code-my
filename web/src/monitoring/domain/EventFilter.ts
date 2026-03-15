/**
 * EventFilter - 事件过滤器
 *
 * 支持链式调用、AND/OR 条件组合的类型安全事件过滤器
 */

import { MonitoringEvent, EventType, EventPriority } from './Event';

type FilterPredicate = (event: MonitoringEvent) => boolean;

type FilterOperator = 'AND' | 'OR';

interface FilterCondition {
  operator: FilterOperator;
  predicate: FilterPredicate;
}

/**
 * 事件过滤器类
 *
 * 示例:
 * ```typescript
 * const filter = new EventFilter()
 *   .type(EventType.AGENT_STARTED)
 *   .priority(EventPriority.HIGH)
 *   .or()
 *   .source('background-task');
 *
 * const results = filter.apply(events);
 * ```
 */
export class EventFilter {
  private conditions: FilterCondition[] = [];
  private currentOperator: FilterOperator = 'AND';

  /**
   * 设置下一个条件为 OR 关系
   */
  or(): this {
    this.currentOperator = 'OR';
    return this;
  }

  /**
   * 设置下一个条件为 AND 关系（默认）
   */
  and(): this {
    this.currentOperator = 'AND';
    return this;
  }

  /**
   * 按事件类型过滤
   */
  type(eventType: EventType): this {
    this.addCondition((event) => event.type === eventType);
    return this;
  }

  /**
   * 按事件类型列表过滤（匹配任一）
   */
  types(eventTypes: EventType[]): this {
    this.addCondition((event) => eventTypes.includes(event.type));
    return this;
  }

  /**
   * 按优先级过滤
   */
  priority(priority: EventPriority): this {
    this.addCondition((event) => event.priority === priority);
    return this;
  }

  /**
   * 按最低优先级过滤（包含更高优先级）
   */
  minPriority(priority: EventPriority): this {
    this.addCondition((event) => event.priority <= priority);
    return this;
  }

  /**
   * 按来源过滤
   */
  source(sourcePattern: string | RegExp): this {
    if (typeof sourcePattern === 'string') {
      this.addCondition((event) => event.source === sourcePattern);
    } else {
      this.addCondition((event) => sourcePattern.test(event.source));
    }
    return this;
  }

  /**
   * 按对话框 ID 过滤
   */
  dialogId(dialogId: string): this {
    this.addCondition((event) => event.dialogId === dialogId);
    return this;
  }

  /**
   * 按上下文 ID 过滤
   */
  contextId(contextId: string): this {
    this.addCondition((event) => event.contextId === contextId);
    return this;
  }

  /**
   * 按父事件 ID 过滤（查找子事件）
   */
  parentId(parentId: string): this {
    this.addCondition((event) => event.parentId === parentId);
    return this;
  }

  /**
   * 按是否为根事件过滤（无父事件）
   */
  rootEvents(): this {
    this.addCondition((event) => event.parentId === undefined);
    return this;
  }

  /**
   * 按时间范围过滤
   */
  timeRange(start: Date, end: Date): this {
    this.addCondition(
      (event) => event.timestamp >= start && event.timestamp <= end
    );
    return this;
  }

  /**
   * 过滤指定时间之后的事件
   */
  after(timestamp: Date): this {
    this.addCondition((event) => event.timestamp >= timestamp);
    return this;
  }

  /**
   * 过滤指定时间之前的事件
   */
  before(timestamp: Date): this {
    this.addCondition((event) => event.timestamp <= timestamp);
    return this;
  }

  /**
   * 按 payload 中的字段值过滤
   */
  payloadField<T>(field: string, value: T): this {
    this.addCondition((event) => {
      const payload = event.payload;
      return payload[field] === value;
    });
    return this;
  }

  /**
   * 按 payload 中的字段值过滤（使用自定义比较器）
   */
  payloadMatch(field: string, matcher: (value: unknown) => boolean): this {
    this.addCondition((event) => {
      const payload = event.payload;
      return matcher(payload[field]);
    });
    return this;
  }

  /**
   * 按自定义条件过滤
   */
  custom(predicate: FilterPredicate): this {
    this.addCondition(predicate);
    return this;
  }

  /**
   * 创建嵌套过滤器组（括号效果）
   */
  group(groupFilter: EventFilter): this {
    this.conditions.push({
      operator: this.currentOperator,
      predicate: (event) => groupFilter.test(event),
    });
    this.currentOperator = 'AND';
    return this;
  }

  /**
   * 反转当前所有条件（NOT 效果）
   */
  not(): EventFilter {
    const invertedFilter = new EventFilter();
    invertedFilter.conditions = this.conditions.map((condition) => ({
      operator: condition.operator,
      predicate: (event: MonitoringEvent) => !condition.predicate(event),
    }));
    return invertedFilter;
  }

  /**
   * 测试单个事件是否匹配
   */
  test(event: MonitoringEvent): boolean {
    if (this.conditions.length === 0) {
      return true;
    }

    let result = this.conditions[0].predicate(event);

    for (let i = 1; i < this.conditions.length; i++) {
      const condition = this.conditions[i];
      if (condition.operator === 'AND') {
        result = result && condition.predicate(event);
      } else {
        result = result || condition.predicate(event);
      }
    }

    return result;
  }

  /**
   * 应用过滤器到事件列表
   */
  apply(events: MonitoringEvent[]): MonitoringEvent[] {
    return events.filter((event) => this.test(event));
  }

  /**
   * 应用过滤器并返回第一个匹配项
   */
  findFirst(events: MonitoringEvent[]): MonitoringEvent | undefined {
    return events.find((event) => this.test(event));
  }

  /**
   * 应用过滤器并返回匹配数量
   */
  count(events: MonitoringEvent[]): number {
    return events.filter((event) => this.test(event)).length;
  }

  /**
   * 检查是否存在匹配项
   */
  exists(events: MonitoringEvent[]): boolean {
    return events.some((event) => this.test(event));
  }

  /**
   * 重置过滤器
   */
  reset(): this {
    this.conditions = [];
    this.currentOperator = 'AND';
    return this;
  }

  /**
   * 克隆当前过滤器
   */
  clone(): EventFilter {
    const cloned = new EventFilter();
    cloned.conditions = [...this.conditions];
    cloned.currentOperator = this.currentOperator;
    return cloned;
  }

  /**
   * 获取过滤器描述（用于调试）
   */
  toString(): string {
    if (this.conditions.length === 0) {
      return 'EventFilter(empty)';
    }

    const descriptions = this.conditions.map((c, index) => {
      const prefix = index === 0 ? '' : ` ${c.operator} `;
      return `${prefix}(condition)`;
    });

    return `EventFilter(${descriptions.join('')})`;
  }

  private addCondition(predicate: FilterPredicate): void {
    this.conditions.push({
      operator: this.currentOperator,
      predicate,
    });
    this.currentOperator = 'AND';
  }
}
