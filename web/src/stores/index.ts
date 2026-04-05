/**
 * Stores 统一导出
 *
 * 按领域划分的状态管理：
 * - DialogStore: 对话领域状态
 * - MessageStore: 消息领域状态
 * - StatusStore: 应用状态和错误管理
 * - SyncStore: 同步领域状态
 * - UIStore: UI 状态
 */

export {
  useDialogStore,
  selectCurrentDialog,
  selectDialogList,
  type Dialog,
  type DialogSummary,
  type DialogState,
} from './dialog-store';

export {
  useMessageStore,
  type Message,
  type MessageRole,
  type MessageStatus,
  type PendingMessage,
  type MessageState,
} from './message-store';

export {
  useStatusStore,
  type ConnectionStatus,
  type AppStatus,
  type StatusStoreState,
} from './status-store';

export {
  useSyncStore,
  selectSyncStatus,
  selectConnectionStatus,
  type ConnectionStatus as SyncConnectionStatus,
  type SyncError,
  type SyncState,
} from './sync-store';

// 保持向后兼容，导出原有的 UI store
export { useUIStore, type Theme, type FontMode, type LayoutMode } from './ui';
