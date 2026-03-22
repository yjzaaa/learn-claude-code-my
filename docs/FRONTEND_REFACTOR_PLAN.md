# 前端重构设计计划

基于 openhanako (Hanako Electron App) 的设计风格与交互逻辑

---

## 1. 设计分析

### 1.1 openhanako 设计特点

| 特性 | 描述 |
|------|------|
| **视觉风格** | 深色主题为主，多主题切换（青夜、沉思、深思等） |
| **背景纹理** | paper-texture.png 纸张纹理，400px 平铺 |
| **色彩系统** | CSS 变量驱动，支持动态主题切换 |
| **圆角设计** | sm(6px), md(10px), lg(16px) 三级圆角 |
| **字体系统** | 系统字体栈，支持无衬线/衬线切换 |
| **动效** | ease-out cubic-bezier(0.16, 1, 0.3, 1), 0.3s 时长 |

### 1.2 核心交互模式

```
┌─────────────────────────────────────────────────────────────┐
│  标题栏 (52px, 可拖拽, 透明/毛玻璃效果)                      │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│  Sidebar │  Main Content                                    │
│  (240px) │  - Chat Area (滚动消息列表)                       │
│          │  - Input Area (底部固定, 多行文本, 工具栏)        │
│          │                                                  │
│  Session │                                                  │
│  List    │  - Preview Panel (右侧可收起, 580px)              │
│          │                                                  │
├──────────┴──────────────────────────────────────────────────┤
│  状态栏/底部工具栏 (可选)                                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 InputArea 核心功能

- **斜杠命令**: /diary, /xing 等快捷命令
- **附件管理**: 文件拖拽、粘贴图片、显示附件标签
- **Todo 显示**: 顶部折叠式 Todo 列表
- **Plan Mode**: 操作电脑模式切换
- **Doc Context**: 引用当前文档
- **Thinking Level**: 推理深度选择 (off/auto/xhigh)
- **Model Selector**: 模型切换下拉菜单
- **发送按钮**: 三态切换 (发送/插话/停止)
- **自动调整高度**: textarea 自适应内容高度

---

## 2. 重构范围

### 2.1 当前项目结构

```
web/                        # Next.js 前端
├── src/
│   ├── app/                # App Router
│   ├── components/         # React 组件
│   ├── hooks/              # 自定义 Hooks
│   └── lib/                # 工具函数
├── package.json
└── next.config.js
```

### 2.2 目标架构

```
web/
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── page.tsx               # 主聊天页面
│   │   ├── layout.tsx             # 根布局 (主题/CSS变量)
│   │   └── settings/              # 设置页面
│   │
│   ├── components/                 # 组件
│   │   ├── layout/                # 布局组件
│   │   │   ├── Sidebar.tsx       # 侧边栏
│   │   │   ├── TitleBar.tsx      # 标题栏
│   │   │   └── MainLayout.tsx    # 主布局
│   │   │
│   │   ├── chat/                  # 聊天相关
│   │   │   ├── ChatArea.tsx      # 聊天消息区域
│   │   │   ├── MessageItem.tsx   # 单条消息
│   │   │   ├── InputArea.tsx     # 输入区域 (核心)
│   │   │   ├── SessionList.tsx   # 会话列表
│   │   │   └── TodoDisplay.tsx   # Todo 显示
│   │   │
│   │   ├── input/                 # 输入区域子组件
│   │   │   ├── SlashCommand.tsx  # 斜杠命令菜单
│   │   │   ├── AttachedFiles.tsx # 附件显示
│   │   │   ├── PlanModeBtn.tsx   # Plan Mode 按钮
│   │   │   ├── DocContextBtn.tsx # 文档上下文按钮
│   │   │   ├── ThinkingLevel.tsx # 思考层级选择
│   │   │   ├── ModelSelector.tsx # 模型选择器
│   │   │   └── SendButton.tsx    # 发送按钮 (三态)
│   │   │
│   │   ├── panels/                # 面板
│   │   │   ├── PreviewPanel.tsx  # 预览面板
│   │   │   ├── ArtifactEditor.tsx # 代码编辑器
│   │   │   └── BridgePanel.tsx   # MCP 工具面板
│   │   │
│   │   └── ui/                    # 基础 UI 组件
│   │       ├── Button.tsx
│   │       ├── Dropdown.tsx
│   │       ├── Tooltip.tsx
│   │       └── Toast.tsx
│   │
│   ├── styles/                     # 样式系统
│   │   ├── globals.css            # 全局样式 + CSS 变量
│   │   ├── themes/                # 主题文件
│   │   │   ├── midnight.css      # 青夜主题
│   │   │   ├── warm-paper.css    # 暖纸主题
│   │   │   └── ...               # 其他主题
│   │   └── components/            # 组件样式
│   │
│   ├── hooks/                      # Hooks
│   │   ├── useTheme.ts           # 主题管理
│   │   ├── useWebSocket.ts       # WebSocket 连接
│   │   ├── useStore.ts           # Zustand 状态
│   │   ├── useI18n.ts            # 国际化
│   │   └── useHanaFetch.ts       # API 请求
│   │
│   ├── stores/                     # Zustand Store
│   │   ├── index.ts              # 主 store
│   │   ├── chat-slice.ts         # 聊天状态
│   │   ├── ui-slice.ts           # UI 状态
│   │   └── settings-slice.ts     # 设置状态
│   │
│   ├── lib/                        # 工具
│   │   ├── utils.ts
│   │   ├── format.ts             # 格式化工具
│   │   └── constants.ts          # 常量
│   │
│   └── types/                      # TypeScript 类型
│       └── index.ts
│
├── public/
│   ├── textures/                  # 背景纹理
│   │   └── paper-texture.png
│   └── locales/                   # 国际化文件
│
└── package.json
```

---

## 3. 设计系统 (Design System)

### 3.1 CSS 变量规范

```css
/* styles/globals.css */
:root {
  /* 间距 */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2.5rem;

  /* 圆角 */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  /* 动效 */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration: 0.3s;

  /* 字体 */
  --font-ui: system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-serif: 'Songti SC', 'Georgia', serif;
  --font-mono: 'SF Mono', 'Fira Code', monospace;

  /* 布局 */
  --sidebar-width: 240px;
  --input-area-height: auto;
  --titlebar-height: 52px;
}

/* 默认主题变量 (会被主题文件覆盖) */
:root {
  --bg: #1a1a1a;
  --bg-card: #252525;
  --bg-glass: rgba(26, 26, 26, 0.92);
  
  --accent: #A76F6F;
  --accent-hover: #B88080;
  --accent-light: rgba(167, 111, 111, 0.10);
  
  --text: #E8E8E8;
  --text-light: #A0A0A0;
  --text-muted: #606060;
  
  --border: rgba(255, 255, 255, 0.08);
  --shadow: rgba(0, 0, 0, 0.36);
  
  --overlay-subtle: rgba(255, 255, 255, 0.03);
  --overlay-light: rgba(255, 255, 255, 0.05);
  --overlay-medium: rgba(255, 255, 255, 0.08);
  --overlay-strong: rgba(255, 255, 255, 0.15);
}
```

### 3.2 主题系统

```typescript
// hooks/useTheme.ts
export type Theme = 'midnight' | 'warm-paper' | 'deep-think' | 'high-contrast';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>('midnight');
  
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);
  
  return { theme, setTheme };
}
```

### 3.3 核心组件样式规范

#### InputArea

```css
.input-area {
  position: fixed;
  bottom: 0;
  left: var(--sidebar-width);
  right: 0;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--overlay-light);
  padding: var(--space-md);
}

.input-box {
  width: 100%;
  min-height: 44px;
  max-height: 120px;
  background: var(--overlay-subtle);
  border: 1px solid var(--overlay-light);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  color: var(--text);
  font-size: 15px;
  line-height: 1.7;
  resize: none;
  transition: border-color var(--duration) var(--ease-out);
}

.input-box:focus {
  border-color: var(--accent);
  outline: none;
}
```

---

## 4. 组件详细设计

### 4.1 InputArea 组件架构

```typescript
// components/chat/InputArea.tsx
interface InputAreaProps {
  sessionId: string;
  onSend: (message: string, options?: SendOptions) => void;
  onSteer?: (message: string) => void;
  onStop?: () => void;
}

interface SendOptions {
  images?: ImageAttachment[];
  files?: FileAttachment[];
  docContext?: boolean;
}

export function InputArea({ sessionId, onSend, onSteer, onStop }: InputAreaProps) {
  // 状态管理
  const [inputText, setInputText] = useState('');
  const [planMode, setPlanMode] = useState(false);
  const [thinkingLevel, setThinkingLevel] = useState<ThinkingLevel>('auto');
  const [attachedFiles, setAttachedFiles] = useState<FileAttachment[]>([]);
  const [slashMenuOpen, setSlashMenuOpen] = useState(false);
  
  // Zustand 状态
  const isStreaming = useStore(s => s.isStreaming);
  const sessionTodos = useStore(s => s.sessionTodos);
  const currentModel = useStore(s => s.currentModel);
  
  // 处理函数...
}
```

### 4.2 斜杠命令系统

```typescript
// lib/slash-commands.ts
export interface SlashCommand {
  name: string;
  label: string;
  description: string;
  icon: string; // SVG string
  execute: () => Promise<void>;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    name: 'compact',
    label: '/compact',
    description: '压缩对话上下文',
    icon: '<svg>...</svg>',
    execute: async () => {
      // 调用 compact API
    }
  },
  {
    name: 'diary',
    label: '/diary',
    description: '写今日日记',
    icon: '<svg>...</svg>',
    execute: async () => {
      // 调用 diary API
    }
  }
];
```

### 4.3 消息组件

```typescript
// components/chat/MessageItem.tsx
interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
  onArtifactClick?: (artifact: Artifact) => void;
}

export function MessageItem({ message, isStreaming, onArtifactClick }: MessageItemProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  
  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar">
        {isUser ? <UserAvatar /> : <AgentAvatar />}
      </div>
      <div className="message-content">
        <MessageHeader role={message.role} timestamp={message.timestamp} />
        <MessageBody content={message.content} />
        {message.artifacts?.map(artifact => (
          <ArtifactCard 
            key={artifact.id} 
            artifact={artifact}
            onClick={() => onArtifactClick?.(artifact)}
          />
        ))}
      </div>
    </div>
  );
}
```

---

## 5. 状态管理 (Zustand)

### 5.1 Store 结构

```typescript
// stores/index.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface AppState 
  extends ChatSlice,
    UISlice,
    SettingsSlice,
    SessionSlice {}

export const useStore = create<AppState>()(
  devtools(
    persist(
      (...args) => ({
        ...createChatSlice(...args),
        ...createUISlice(...args),
        ...createSettingsSlice(...args),
        ...createSessionSlice(...args),
      }),
      {
        name: 'hana-store',
        partialize: (state) => ({
          // 只持久化设置和会话列表
          settings: state.settings,
          sessions: state.sessions,
        }),
      }
    )
  )
);
```

### 5.2 Chat Slice

```typescript
// stores/chat-slice.ts
export interface ChatSlice {
  // 状态
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  attachedFiles: FileAttachment[];
  sessionTodos: TodoItem[];
  
  // Actions
  addMessage: (message: Message) => void;
  updateStreamingContent: (content: string) => void;
  setIsStreaming: (value: boolean) => void;
  addAttachedFile: (file: FileAttachment) => void;
  removeAttachedFile: (index: number) => void;
  clearAttachedFiles: () => void;
  updateTodos: (todos: TodoItem[]) => void;
}

export const createChatSlice: StoreSlice<ChatSlice> = (set, get) => ({
  messages: [],
  isStreaming: false,
  streamingContent: '',
  attachedFiles: [],
  sessionTodos: [],
  
  addMessage: (message) => 
    set((state) => ({ messages: [...state.messages, message] })),
  
  updateStreamingContent: (content) => 
    set({ streamingContent: content }),
  
  setIsStreaming: (value) => 
    set({ isStreaming: value }),
  
  addAttachedFile: (file) => 
    set((state) => ({ attachedFiles: [...state.attachedFiles, file] })),
  
  removeAttachedFile: (index) => 
    set((state) => ({ 
      attachedFiles: state.attachedFiles.filter((_, i) => i !== index) 
    })),
  
  clearAttachedFiles: () => 
    set({ attachedFiles: [] }),
  
  updateTodos: (todos) => 
    set({ sessionTodos: todos }),
});
```

---

## 6. WebSocket 通信

### 6.1 Hook 设计

```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '@/stores';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  
  const setConnected = useStore(s => s.setConnected);
  const addMessage = useStore(s => s.addMessage);
  const updateStreamingContent = useStore(s => s.updateStreamingContent);
  
  const connect = useCallback(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
      setConnected(true);
      console.log('[WS] Connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };
    
    ws.onclose = () => {
      setConnected(false);
      // 重连逻辑
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };
    
    wsRef.current = ws;
  }, []);
  
  const sendMessage = useCallback((type: string, payload: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...payload }));
    }
  }, []);
  
  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connect]);
  
  return { sendMessage };
}
```

---

## 7. 国际化 (i18n)

### 7.1 实现方案

```typescript
// hooks/useI18n.ts
import { useCallback } from 'react';

const translations = {
  'zh-CN': {
    'input.placeholder': '发消息...',
    'input.planMode': '操作电脑',
    'input.docContext': '看着文档说',
    'chat.send': '发送',
    'chat.steer': '插话',
    'chat.stop': '停止',
    'slash.compact': '压缩上下文',
    'slash.diary': '写今日日记',
  },
  'en': {
    // ...
  }
};

export function useI18n() {
  const t = useCallback((key: string) => {
    const lang = localStorage.getItem('lang') || 'zh-CN';
    return translations[lang]?.[key] || key;
  }, []);
  
  return { t };
}
```

---

## 8. 实现路线图

### Phase 1: 基础架构 (Week 1)

- [ ] 创建项目结构
- [ ] 配置 Tailwind CSS + CSS 变量系统
- [ ] 实现主题切换机制
- [ ] 创建 Zustand Store 基础
- [ ] 设置 WebSocket 连接

### Phase 2: 核心组件 (Week 2)

- [ ] MainLayout (Sidebar + ChatArea)
- [ ] InputArea 基础结构
  - [ ] textarea + 自动高度
  - [ ] 附件管理
  - [ ] 发送按钮 (三态)
- [ ] MessageItem 基础显示
- [ ] SessionList

### Phase 3: InputArea 高级功能 (Week 3)

- [ ] 斜杠命令菜单
- [ ] Todo Display
- [ ] Plan Mode 按钮
- [ ] Doc Context 按钮
- [ ] Thinking Level 选择器
- [ ] Model Selector
- [ ] 粘贴图片处理

### Phase 4: 聊天功能完善 (Week 4)

- [ ] 消息流式显示
- [ ] Artifact 卡片
- [ ] 代码高亮
- [ ] 工具调用显示
- [ ] 消息操作 (复制、重新生成)

### Phase 5: 面板与设置 (Week 5)

- [ ] Preview Panel
- [ ] Artifact Editor (CodeMirror)
- [ ] Settings 页面
- [ ] 主题选择
- [ ] 快捷键设置

### Phase 6: 优化与测试 (Week 6)

- [ ] 性能优化 (虚拟列表)
- [ ] 响应式适配
- [ ] 无障碍支持
- [ ] E2E 测试

---

## 9. 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Next.js 15 + React 19 |
| 语言 | TypeScript |
| 样式 | Tailwind CSS + CSS 变量 |
| 状态 | Zustand |
| 通信 | WebSocket + SWR |
| 编辑器 | CodeMirror 6 |
| 图标 | Lucide React |
| 动画 | Framer Motion |

---

## 10. 设计原则

1. **一致性强**: 严格遵循 CSS 变量系统，确保主题切换无缝
2. **响应式交互**: 0.3s ease-out 动效，即时反馈
3. **键盘优先**: 支持全键盘操作，快捷键友好
4. **视觉层次**: 通过 overlay 层级 (subtle/light/medium/strong) 构建深度
5. **内容优先**: 界面元素不抢夺内容焦点，留白得当

---

*文档版本: 1.0*
*基于 openhanako 设计系统*
