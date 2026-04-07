# 记忆系统可视化组件设计文档

## 概述

本文档定义了记忆系统（Memory System）的可视化组件设计，包括组件结构、Props 接口、样式规范和使用示例。

## 组件清单

### 1. MemoryPanel - 记忆面板（侧边栏）

主容器组件，以侧边栏形式展示记忆列表。

#### Props 接口

```typescript
interface MemoryPanelProps {
  /** 记忆列表数据 */
  memories: MemoryItemData[];
  /** 当前选中的记忆ID */
  activeMemoryId?: string;
  /** WebSocket连接状态 */
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  /** 最后更新时间 */
  lastUpdatedAt?: string;
  /** 是否展开 */
  isOpen: boolean;
  /** 选择记忆回调 */
  onSelectMemory: (memory: MemoryItemData) => void;
  /** 新建记忆回调 */
  onCreateMemory: () => void;
  /** 刷新列表回调 */
  onRefresh: () => void;
  /** 关闭面板回调 */
  onClose: () => void;
}

interface MemoryItemData {
  id: string;
  name: string;
  description: string;
  type: 'user' | 'feedback' | 'project' | 'reference';
  content: string;
  createdAt: string;
  updatedAt: string;
}
```

#### 布局结构

```
┌─────────────────────────────────────┐
│  记忆库                    [刷新][+] │  ← Header (40px)
├─────────────────────────────────────┤
│  ● 已连接 | 12条记忆 | 2分钟前      │  ← Status Bar (32px)
├─────────────────────────────────────┤
│                                     │
│  [用户] 用户偏好设置        3天前   │  ← Memory Item
│  [反馈] 代码审查反馈        1周前   │
│  [项目] 架构决策记录        2周前   │
│  [参考] API文档链接         1月前   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  📄 暂无记忆                │   │  ← Empty State
│  │  点击 + 创建第一条记忆      │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

#### 样式规范

- **宽度**: `280px`（与 SessionSidebar 一致）
- **背景**: `var(--sidebar-bg)`
- **边框**: 右侧 `1px solid var(--border)`
- **Header 高度**: `40px`
- **内边距**: `var(--space-md)`（16px）

---

### 2. MemoryItem - 记忆项

单个记忆卡片组件，支持展开/收起显示详情。

#### Props 接口

```typescript
interface MemoryItemProps {
  /** 记忆数据 */
  memory: MemoryItemData;
  /** 是否选中 */
  isActive: boolean;
  /** 是否展开 */
  isExpanded: boolean;
  /** 选择回调 */
  onSelect: (memory: MemoryItemData) => void;
  /** 展开/收起回调 */
  onToggleExpand: (memoryId: string) => void;
  /** 编辑回调 */
  onEdit: (memory: MemoryItemData) => void;
  /** 删除回调 */
  onDelete: (memoryId: string) => void;
}
```

#### 布局结构

```
┌─────────────────────────────────────────────────┐
│ [用户] 用户角色偏好                    [展开▼]  │  ← Header
├─────────────────────────────────────────────────┤
│ 创建于 2024-01-15 · 更新于 2天前               │  ← Meta
│                                                 │
│ 用户是高级前端工程师，偏好 TypeScript...       │  ← Description
│                                                 │
│ ┌─────────────────────────────────────────┐    │
│ │ ## 详细内容                             │    │  ← Content (展开后)
│ │                                         │    │
│ │ - 技术栈: React, TypeScript, Node.js   │    │
│ │ - 代码风格: 函数式优先，避免类组件     │    │
│ └─────────────────────────────────────────┘    │
│                                                 │
│ [编辑] [删除]                                   │  ← Actions
└─────────────────────────────────────────────────┘
```

#### 样式规范

- **内边距**: `var(--space-sm) var(--space-md)`（12px 16px）
- **选中背景**: `var(--accent-light)`
- **选中边框**: 左侧 `2px solid var(--accent)`
- **标题字体**: `13px`，选中时 `font-weight: 500`
- **元信息字体**: `11px`，颜色 `var(--text-muted)`
- **内容区域**: 展开时显示，背景 `var(--overlay-light)`，圆角 `var(--radius-sm)`

---

### 3. MemoryTypeBadge - 记忆类型标签

显示记忆类型的彩色徽章。

#### Props 接口

```typescript
interface MemoryTypeBadgeProps {
  /** 记忆类型 */
  type: 'user' | 'feedback' | 'project' | 'reference';
  /** 尺寸 */
  size?: 'sm' | 'md';
  /** 自定义类名 */
  className?: string;
}
```

#### 颜色规范

| 类型 | 背景色 | 文字色 | 用途 |
|------|--------|--------|------|
| `user` | `bg-blue-100` / `dark:bg-blue-900/30` | `text-blue-800` / `dark:text-blue-300` | 用户信息 |
| `feedback` | `bg-emerald-100` / `dark:bg-emerald-900/30` | `text-emerald-800` / `dark:text-emerald-300` | 反馈信息 |
| `project` | `bg-purple-100` / `dark:bg-purple-900/30` | `text-purple-800` / `dark:text-purple-300` | 项目信息 |
| `reference` | `bg-amber-100` / `dark:bg-amber-900/30` | `text-amber-800` / `dark:text-amber-300` | 参考资料 |

#### 样式规范

- **圆角**: `rounded-full`
- **内边距**: `px-2 py-0.5`（sm）/ `px-2.5 py-1`（md）
- **字体**: `text-xs`，`font-medium`

---

### 4. MemoryStatusBar - 记忆状态栏

显示 WebSocket 连接状态、记忆数量和最后更新时间。

#### Props 接口

```typescript
interface MemoryStatusBarProps {
  /** 连接状态 */
  status: 'connected' | 'disconnected' | 'connecting';
  /** 记忆数量 */
  count: number;
  /** 最后更新时间 */
  lastUpdatedAt?: string;
  className?: string;
}
```

#### 布局结构

```
┌─────────────────────────────────────────┐
│ ● 已连接 | 12条记忆 | 更新于2分钟前    │
└─────────────────────────────────────────┘
```

#### 状态指示器颜色

| 状态 | 圆点颜色 | 文字 |
|------|----------|------|
| `connected` | `bg-green-500` | 已连接 |
| `connecting` | `bg-yellow-400` + `animate-pulse` | 连接中 |
| `disconnected` | `bg-red-500` | 已断开 |

---

### 5. MemoryEmptyState - 空状态

当没有记忆时显示的提示组件。

#### Props 接口

```typescript
interface MemoryEmptyStateProps {
  /** 点击创建按钮回调 */
  onCreate: () => void;
  className?: string;
}
```

#### 布局结构

```
┌─────────────────────────────────────────┐
│                                         │
│              [BrainIcon]                │
│                                         │
│            暂无记忆记录                 │
│         点击创建第一条记忆              │
│                                         │
│            [ + 新建记忆 ]               │
│                                         │
└─────────────────────────────────────────┘
```

---

## 组件关系图

```
MemoryPanel (容器)
├── Header (标题栏)
│   ├── Title ("记忆库")
│   ├── RefreshButton
│   └── CreateButton
├── MemoryStatusBar (状态栏)
└── MemoryList (列表区)
    ├── MemoryEmptyState (空状态)
    └── MemoryItem[] (记忆项)
        ├── MemoryTypeBadge (类型标签)
        ├── MemoryContent (内容区，可展开)
        └── MemoryActions (操作按钮)
```

## 文件结构

```
src/components/memory/
├── index.ts              # 导出所有组件
├── MemoryPanel.tsx       # 主面板组件
├── MemoryItem.tsx        # 记忆项组件
├── MemoryTypeBadge.tsx   # 类型标签组件
├── MemoryStatusBar.tsx   # 状态栏组件
├── MemoryEmptyState.tsx  # 空状态组件
└── types.ts              # 类型定义
```

## 使用示例

```tsx
import { MemoryPanel } from '@/components/memory';

function ChatPage() {
  const [memories, setMemories] = useState<MemoryItemData[]>([]);
  const [activeId, setActiveId] = useState<string>();
  const [isOpen, setIsOpen] = useState(true);

  const handleRefresh = async () => {
    const data = await fetchMemories();
    setMemories(data);
  };

  return (
    <MemoryPanel
      memories={memories}
      activeMemoryId={activeId}
      connectionStatus="connected"
      lastUpdatedAt={new Date().toISOString()}
      isOpen={isOpen}
      onSelectMemory={(memory) => setActiveId(memory.id)}
      onCreateMemory={() => {/* 打开创建对话框 */}}
      onRefresh={handleRefresh}
      onClose={() => setIsOpen(false)}
    />
  );
}
```

## 响应式行为

- **桌面端 (>768px)**: 固定宽度 280px，始终可见
- **移动端 (<=768px)**: 可滑出的抽屉面板，宽度 80%

## 动画效果

- **展开/收起**: 使用 Framer Motion，`height: auto` 动画，时长 200ms
- **列表加载**: 淡入动画，stagger 50ms
- **状态变化**: 圆点脉冲动画（connecting 状态）

## 主题适配

所有组件支持亮/暗主题，使用 CSS 变量：

```css
--sidebar-bg: #f8f9fa / #1a1a1a
--border: #e5e7eb / #2d2d2d
--text: #111827 / #f3f4f6
--text-light: #4b5563 / #9ca3af
--text-muted: #9ca3af / #6b7280
--accent: #3b82f6
--accent-light: #eff6ff / #1e3a5f
```
