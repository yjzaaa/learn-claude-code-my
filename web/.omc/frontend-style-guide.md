# 前端架构和风格指南

## 1. 组件文件组织规范

### 1.1 目录结构
```
src/
├── components/           # 组件目录
│   ├── chat/            # 聊天相关组件
│   │   ├── input/       # 输入区域子组件
│   │   │   ├── InputArea.tsx
│   │   │   ├── ModelSelector.tsx
│   │   │   ├── SlashCommandMenu.tsx
│   │   │   ├── FileAttachment.tsx
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   ├── ChatArea.tsx
│   │   ├── MessageItem.tsx
│   │   ├── SessionSidebar.tsx
│   │   └── index.ts
│   ├── ui/              # 基础UI组件（原子组件）
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   └── tabs.tsx
│   ├── layout/          # 布局组件
│   ├── code/            # 代码展示组件
│   └── ...
├── hooks/               # 自定义Hooks
│   ├── index.ts         # 统一导出
│   ├── useAgentApi.ts
│   ├── useDialog.ts
│   └── websocket/       # WebSocket相关hooks
├── stores/              # 状态管理（Zustand）
│   ├── ui.ts            # UI状态
│   ├── dialog-store.ts  # 对话状态
│   ├── message-store.ts # 消息状态
│   └── ...
├── styles/              # 全局样式
│   ├── globals.css
│   └── themes/          # 主题样式
│       ├── index.css
│       ├── midnight.css
│       └── ...
└── types/               # TypeScript类型定义
```

### 1.2 组件命名规范
- **文件命名**: PascalCase (如 `ChatArea.tsx`, `MessageItem.tsx`)
- **目录命名**: kebab-case (如 `slash-command-menu/`)
- **Hook命名**: use + PascalCase (如 `useAgentApi`, `useWebSocket`)
- **Store命名**: use + StoreName + Store (如 `useDialogStore`, `useUIStore`)

### 1.3 组件导出模式
```typescript
// index.ts - 统一导出
export { ChatArea } from './ChatArea';
export { MessageItem } from './MessageItem';
export type { ChatAreaProps } from './ChatArea';

// 组件文件 - 命名导出
export function ChatArea({ dialogId }: ChatAreaProps) {
  // ...
}

// 复杂组件拆分子组件
export interface InputAreaProps {
  dialogId: string;
  isStreaming?: boolean;
  onSend: (content: string, options: SendOptions) => Promise<void>;
  onStop?: () => void;
}

export function InputArea({ ... }: InputAreaProps) {
  // 使用内部子组件 ToolBtn, PopupMenu 等
}
```

## 2. 样式编写模式

### 2.1 CSS变量主题系统
所有样式基于CSS变量，支持7种主题切换：

```css
/* styles/themes/midnight.css */
[data-theme="midnight"] {
  /* 背景色 */
  --bg: #0f1419;
  --bg-card: #141b23;
  --bg-glass: rgba(15, 20, 25, 0.85);
  --sidebar-bg: #0d1216;

  /* 文字色 */
  --text: #e6e6e6;
  --text-light: #a0a0a0;
  --text-muted: #6b7280;

  /* 强调色 */
  --accent: #5eead4;
  --accent-light: rgba(94, 234, 212, 0.12);
  --accent-hover: #4dd9c1;

  /* 边框和阴影 */
  --border: rgba(94, 234, 212, 0.12);
  --shadow: rgba(0, 0, 0, 0.4);

  /* 叠加层 */
  --overlay-subtle: rgba(94, 234, 212, 0.03);
  --overlay-light: rgba(94, 234, 212, 0.08);
  --overlay-medium: rgba(94, 234, 212, 0.15);

  /* 功能色 */
  --danger: #ef4444;
  --success: #22c55e;
  --warning: #f59e0b;

  /* 尺寸 */
  --sidebar-width: 260px;
  --titlebar-height: 44px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 24px;

  /* 圆角 */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  /* 动画 */
  --duration: 200ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);

  /* 字体 */
  --font-ui: system-ui, -apple-system, sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;
}
```

### 2.2 内联样式模式（主要方式）
项目主要使用内联样式配合CSS变量：

```tsx
<div
  style={{
    background: "var(--bg-glass)",
    backdropFilter: "blur(20px)",
    borderTop: "1px solid var(--overlay-light)",
    padding: "var(--space-md)",
    borderRadius: "var(--radius-md)",
    transition: "border-color var(--duration) var(--ease-out)",
  }}
>
```

### 2.3 Tailwind CSS（UI组件）
基础UI组件使用Tailwind：

```tsx
// components/ui/button.tsx
export function Button({ className, variant = "default", size = "md", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT_STYLES[variant],
        SIZE_STYLES[size],
        className,
      )}
      {...props}
    />
  );
}
```

### 2.4 条件样式处理
```tsx
// 使用对象映射
const VARIANT_STYLES: Record<ButtonVariant, string> = {
  default: "bg-zinc-900 text-white hover:bg-zinc-800",
  outline: "border border-zinc-300 bg-white text-zinc-900",
  ghost: "bg-transparent text-zinc-900 hover:bg-zinc-100",
};

// 动态内联样式
<button
  style={{
    background: isActive ? "var(--accent-light)" : "transparent",
    border: active ? "1px solid var(--accent)" : "1px solid var(--overlay-light)",
    color: active ? "var(--accent)" : "var(--text-light)",
  }}
/>
```

## 3. 颜色变量参考表

### 3.1 主题列表
| 主题ID | 名称 | 描述 |
|--------|------|------|
| `midnight` | 青夜 | 深青蓝 + 暖玫瑰（默认） |
| `warm-paper` | 暖纸 | 温暖的纸张质感 |
| `forest` | 森绿 | 森林绿色调 |
| `lavender` | 薰衣草 | 淡紫色调 |
| `ocean` | 深海 | 深海蓝色调 |
| `charcoal` | 墨炭 | 极简深灰 |
| `sakura` | 樱粉 | 樱花粉色 |

### 3.2 核心CSS变量

#### 背景色
| 变量名 | 用途 |
|--------|------|
| `--bg` | 页面主背景 |
| `--bg-card` | 卡片背景 |
| `--bg-glass` | 毛玻璃背景 |
| `--sidebar-bg` | 侧边栏背景 |

#### 文字色
| 变量名 | 用途 |
|--------|------|
| `--text` | 主要文字 |
| `--text-light` | 次要文字 |
| `--text-muted` | 辅助/禁用文字 |

#### 强调色
| 变量名 | 用途 |
|--------|------|
| `--accent` | 主强调色（按钮、链接） |
| `--accent-light` | 浅强调色（选中背景） |
| `--accent-hover` | 悬停强调色 |

#### 叠加层
| 变量名 | 用途 |
|--------|------|
| `--overlay-subtle` | 微弱叠加 |
| `--overlay-light` | 轻叠加（边框） |
| `--overlay-medium` | 中等叠加（悬停） |

#### 功能色
| 变量名 | 用途 |
|--------|------|
| `--danger` | 错误/危险操作 |
| `--success` | 成功状态 |
| `--warning` | 警告状态 |

## 4. 组件Props模式

### 4.1 Props接口定义
```typescript
// 基础Props
export interface ChatAreaProps {
  dialogId: string;
}

// 带可选属性的Props
export interface InputAreaProps {
  dialogId: string;
  isStreaming?: boolean;
  onSend: (content: string, options: SendOptions) => Promise<void>;
  onStop?: () => void;
}

// 联合类型
export type ButtonVariant = "default" | "outline" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

// 复杂类型
export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  status: MessageStatus;
  metadata?: {
    toolName?: string;
    thinkingLevel?: 'none' | 'brief' | 'full';
  };
}
```

### 4.2 子组件Props传递
```typescript
// 内部子组件定义
function ToolBtn({
  children,
  active = false,
  onClick,
  title,
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        padding: "5px 9px",
        borderRadius: "var(--radius-sm)",
        border: active ? "1px solid var(--accent)" : "1px solid var(--overlay-light)",
        background: active ? "var(--accent-light)" : "transparent",
        color: active ? "var(--accent)" : "var(--text-light)",
        cursor: "pointer",
        fontSize: "12px",
        transition: "all var(--duration) var(--ease-out)",
      }}
    >
      {children}
    </button>
  );
}
```

### 4.3 事件处理模式
```typescript
const handleSubmit = useCallback(async () => {
  if (isStreaming) {
    onStop?.();
    return;
  }
  const content = inputText.trim();
  if (!content || isSending) return;

  setIsSending(true);
  try {
    await onSend(content, { thinkingLevel, model, planMode });
    setInputText("");
    setAttachedFiles([]);
  } finally {
    setIsSending(false);
  }
}, [isStreaming, inputText, isSending, onSend, onStop, thinkingLevel, model, planMode]);

// 键盘事件
const handleKeyDown = useCallback(
  (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  },
  [handleSubmit]
);
```

## 5. 状态管理模式

### 5.1 Zustand Store结构
```typescript
// stores/ui.ts - UI状态
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'midnight' | 'warm-paper' | 'forest' | ...;
export type FontMode = 'serif' | 'sans';

interface UIState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  fontMode: FontMode;
  setFontMode: (mode: FontMode) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'midnight',
      setTheme: (theme) => set({ theme }),
      // ...
    }),
    {
      name: 'hana-ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        fontMode: state.fontMode,
        // 只持久化部分状态
      }),
    }
  )
);
```

### 5.2 Immer中间件使用
```typescript
// stores/dialog-store.ts - 使用immer处理复杂状态
import { immer } from 'zustand/middleware/immer';

export const useDialogStore = create<DialogState>()(
  immer((set) => ({
    dialogs: [],
    currentDialogId: null,

    addDialog: (dialog) =>
      set((state) => {
        state.dialogs.unshift(dialog);  // 直接修改，immer处理不可变性
        state.currentDialogId = dialog.id;
      }),

    updateDialog: (id, updates) =>
      set((state) => {
        const dialog = state.dialogs.find((d) => d.id === id);
        if (dialog) {
          Object.assign(dialog, updates);
        }
      }),
  }))
);
```

### 5.3 Store选择器
```typescript
// 基础选择
const theme = useUIStore((s) => s.theme);
const setTheme = useUIStore((s) => s.setTheme);

// 派生状态
export const selectCurrentDialog = (state: DialogState): Dialog | null => {
  if (!state.currentDialogId) return null;
  return state.dialogs.find((d) => d.id === state.currentDialogId) ?? null;
};

// 组件中使用
const currentDialog = useDialogStore(selectCurrentDialog);
```

## 6. 响应式设计模式

### 6.1 布局断点
项目使用CSS变量控制布局尺寸：

```css
:root {
  --sidebar-width: 260px;
  --titlebar-height: 44px;
  --space-md: 12px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  :root {
    --sidebar-width: 0px;  /* 移动端隐藏侧边栏 */
    --space-md: 8px;
  }
}
```

### 6.2 弹性布局模式
```tsx
// 主布局结构
<div style={{
  display: "flex",
  height: "100vh",
  overflow: "hidden",
}}>
  {/* 侧边栏 */}
  <div style={{
    width: "var(--sidebar-width)",
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
  }}>

  {/* 主内容区 */}
  <div style={{
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    minWidth: 0,  // 关键：防止flex子项溢出
  }}>
```

### 6.3 自适应组件
```tsx
// 文本截断
<div style={{
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
  maxWidth: "100%",
}}>

// 自动调整高度的textarea
useEffect(() => {
  const ta = textareaRef.current;
  if (!ta) return;
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
}, [inputText]);
```

## 7. 最佳实践总结

1. **组件拆分**: 复杂组件拆分为子组件，如 `InputArea` 拆分为 `ModelSelector`, `SlashCommandMenu`, `FileAttachment`

2. **样式优先使用CSS变量**: 便于主题切换和统一维护

3. **Hooks职责分离**: 
   - `useAgentApi` - API调用
   - `useDialog` - 对话管理
   - `useWebSocket` - WebSocket连接

4. **状态按领域划分**:
   - `ui.ts` - 界面状态
   - `dialog-store.ts` - 对话领域
   - `message-store.ts` - 消息领域

5. **类型定义集中管理**: 在 `types/` 目录或组件内定义，通过 `index.ts` 统一导出

6. **动画使用CSS变量**: `--duration` 和 `--ease-out` 确保动画一致性
