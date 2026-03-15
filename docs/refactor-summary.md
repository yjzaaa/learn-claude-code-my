# 重构完成说明

## 新架构特点

### 后端 (`agents/`)
- `api/main_new.py` - FastAPI 主应用入口
- `models/dialog_types.py` - 数据模型定义
- `hooks/state_managed_agent_bridge.py` - 状态管理型 Bridge
- `agent/s_full.py` - 主 Agent 实现 (SFullAgent)
- `core/s05_skill_loading.py` - Skill 加载系统

### 前端 (`web/src/`)
- `types/dialog.ts` - 类型定义
- `hooks/useWebSocket.ts` - 纯状态接收 hook
- `hooks/useMessageStore.ts` - 消息状态管理
- `components/realtime/EmbeddedDialog.tsx` - 纯渲染组件
- `app/[locale]/agent/client.tsx` - Agent 客户端页面

## 启动方式

### 后端
```bash
# 方式1：使用启动脚本
cd agents
python start_server.py

# 方式2：使用 uvicorn
cd agents
python -m uvicorn api.main_new:app --host 0.0.0.0 --port 8001 --reload
```

### 前端
正常使用 Next.js 启动，在需要的地方导入新的 EmbeddedDialog 组件：
```tsx
import { EmbeddedDialog } from "@/components/realtime/EmbeddedDialog";
```

## 主要改进

1. **后端是唯一直实数据源** - 所有状态在后端维护，推送完整快照
2. **前端纯渲染** - 只接收 snapshot，无状态管理逻辑
3. **简化 WebSocket 事件** - 只有 dialog:snapshot, stream:delta, tool_call:update, status:change
4. **每次发送创建新对话框** - 符合用户要求
5. **历史列表保留** - 左侧栏可切换查看历史对话

## 数据结构

后端推送的 snapshot 格式:
```json
{
  "type": "dialog:snapshot",
  "dialog_id": "uuid",
  "data": {
    "id": "uuid",
    "status": "thinking",
    "messages": [...],
    "streaming_message": {...},
    "metadata": {...}
  }
}
```

## 项目结构

```
agents/
├── api/main_new.py              # FastAPI 主应用
├── agent/s_full.py              # 主 Agent 实现
├── core/s05_skill_loading.py    # Skill 加载系统
├── hooks/state_managed_agent_bridge.py  # 状态管理
├── models/dialog_types.py       # 数据模型
├── websocket/server.py          # WebSocket 服务器
└── start_server.py              # 启动脚本
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `agents/api/main_new.py` | FastAPI 主应用入口 |
| `agents/agent/s_full.py` | 主 Agent 实现 (SFullAgent) |
| `agents/core/s05_skill_loading.py` | Skill 加载系统 |
| `agents/hooks/state_managed_agent_bridge.py` | 状态管理 Bridge |
| `agents/models/dialog_types.py` | 数据模型定义 |
| `web/src/hooks/useWebSocket.ts` | WebSocket Hook |
| `web/src/components/realtime/EmbeddedDialog.tsx` | 渲染组件 |

## 注意事项

1. 后端启动需要使用 `main_new:app` 而不是原来的 `main:app`
2. 前端使用了新的组件 `EmbeddedDialog`，旧的可以保留作为对比
3. WebSocket URL 默认是 `ws://localhost:8001/ws/client-1`
4. 所有状态变更都会推送完整 snapshot，流式内容使用 delta 增量
