## Context

当前后端架构经过多年演化，形成了复杂且不一致的目录结构。主要问题：

1. **模型分散**: 同一领域的模型分布在 5+ 个不同目录
2. **目录嵌套过深**: `core/agent/runtimes/agents/middleware/` 达到 5 层嵌套
3. **职责混乱**: `capabilities/`、`bridge/`、`domain/` 三者边界不清
4. **命名不一致**: 单数/复数混用，接口文件命名不统一
5. **后端代码分散**: `interfaces/` 和 `runtime/` 位于项目根目录，与 `core/` 并列
6. **目录命名模糊**: `core/` 命名过于宽泛，无法清晰表达其用途

当前目录统计：
- 131 个 Python 文件在 core/
- 15 个 Python 文件在 interfaces/ 和 runtime/
- 最大嵌套深度: 6 层
- 模型相关文件分布在 8 个不同目录

## Goals / Non-Goals

**Goals:**
1. 将 `core/` 重命名为 `backend/`，使目录命名反映其用途
2. 将根目录的 `interfaces/` 和 `runtime/` 移入 `backend/`，统一后端代码位置
3. 建立清晰的 4 层 Clean Architecture
4. 统一所有模型到 `domain/models/` 并按领域组织
5. 扁平化目录结构（最大深度不超过 4 层）
6. 统一命名规范（全部复数、接口统一命名）
7. 消除冗余目录（合并 infra/ 和 infrastructure/）
8. 项目根目录只保留 `main.py` 作为入口点

**Non-Goals:**
1. 不改变任何业务逻辑或功能行为
2. 不改变外部 API（REST/WebSocket）
3. 不引入新的依赖或框架
4. 不优化性能（纯结构调整）

## Decisions

### Decision 1: 将 core/ 重命名为 backend/

**选择**: 将 `core/` 重命名为 `backend/`

**理由**:
- `backend/` 明确表达了这是后端代码目录
- `core/` 过于宽泛，容易与 frontend core 或其他 core 概念混淆
- 符合常见项目结构约定（backend/ + frontend/ 或 web/）

**影响**:
- 所有 `from core.xxx` 导入变为 `from backend.xxx`
- 更新 main.py、tests/、CLAUDE.md 等所有引用

### Decision 2: 将 interfaces/ 和 runtime/ 移入 backend/

**选择**: 将项目根目录的 `interfaces/` 和 `runtime/` 移动到 `backend/` 中

**理由**:
- 所有后端代码统一在一个目录下，避免分散
- `interfaces/` 属于接口层，应作为 backend 的一部分
- `runtime/` 是运行时基础设施，属于后端核心
- 项目根目录只保留入口文件（main.py）和配置（README, .env 等）

**新结构**:
```
backend/
├── domain/          # 领域层
├── application/     # 应用层
├── infrastructure/  # 基础设施层
├── interfaces/      # 接口层（从根目录移入）
│   ├── http/        # HTTP 路由
│   └── websocket/   # WebSocket 处理器
└── runtime/         # 运行时（从根目录移入，合并现有 core/runtime/）
    └── event_bus.py
```

### Decision 3: 采用 4 层 Clean Architecture

**选择**: 严格分层架构（Domain → Application → Infrastructure → Interfaces）

**理由**:
- 业界成熟模式，职责边界清晰
- 与当前代码的大部分概念兼容
- 便于测试（可以 mock 底层依赖）

**替代方案**: Hexagonal Architecture（端口适配器模式）
- 拒绝原因：对当前团队学习成本较高，且现有代码不完全匹配

### Decision 2: 模型按领域组织而非类型组织

**选择**: `domain/models/dialog/` 而非 `domain/models/entities/`

**理由**:
- 按领域组织更符合 DDD 思想
- 查找相关模型更直观（所有对话相关在一个目录）
- 避免 `entities/` 目录过于庞大

**目录结构**:
```
domain/models/
├── dialog/           # 对话领域
│   ├── dialog.py     # Dialog 实体
│   ├── session.py    # Session 实体
│   └── events.py     # 对话相关事件
├── message/          # 消息领域
│   ├── message.py    # Message 实体
│   ├── content.py    # 内容类型
│   └── adapter.py    # 消息适配器
├── agent/            # Agent 领域
│   ├── runtime.py    # Runtime 配置
│   ├── config.py     # Agent 配置
│   └── events.py     # Agent 事件
└── events/           # 共享事件类型
    ├── base.py
    └── websocket.py
```

### Decision 3: 运行时实现移到 Infrastructure 层

**选择**: `infrastructure/runtime/` 而非 `agent/runtimes/`

**理由**:
- Runtime 属于技术实现细节，应在 Infrastructure 层
- Agent 概念应保留在 Domain 层（Agent 配置、行为定义）
- 区分 "Agent 是什么"（Domain）和 "Agent 如何运行"（Infrastructure）

**新结构**:
```
infrastructure/runtime/
├── __init__.py
├── runtime.py          # Runtime 抽象协议
├── simple_runtime.py   # Simple 实现
├── deep_runtime.py     # Deep Agent 实现
└── services/           # Runtime 辅助服务
    ├── logging.py
    └── compression.py
```

### Decision 4: 统一接口命名为 protocols.py

**选择**: 所有接口定义放在 `protocols.py`

**理由**:
- `protocols.py` 比 `interfaces.py` 更符合 Python 3.8+ 的 typing.Protocol 概念
- 比 `base.py` 语义更清晰
- 统一命名便于查找

**映射**:
- `core/agent/interface.py` → `domain/protocols/agent.py`
- `core/capabilities/interfaces.py` → `application/protocols/capabilities.py`
- `core/bridge/interfaces.py` → `infrastructure/protocols/bridge.py`

### Decision 5: 保留 tests/ 目录结构不变

**选择**: 测试文件跟随源码移动，但保持 `tests/` 根目录结构

**理由**:
- 避免测试与源码混合
- 保持测试发现简单
- 与现有 CI/CD 配置兼容

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| 导入路径变更导致大面积修改 | 高 | 1. 一次性完成全部移动<br>2. 使用 IDE 批量重构<br>3. 完整回归测试 |
| 功能回归风险 | 中 | 1. 不改变任何实现逻辑<br>2. 仅移动文件和修改导入<br>3. 所有测试必须通过 |
| 团队成员适应成本 | 低 | 1. 编写 ARCHITECTURE.md<br>2. 更新 CLAUDE.md<br>3. 代码审查时提醒 |
| 合并冲突风险 | 中 | 1. 在团队空闲期执行<br>2. 提前通知所有人冻结代码<br>3. 快速完成（目标 1 天内）|

## Migration Plan

### Phase 1: 准备（提前 1 天）
1. 创建 feature branch: `refactor/architecture`
2. 通知团队代码冻结
3. 确保所有 CI 测试通过

### Phase 2: 执行（1 天）
1. **将 core/ 重命名为 backend/**（10 min）
   - 使用 git mv 保留历史
2. **移动 interfaces/ 到 backend/**（15 min）
   - 移动 `interfaces/` → `backend/interfaces/`
   - 保留子目录结构（http/, websocket/）
3. **移动 runtime/ 到 backend/**（15 min）
   - 移动 `runtime/` → `backend/runtime/`
   - 与现有的 `backend/runtime/` 合并（如有冲突）
4. **创建新目录结构**（30 min）
5. **移动 Domain 层**（1 hour）
   - 移动所有模型到 `backend/domain/models/`
   - 移动仓库接口到 `backend/domain/repositories/`
6. **移动 Application 层**（1 hour）
   - 移动服务到 `backend/application/services/`
   - 移动 DTO 到 `backend/application/dto/`
7. **移动 Infrastructure 层**（1.5 hour）
   - 移动 Runtime 实现
   - 移动 Provider 实现
   - 移动 Persistence 实现
8. **更新所有导入**（1 hour）
   - 更新 `core.` → `backend.`
   - 更新 `interfaces.` → `backend.interfaces.`
   - 更新 `runtime.` → `backend.runtime.`
9. **运行测试并修复**（1 hour）

### Phase 3: 验证（半天）
1. 完整测试套件通过
2. 手动验证关键流程
3. 更新文档

### Phase 4: 合并
1. 创建 PR
2. 快速审查（只检查文件移动，不检查逻辑）
3. 合并到 main

### Rollback Strategy
- 如有严重问题，revert 整个 PR
- 由于只是文件移动，revert 安全
- 确保在 revert 前通知团队

## Open Questions

1. **Q**: `core/` 重命名为 `backend/` 的时机？
   **A**: 在移动 `interfaces/` 和 `runtime/` 之前或之后都可以，但建议先移动再重命名，以便清晰看到最终结构

2. **Q**: `backend/types/` 目录是否保留？
   **A**: 合并到 `backend/domain/models/shared/`，作为跨领域共享类型

3. **Q**: `skills/` 目录位置？
   **A**: 保留在项目根目录，不属于 backend 架构的一部分

4. **Q**: 如何处理 `main.py`？
   **A**: 保留在项目根目录，作为应用入口点，导入路径更新为 `from backend.xxx import ...`

5. **Q**: `runtime/` 和 `backend/runtime/` 如何合并？
   **A**: 检查文件冲突，如果存在同名文件则手动合并内容，否则直接移动
