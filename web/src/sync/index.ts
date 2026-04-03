/**
 * Sync 模块统一导出
 *
 * WebSocket 同步层：
 * - ConnectionManager: 连接管理
 * - OptimisticUpdateManager: 乐观更新管理
 * - MessageHandler: 消息处理器
 */

export {
  ConnectionManager,
  getConnectionManager,
  createConnectionManager,
} from './connection';

export {
  OptimisticUpdateManager,
  getOptimisticUpdateManager,
  createOptimisticUpdateManager,
} from './optimistic-update';

export { MessageHandler } from './message-handler';
