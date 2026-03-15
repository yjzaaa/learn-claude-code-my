# Agent 监控系统测试问题集

## 测试环境准备

1. **启动后端服务**
   ```bash
   cd agents/api
   python -m agents.api.main_new
   ```

2. **启动前端**
   ```bash
   cd web
   npm run dev
   ```

3. **打开浏览器**
   - 访问 http://localhost:3000
   - 打开开发者工具 (F12) → Console 面板
   - 切换到 Monitor 标签页

---

## 第一级：基础生命周期测试

### 测试 1.1：Agent 启动事件
**目的**: 验证 AGENT_STARTED 事件是否正确发送和显示

**步骤**:
1. 刷新浏览器页面
2. 在 Chat 标签页输入："你好"
3. 立即切换到 Monitor 标签页

**预期结果**:
- [ ] 事件时间线显示 "Agent 启动" 事件
- [ ] Agent 名称为 "TeamLeadAgent"
- [ ] Agent 层级显示根节点
- [ ] 状态显示为 "INITIALIZING"

**检查点**:
```
Console 应显示:
[WebSocketEventAdapter] Received: monitor:agent:started {...}
[MonitoringStore] Handling event: agent:started {...}
```

---

### 测试 1.2：消息流事件
**目的**: 验证 MESSAGE_DELTA 事件流

**步骤**:
1. 在 Chat 标签页输入："请写一个简短的问候语"
2. 观察 Monitor 标签页的事件流

**预期结果**:
- [ ] 显示多个 "消息增量" 事件
- [ ] 每个事件显示 Token 增量
- [ ] 流式内容区域显示累积的文本

---

### 测试 1.3：Agent 完成事件
**目的**: 验证 AGENT_STOPPED 事件

**步骤**:
1. 等待 Agent 完成响应
2. 查看 Monitor 标签页

**预期结果**:
- [ ] 显示 "Agent 停止" 事件
- [ ] 显示总运行时间
- [ ] 状态变为 "COMPLETED"

---

## 第二级：工具调用测试

### 测试 2.1：单次工具调用
**目的**: 验证工具调用事件序列

**步骤**:
1. 在 Chat 标签页输入："查看当前目录的文件"

**预期结果**:
- [ ] 显示 "工具调用开始" 事件
- [ ] 工具名称为 "list_directory" 或类似
- [ ] 显示 "工具结果" 事件
- [ ] 指标面板显示工具调用次数 = 1

**事件序列检查**:
```
1. tool_call:start
2. tool:result
```

---

### 测试 2.2：多次工具调用
**目的**: 验证多次工具调用的监控

**步骤**:
1. 在 Chat 标签页输入："先查看当前目录，然后读取 README.md 文件"

**预期结果**:
- [ ] 显示 2 次 "工具调用开始" 事件
- [ ] 显示 2 次 "工具结果" 事件
- [ ] 指标面板显示工具调用次数 = 2
- [ ] 事件时间线按顺序显示

---

### 测试 2.3：工具调用错误
**目的**: 验证工具调用错误处理

**步骤**:
1. 在 Chat 标签页输入："读取一个不存在的文件 /path/to/nonexistent.txt"

**预期结果**:
- [ ] 显示 "工具调用开始" 事件
- [ ] 显示 "工具调用错误" 或包含错误信息的 "工具结果"
- [ ] 错误信息在 Payload 中可见

---

## 第三级：子智能体测试

### 测试 3.1：子智能体创建
**目的**: 验证 SUBAGENT_SPAWNED 事件

**步骤**:
1. 在 Chat 标签页输入一个复杂任务："分析一下这个项目的主要功能，写一个摘要"

**预期结果**:
- [ ] 显示 "子智能体创建" 事件
- [ ] Agent 层级显示子节点
- [ ] 子节点类型为 "subagent"

---

### 测试 3.2：子智能体生命周期
**目的**: 验证子智能体的完整生命周期

**步骤**:
1. 输入明确需要分解的复杂任务："请使用子智能体帮我分析这个项目：先让一个 Explore 类型的子智能体找出所有配置文件，然后让一个 Code 类型的子智能体分析主要的代码入口点"
2. 等待完成

**备选测试问题**（如果上面的没有触发子智能体）：
> "我需要你分解这个任务：使用 subagent 工具，创建一个名为 'FileExplorer' 的子智能体，让它列出当前目录下所有的 Python 文件"

**预期结果**:
- [ ] 显示 "子智能体启动" 事件
- [ ] 子智能体状态变化：INITIALIZING → THINKING → COMPLETED
- [ ] 显示 "子智能体完成" 事件
- [ ] 指标面板显示子智能体调用次数

**调试技巧**：
如果子智能体事件没有显示，在浏览器 Console 中检查：
```javascript
// 查看收到的所有事件类型
console.log('All received events:',
  performance.getEntriesByType('resource')
    .filter(r => r.name.includes('ws'))
);
```

---

### 测试 3.3：多级子智能体
**目的**: 验证多级嵌套子智能体

**步骤**:
1. 输入明确需要多级分解的复杂任务：
   > "我需要你完成一个复杂的多步骤分析任务，必须按照以下方式使用 subagent 工具：
   >
   > 第一步：创建一个名为 'ProjectAnalyzer' 的子智能体（类型：Explore），让它分析项目结构并找出所有主要组件。
   >
   > 第二步：基于 ProjectAnalyzer 的结果，创建三个子智能体：
   > - 'FrontendAnalyzer'（类型：Code）分析前端代码
   > - 'BackendAnalyzer'（类型：Code）分析后端代码
   > - 'ConfigAnalyzer'（类型：Explore）分析配置文件
   >
   > 确保每个子智能体都有独立的名称和明确的任务。"

**预期结果**:
- [ ] Agent 层级显示多级树形结构（至少 2 级）
- [ ] 可以展开/收起子节点
- [ ] 每个子智能体有独立的名称和状态
- [ ] 显示所有子智能体的生命周期事件（SUBAGENT_STARTED, SUBAGENT_COMPLETED）

**替代测试方案**（如果上面的没有触发多级）：
使用以下强制触发脚本在后端运行：
```bash
.venv\Scripts\python.exe -c "
import asyncio
from agents.monitoring import event_bus
from agents.monitoring.domain import MonitoringEvent, EventType, EventPriority
from uuid import uuid4

async def emit_nested_subagent_events():
    await event_bus.start_processing()
    dialog_id = 'test-dialog'

    # 主 Agent 启动
    await event_bus.emit(MonitoringEvent(
        type=EventType.AGENT_STARTED,
        dialog_id=dialog_id,
        source='SFullAgent',
        context_id=uuid4(),
        priority=EventPriority.HIGH,
        payload={'agent_name': 'SFullAgent', 'bridge_id': 'main-bridge'}
    ))
    await asyncio.sleep(0.5)

    # 第一层子智能体
    await event_bus.emit(MonitoringEvent(
        type=EventType.SUBAGENT_STARTED,
        dialog_id=dialog_id,
        source='Subagent:Explore:ProjectAnalyzer',
        context_id=uuid4(),
        priority=EventPriority.HIGH,
        payload={'subagent_name': 'ProjectAnalyzer', 'subagent_type': 'Explore'}
    ))
    await asyncio.sleep(0.5)

    # 第二层子智能体（嵌套）
    for name in ['FrontendAnalyzer', 'BackendAnalyzer', 'ConfigAnalyzer']:
        await event_bus.emit(MonitoringEvent(
            type=EventType.SUBAGENT_STARTED,
            dialog_id=dialog_id,
            source=f'Subagent:Code:{name}',
            context_id=uuid4(),
            priority=EventPriority.HIGH,
            payload={'subagent_name': name, 'subagent_type': 'Code', 'parent': 'ProjectAnalyzer'}
        ))
        await asyncio.sleep(0.3)

        await event_bus.emit(MonitoringEvent(
            type=EventType.SUBAGENT_COMPLETED,
            dialog_id=dialog_id,
            source=f'Subagent:Code:{name}',
            context_id=uuid4(),
            priority=EventPriority.HIGH,
            payload={'subagent_name': name, 'subagent_type': 'Code', 'result_preview': f'{name} 完成'}
        ))
        await asyncio.sleep(0.3)

    # 第一层完成
    await event_bus.emit(MonitoringEvent(
        type=EventType.SUBAGENT_COMPLETED,
        dialog_id=dialog_id,
        source='Subagent:Explore:ProjectAnalyzer',
        context_id=uuid4(),
        priority=EventPriority.HIGH,
        payload={'subagent_name': 'ProjectAnalyzer', 'subagent_type': 'Explore'}
    ))

    await event_bus.stop_processing()
    print('✓ Nested subagent events emitted!')

asyncio.run(emit_nested_subagent_events())
"
```

---

## 第四级：Token 使用测试

### 测试 4.1：Token 统计
**目的**: 验证 TOKEN_USAGE 事件

**步骤**:
1. 输入："请详细解释一下 Python 的 asyncio 工作原理，包括事件循环、协程和任务"
2. 等待完成

**预期结果**:
- [ ] 显示 "Token 使用" 事件
- [ ] 指标面板显示 Input/Output Token 数
- [ ] Token 使用分布图表可见
- [ ] 总 Token 数 > 0

---

### 测试 4.2：Token 累积
**目的**: 验证多次对话的 Token 累积

**步骤**:
1. 连续发送 3-5 条消息
2. 观察指标面板

**预期结果**:
- [ ] Token 数随着对话累积
- [ ] 平均 Token/调用计算正确
- [ ] Input/Output 比例显示正常

---

## 第五级：状态机测试

### 测试 5.1：状态转换
**目的**: 验证状态转换事件

**步骤**:
1. 输入需要工具调用的任务："运行一个 bash 命令查看系统信息"
2. 快速观察状态面板

**预期结果**:
- [ ] 状态机可视化显示状态变化
- [ ] 状态序列：IDLE → INITIALIZING → THINKING → TOOL_CALLING → WAITING_FOR_TOOL → THINKING → COMPLETED
- [ ] 当前状态高亮显示

---

### 测试 5.2：状态持续时间
**目的**: 验证状态持续时间统计

**步骤**:
1. 执行一个长时间运行的任务
2. 查看状态机面板

**预期结果**:
- [ ] 每个状态显示持续时间
- [ ] THINKING 状态显示思考时间
- [ ] TOOL_CALLING 状态显示等待时间

---

## 第六级：错误处理测试

### 测试 6.1：Agent 错误
**目的**: 验证 AGENT_ERROR 事件

**步骤**:
1. 尝试触发错误（如发送超长文本）

**预期结果**:
- [ ] 显示 "Agent 错误" 事件
- [ ] 错误类型和消息在 Payload 中
- [ ] 状态变为 "ERROR"

---

### 测试 6.2：WebSocket 重连
**目的**: 验证连接断开后的重连

**步骤**:
1. 断开网络连接几秒钟
2. 恢复网络连接
3. 发送新消息

**预期结果**:
- [ ] Console 显示重连日志
- [ ] 自动重新连接成功
- [ ] 新事件正常接收

---

## 第七级：性能测试

### 测试 7.1：高频事件处理
**目的**: 验证系统在高频事件下的表现

**步骤**:
1. 输入："快速列出 20 个常见的 Python 内置函数"
2. 观察事件流的流畅度

**预期结果**:
- [ ] 事件时间线实时更新，不卡顿
- [ ] 流式内容平滑显示
- [ ] 浏览器不卡顿

---

### 测试 7.2：大数据量测试
**目的**: 验证大数据量下的稳定性

**步骤**:
1. 输入："读取一个较大的文件内容"（如果有大文件）
2. 或请求生成大量内容

**预期结果**:
- [ ] 大 payload 正确显示
- [ ] 可以展开/收起查看详情
- [ ] 内存使用稳定

---

## 第八级：多标签页测试

### 测试 8.1：Chat 和 Monitor 同时工作
**目的**: 验证多标签页同步

**步骤**:
1. 在 Chat 标签页持续对话
2. 同时观察 Monitor 标签页的事件流

**预期结果**:
- [ ] 事件实时显示在 Monitor
- [ ] 两个标签页数据一致
- [ ] 切换标签页后状态保持

---

## 测试通过标准

| 级别 | 测试项 | 通过标准 |
|------|--------|----------|
| 第一级 | 基础生命周期 | 3/3 通过 |
| 第二级 | 工具调用 | 3/3 通过 |
| 第三级 | 子智能体 | 3/3 通过 |
| 第四级 | Token 使用 | 2/2 通过 |
| 第五级 | 状态机 | 2/2 通过 |
| 第六级 | 错误处理 | 2/2 通过 |
| 第七级 | 性能 | 2/2 通过 |
| 第八级 | 多标签页 | 1/1 通过 |

**总通过率**: 18/18 (100%)

---

## 问题排查指南

### 如果事件不显示

1. **检查 WebSocket 连接**
   ```javascript
   // 在浏览器 Console 中执行
   console.log(WebSocket.readyState); // 应为 1 (OPEN)
   ```

2. **检查后端日志**
   ```bash
   # 查看是否有事件发送日志
   tail -f agents/api/logs/app.log
   ```

3. **检查过滤器设置**
   - 确保 Monitor 页面的过滤器没有排除某些事件类型

### 如果 Agent 名称显示不正确

1. 检查 Payload 字段名是否匹配（蛇形 vs 驼峰）
2. 查看 Console 中的调试日志
3. 检查 `fromWebSocket` 转换逻辑

### 如果性能问题

1. 检查事件队列长度
2. 检查是否有内存泄漏
3. 检查订阅者是否正确清理

### 如果子智能体事件不显示

**原因分析**：子智能体的创建取决于 LLM 是否决定调用 `subagent` 工具。如果 LLM 认为任务不需要分解，就不会创建子智能体。

**解决方案**：

1. **使用明确触发子智能体的提示词**：
   ```
   请使用 subagent 工具，创建一个名为 "CodeAnalyzer" 的子智能体，
   类型为 "Code"，任务为 "分析 src 目录下的主要代码文件"
   ```

2. **强制触发脚本**（在后端运行，不依赖 LLM 决策）：
   ```bash
   # 在项目根目录运行
   .venv\Scripts\python.exe -c "
   import asyncio
   from agents.monitoring import event_bus
   from agents.monitoring.domain import MonitoringEvent, EventType, EventPriority
   from uuid import uuid4

   async def emit_subagent_events():
       await event_bus.start_processing()
       dialog_id = 'test-dialog'

       # 发送子智能体启动事件
       event = MonitoringEvent(
           type=EventType.SUBAGENT_STARTED,
           dialog_id=dialog_id,
           source='Subagent:Explore:FileFinder',
           context_id=uuid4(),
           priority=EventPriority.HIGH,
           payload={
               'subagent_name': 'FileFinder',
               'subagent_type': 'Explore',
               'task_preview': '查找所有Python文件'
           }
       )
       await event_bus.emit(event)
       await asyncio.sleep(0.5)

       # 发送子智能体进度事件
       for i in range(3):
           progress_event = MonitoringEvent(
               type=EventType.SUBAGENT_PROGRESS,
               dialog_id=dialog_id,
               source='Subagent:Explore:FileFinder',
               context_id=uuid4(),
               priority=EventPriority.LOW,
               payload={
                   'subagent_name': 'FileFinder',
                   'progress': {'step': i+1, 'total': 3}
               }
           )
           await event_bus.emit(progress_event)
           await asyncio.sleep(0.3)

       # 发送子智能体完成事件
       completed_event = MonitoringEvent(
           type=EventType.SUBAGENT_COMPLETED,
           dialog_id=dialog_id,
           source='Subagent:Explore:FileFinder',
           context_id=uuid4(),
           priority=EventPriority.HIGH,
           payload={
               'subagent_name': 'FileFinder',
               'subagent_type': 'Explore',
               'result_preview': '找到 5 个文件',
               'duration_ms': 1500
           }
       )
       await event_bus.emit(completed_event)
       await asyncio.sleep(0.5)

       await event_bus.stop_processing()
       print('✓ Subagent events emitted successfully!')
       print('  Check the Monitor tab for:')
       print('    - SUBAGENT_STARTED')
       print('    - SUBAGENT_PROGRESS (x3)')
       print('    - SUBAGENT_COMPLETED')

   asyncio.run(emit_subagent_events())
   "
   ```

3. **检查前端过滤器**：
   - 确保 Monitor 页面的过滤器包含 "子智能体" 类型
   - 检查事件时间线是否过滤了 SUBAGENT 事件

---

## 自动化测试脚本（可选）

```python
# test_monitoring.py
# 自动化测试脚本示例

import asyncio
import websockets
import json

async def test_monitoring():
    uri = "ws://localhost:8001/ws/test-client"
    async with websockets.connect(uri) as websocket:
        # 订阅对话框
        await websocket.send(json.dumps({
            "type": "subscribe",
            "dialog_id": "test-dialog"
        }))

        # 发送用户输入
        await websocket.send(json.dumps({
            "type": "user:input",
            "dialog_id": "test-dialog",
            "content": "你好"
        }))

        # 接收事件
        events = []
        for _ in range(10):  # 接收最多 10 个事件
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(msg)
                if data.get("type", "").startswith("monitor:"):
                    events.append(data)
                    print(f"Received: {data['type']}")
            except asyncio.TimeoutError:
                break

        # 验证结果
        assert len(events) > 0, "No monitoring events received"
        print(f"✓ Received {len(events)} monitoring events")

if __name__ == "__main__":
    asyncio.run(test_monitoring())
```

---

## 记录测试结果

| 日期 | 测试员 | 通过率 | 备注 |
|------|--------|--------|------|
| | | | |

