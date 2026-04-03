# 架构重构执行计划

## 阶段一：模型层清理（可并行）✅

**任务1-1**: ~~清理 tool.py 重复代码~~ ✅ 已完成
- 将 tool.py 改为从 tool_models.py 重新导出
- 风险：低
- 依赖：无

**任务1-2**: 删除废弃的模型文件（并行执行）
- 删除 `core/models/dialog.py`（内容已迁移至 entities.py）
- 删除 `core/models/event_models.py`（已标记废弃）
- 删除 `core/models/dto.py`（已标记废弃）
- 删除 `core/models/response_models.py`（已合并至 api.py）
- 删除 `core/models/stats_models.py`（已合并至 api.py）
- **并行度**：5个文件可同时进行
- **风险**：低（只需确认无活跃导入）
- **依赖**：无

**任务1-3**: 统一 types.py（独立任务）
- 将 `core/types.py` 迁移至 `core/models/types.py`
- 更新所有导入语句
- **并行度**：可独立执行
- **风险**：中（需要全局搜索替换导入）
- **依赖**：无

---

## 阶段二：运行时层重构（串行）⚠️

**任务2-1**: 分析 Runtime 依赖关系（前置任务）
- 确认哪些代码依赖 `core/agent/runtime.py` 的 `AgentRuntime`
- 确认哪些代码依赖 `core/agent/interface.py`
- **阻塞后续任务**：是
- **依赖**：阶段一完成

**任务2-2**: 迁移 Runtime 抽象（串行）
- 统一使用 `core/runtime/interfaces.py` 中的 `IAgentRuntime`
- 更新 `core/agent/runtimes/base.py` 继承关系
- **阻塞后续任务**：是
- **依赖**：任务2-1

**任务2-3**: 删除旧 Runtime 文件（串行）
- 删除 `core/agent/runtime.py`
- 删除 `core/agent/interface.py`
- 删除 `core/agent/factory.py`
- **依赖**：任务2-2

**任务2-4**: 移动 Runtime 实现（可选）
- 将 `core/agent/runtimes/` 移动到 `core/runtime/`
- 更新所有导入
- **依赖**：任务2-3

---

## 阶段三：基础设施清理（可并行）🔧

**任务3-1**: 删除临时文件（独立）
- 删除 `core/agent/runtimes/.tmp_mypy_check_*.py`
- 删除其他临时文件
- **并行度**：可独立执行
- **风险**：极低
- **依赖**：无

**任务3-2**: 统一 EventBus 位置（独立）
- 将 `runtime/event_bus.py` 移动到 `core/runtime/event_bus.py`
- 统一 `IEventBus` 接口定义
- **并行度**：可独立执行
- **风险**：中
- **依赖**：无

**任务3-3**: 清理 adapters 目录（独立）
- 评估 `core/agent/adapters/` 必要性
- 如无使用则删除
- **并行度**：可独立执行
- **风险**：低
- **依赖**：无

---

## 阶段四：接口层统一（串行）🔗

**任务4-1**: 创建统一接口目录（可选）
- 创建 `core/interfaces/` 目录
- 将分散的接口定义迁移至此
- **阻塞后续任务**：是
- **依赖**：阶段二、三完成

**任务4-2**: 修复桥接层依赖（串行）
- 确保 `AgentRuntimeBridge` 通过接口注入 `IWebSocketBroadcaster`
- **依赖**：任务4-1

---

## 阶段五：导入循环修复（串行）🔄

**任务5-1**: 修复 `core/models/__init__.py` 循环导入（串行）
- 使用 `TYPE_CHECKING` 标记
- 简化导出内容
- **阻塞后续任务**：是
- **依赖**：阶段一完成

**任务5-2**: 修复其他循环导入（串行）
- 检查并修复 `core/agent/__init__.py`
- 检查并修复其他模块
- **依赖**：任务5-1

---

## 执行流程图

```
阶段一: 模型层清理
├── 任务1-1 ✅ 已完成
├── 任务1-2 删除废弃模型文件（并行）
│   ├── 删除 dialog.py
│   ├── 删除 event_models.py
│   ├── 删除 dto.py
│   ├── 删除 response_models.py
│   └── 删除 stats_models.py
└── 任务1-3 统一 types.py

        ↓ (阶段一全部完成后)

阶段二: 运行时层重构（串行）
├── 任务2-1 分析依赖关系
├── 任务2-2 迁移 Runtime 抽象
├── 任务2-3 删除旧文件
└── 任务2-4 移动目录（可选）

        ↓ (阶段二完成后)

阶段三: 基础设施清理（可与阶段二并行）
├── 任务3-1 删除临时文件
├── 任务3-2 统一 EventBus
└── 任务3-3 清理 adapters

        ↓ (阶段二、三完成后)

阶段四: 接口层统一（串行）
├── 任务4-1 创建统一接口目录
└── 任务4-2 修复桥接层依赖

        ↓ (阶段四完成后)

阶段五: 导入循环修复（串行）
├── 任务5-1 修复 models/__init__.py
└── 任务5-2 修复其他循环导入

        ↓ (全部完成后)

阶段六: 验证
├── 运行所有测试
├── 启动服务验证
└── 检查类型错误
```

---

## 并行任务组

### 可并行组 A（独立任务）
- [ ] 删除 core/models/dialog.py
- [ ] 删除 core/models/event_models.py
- [ ] 删除 core/models/dto.py
- [ ] 删除 core/models/response_models.py
- [ ] 删除 core/models/stats_models.py
- [ ] 删除临时文件 (.tmp_mypy_check_*.py)
- [ ] 清理 adapters 目录

### 可并行组 B（依赖组 A）
- [ ] 统一 types.py
- [ ] 统一 EventBus 位置

### 串行组 C（依赖组 A、B）
- [ ] 分析 Runtime 依赖
- [ ] 迁移 Runtime 抽象
- [ ] 删除旧 Runtime 文件

### 串行组 D（依赖组 C）
- [ ] 统一接口目录
- [ ] 修复桥接层依赖

### 串行组 E（依赖组 D）
- [ ] 修复循环导入

---

## 建议执行顺序

**第一波（并行）**: 删除所有废弃模型文件（任务1-2）
**第二波（并行）**: 清理临时文件和 adapters（任务3-1、3-3）
**第三波（串行）**: Runtime 层重构（任务2-1 到 2-4）
**第四波（并行）**: 基础设施统一（任务3-2、1-3）
**第五波（串行）**: 接口层和循环导入修复（任务4、5）

---

## 风险评估

| 阶段 | 风险等级 | 原因 |
|------|---------|------|
| 阶段一 | 低 | 删除已标记废弃的文件 |
| 阶段二 | 高 | Runtime 是核心组件，影响面广 |
| 阶段三 | 低 | 基础设施清理 |
| 阶段四 | 中 | 接口变更影响调用方 |
| 阶段五 | 中 | 导入变更可能影响运行时 |

---

*计划创建时间: 2026-03-30*
