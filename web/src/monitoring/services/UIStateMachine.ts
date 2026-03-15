/**
 * UIStateMachine - UI 状态机
 *
 * 管理 Agent 状态，与后端 StateMachine 对应
 */

import { AgentState } from '../domain/AgentNode';

export interface StateTransition {
  fromState: AgentState;
  toState: AgentState;
  timestamp: Date;
  trigger?: string;
  durationMs?: number;
}

export class UIStateMachine {
  private _currentState: AgentState;
  private _history: StateTransition[];
  private _enteredAt: Date;

  constructor() {
    this._currentState = AgentState.IDLE;
    this._history = [];
    this._enteredAt = new Date();
  }

  /**
   * 执行状态转换
   */
  transition(toState: AgentState, trigger?: string): boolean {
    const fromState = this._currentState;

    // 计算持续时间
    const durationMs = new Date().getTime() - this._enteredAt.getTime();

    // 记录转换
    const transition: StateTransition = {
      fromState,
      toState,
      timestamp: new Date(),
      trigger,
      durationMs,
    };
    this._history.push(transition);

    // 更新状态
    this._currentState = toState;
    this._enteredAt = new Date();

    return true;
  }

  /**
   * 获取当前状态
   */
  getCurrentState(): AgentState {
    return this._currentState;
  }

  /**
   * 获取状态历史
   */
  getHistory(): StateTransition[] {
    return [...this._history];
  }

  /**
   * 获取在当前状态的持续时间（毫秒）
   */
  getTimeInStateMs(): number {
    return new Date().getTime() - this._enteredAt.getTime();
  }

  /**
   * 重置状态机
   */
  reset(): void {
    this._currentState = AgentState.IDLE;
    this._history = [];
    this._enteredAt = new Date();
  }
}
