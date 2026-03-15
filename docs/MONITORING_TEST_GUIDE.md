# 监控系统测试指南

## 快速验证步骤

### 1. 后端启动测试

```bash
# 在项目根目录
.venv\Scripts\python.exe -c "
import asyncio
from agents.monitoring import event_bus
from agents.monitoring.bridge import CompositeMonitoringBridge

async def test():
    await event_bus.start_processing()
    print('EventBus started')

    agent = CompositeMonitoringBridge(
        dialog_id='test',
        agent_name='TestAgent',
        event_bus=event_bus
    )
    print(f'Agent created: {agent.get_bridge_id()}')

    # Emit events
    agent.on_before_run([])
    await asyncio.sleep(0.1)

    print('Events emitted successfully')
    await event_bus.stop_processing()

asyncio.run(test())
"
```

### 2. 完整后端启动

```bash
# 方法1: 使用 main_new (推荐)
.venv\Scripts\python.exe -m agents.api.main_new

# 方法2: 使用 uvicorn
uvicorn agents.api.main_new:app --host 0.0.0.0 --port 8001 --reload
```

启动后应该看到：
```
EventBus started
WebSocket handler registered
Monitoring system initialized
```

### 3. 前端启动

```bash
cd web
npm install    # 如果还没安装依赖
npm run dev
```

启动后访问：
- 主应用: `http://localhost:3000`
- 监控页面: `http://localhost:3000/monitoring`

### 4. 端到端测试

1. **打开监控页面**: `http://localhost:3000/monitoring`
   - 应该看到监控仪表板（5个标签页）

2. **创建对话**:
   - 在主界面点击"新建对话"
   - 输入消息并发送

3. **观察监控页面**:
   - 应该实时显示 Agent 状态变化
   - 时间线应该显示事件流
   - 层级图应该显示 Agent 调用树

## 常见问题

### 问题1: WebSocket 连接失败

**症状**: 前端控制台显示 WebSocket 错误

**解决**:
1. 确认后端已启动 (`http://localhost:8001`)
2. 检查 CORS 配置
3. 查看后端日志是否有连接日志

### 问题2: 事件不显示

**症状**: 监控页面空白

**解决**:
1. 检查浏览器控制台错误
2. 确认后端有事件产生（查看后端日志）
3. 检查 WebSocket 消息是否到达（浏览器 Network 面板）

### 问题3: 组件报错

**症状**: React 错误

**解决**:
```bash
cd web
npm install
npm run build  # 查看编译错误
```

## 验证清单

- [ ] 后端启动无错误
- [ ] EventBus 初始化成功
- [ ] WebSocket 服务器启动
- [ ] 前端编译无错误
- [ ] 监控页面可访问
- [ ] WebSocket 连接成功
- [ ] 创建对话后事件显示
- [ ] 时间线有事件流
- [ ] 层级图显示 Agent 树

## 调试技巧

### 查看后端事件

在后端代码中添加：
```python
from agents.monitoring import event_bus

class DebugObserver:
    async def on_event(self, event):
        print(f"[DEBUG] {event.type}: {event.payload}")

event_bus.subscribe(DebugObserver())
```

### 查看 WebSocket 消息

浏览器开发者工具：
1. 打开 Network 面板
2. 选择 WS (WebSocket) 过滤器
3. 查看消息列表

### 查看前端状态

浏览器控制台：
```javascript
// 查看当前状态
$monitoringStore.getState()
```
