/**
 * 过滤器便捷函数
 */

import { EventFilter } from './EventFilter';
import { MonitoringEvent, EventType } from './Event';

/**
 * 创建事件过滤器
 */
export function filterEvents(): EventFilter {
  return new EventFilter();
}

/**
 * 按类型过滤
 */
export function filterByType(
  events: MonitoringEvent[],
  type: EventType
): MonitoringEvent[] {
  return new EventFilter().type(type).apply(events);
}

/**
 * 按时间范围过滤
 */
export function filterByTimeRange(
  events: MonitoringEvent[],
  start: Date,
  end: Date
): MonitoringEvent[] {
  return new EventFilter().timeRange(start, end).apply(events);
}
