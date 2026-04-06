/**
 * MetricsCollector - 指标收集器
 *
 * 收集和聚合性能指标
 */

import { PerformanceMetrics } from '../domain/AgentNode';

export interface MetricsReport {
  tokenCount: { input: number; output: number };
  toolCalls: number;
  subagentCalls: number;
  averageLatency: number;
  p95Latency: number;
  durationMs: number;
}

export class MetricsCollector {
  private _metrics: PerformanceMetrics;
  private _startTime?: Date;
  private _endTime?: Date;

  constructor() {
    this._metrics = {
      tokenCount: { input: 0, output: 0 },
      toolCalls: 0,
      subagentCalls: 0,
      latencyMs: [],
    };
  }

  /**
   * 开始收集
   */
  start(): void {
    this._startTime = new Date();
  }

  /**
   * 停止收集
   */
  stop(): void {
    this._endTime = new Date();
  }

  /**
   * 添加 Token
   */
  addTokens(type: 'input' | 'output', count: number): void {
    this._metrics.tokenCount[type] += count;
  }

  /**
   * 增加工具调用计数
   */
  incrementToolCalls(): void {
    this._metrics.toolCalls++;
  }

  /**
   * 增加子智能体调用计数
   */
  incrementSubagentCalls(): void {
    this._metrics.subagentCalls++;
  }

  /**
   * 记录延迟
   */
  recordLatency(ms: number): void {
    this._metrics.latencyMs.push(ms);
  }

  /**
   * 获取总 Token 数
   */
  getTotalTokens(): number {
    return this._metrics.tokenCount.input + this._metrics.tokenCount.output;
  }

  /**
   * 获取平均延迟
   */
  getAverageLatency(): number {
    if (this._metrics.latencyMs.length === 0) return 0;
    const sum = this._metrics.latencyMs.reduce((a, b) => a + b, 0);
    return sum / this._metrics.latencyMs.length;
  }

  /**
   * 获取 P95 延迟
   */
  getP95Latency(): number {
    if (this._metrics.latencyMs.length === 0) return 0;
    const sorted = [...this._metrics.latencyMs].sort((a, b) => a - b);
    const index = Math.floor(sorted.length * 0.95);
    return sorted[index];
  }

  /**
   * 获取持续时间
   */
  getDurationMs(): number {
    if (!this._startTime) return 0;
    const end = this._endTime || new Date();
    return end.getTime() - this._startTime.getTime();
  }

  /**
   * 生成报告
   */
  getReport(): MetricsReport {
    return {
      tokenCount: { ...this._metrics.tokenCount },
      toolCalls: this._metrics.toolCalls,
      subagentCalls: this._metrics.subagentCalls,
      averageLatency: this.getAverageLatency(),
      p95Latency: this.getP95Latency(),
      durationMs: this.getDurationMs(),
    };
  }

  /**
   * 获取原始指标
   */
  getMetrics(): PerformanceMetrics {
    return {
      tokenCount: { ...this._metrics.tokenCount },
      toolCalls: this._metrics.toolCalls,
      subagentCalls: this._metrics.subagentCalls,
      latencyMs: [...this._metrics.latencyMs],
      startTime: this._startTime,
      endTime: this._endTime,
    };
  }

  /**
   * 重置
   */
  reset(): void {
    this._metrics = {
      tokenCount: { input: 0, output: 0 },
      toolCalls: 0,
      subagentCalls: 0,
      latencyMs: [],
    };
    this._startTime = undefined;
    this._endTime = undefined;
  }

  /**
   * 从后端数据同步
   */
  syncFromBackend(data: {
    tokenCount: { input: number; output: number };
    toolCalls: number;
    subagentCalls: number;
  }): void {
    this._metrics.tokenCount = { ...data.tokenCount };
    this._metrics.toolCalls = data.toolCalls;
    this._metrics.subagentCalls = data.subagentCalls;
  }
}
