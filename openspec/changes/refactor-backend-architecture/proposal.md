## Why

当前后端架构存在严重的语义不一致问题，导致代码难以理解和维护：

1. **数据模型分散在各处**：模型定义散落在 `core/models/`、`core/models/entities/`、`core/session/models.py`、`core/types/`、`core/application/dto/` 等多个位置，没有统一的存放规范
2. **目录层级过深且混乱**：`core/agent/` 目录下有 5 层嵌套（runtimes/agents/middleware/），包含大量重复的 mixins 和 adapters
3. **命名不一致**：有的目录用单数（entity），有的用复数（models）；接口文件有的叫 `interfaces.py`，有的叫 `base.py`
4. **职责边界模糊**：`capabilities/`、`bridge/`、`domain/` 三个层的职责不清晰，存在交叉依赖
5. **冗余目录**：同时存在 `core/infra/` 和 `core/infrastructure/` 两个相同语义的目录
6. **根目录结构混乱**：`interfaces/` 和 `runtime/` 目录位于项目根目录，与 `core/` 并列，导致后端代码分散在多个位置
7. **目录命名不清晰**：`core/` 命名过于宽泛，应明确命名为 `backend/` 以反映其用途

这些问题导致新开发者难以理解代码结构，也增加了维护成本。

## What Changes

- **BREAKING**: 将项目根目录的 `interfaces/` 和 `runtime/` 移动到 `core/` 中，统一后端代码位置

- **BREAKING**: 将 `core/` 目录重命名为 `backend/`，使目录命名反映其真实用途

- **BREAKING**: 重新设计 `backend/` 目录结构，建立清晰的 4 层架构：
  - `domain/` - 领域层（实体、值对象、领域服务）
  - `application/` - 应用层（用例、DTO、应用服务）
  - `infrastructure/` - 基础设施层（持久化、外部服务、运行时）
  - `interfaces/` - 接口层（API、WebSocket、CLI，从根目录移入）

- **BREAKING**: 统一所有数据模型到 `domain/models/` 目录，按领域划分：
  - `domain/models/dialog/` - 对话相关模型
  - `domain/models/message/` - 消息相关模型
  - `domain/models/agent/` - Agent 相关模型
  - `domain/models/events/` - 事件模型

- **BREAKING**: 扁平化 `agent/` 目录结构：
  - 将 `core/agent/runtimes/` 下的 5 层嵌套压缩为 2 层
  - 移除未使用的 adapter 和 mixin 文件
  - 统一运行时实现到 `infrastructure/runtime/`

- **BREAKING**: 合并 `infra/` 和 `infrastructure/` 为统一的 `infrastructure/`

- **BREAKING**: 统一命名规范：
  - 目录全部使用复数形式（`models/`、`services/`、`repositories/`）
  - 接口文件统一命名为 `protocols.py` 或放在 `interfaces/` 子目录
  - 删除冗余的 `base.py`，统一用 `protocols.py`

- **BREAKING**: 项目根目录只保留 `main.py`，其他所有后端代码移入 `backend/`

- **非破坏性**: 创建 `backend/ARCHITECTURE.md` 文档说明新的架构规范

## Capabilities

### New Capabilities
- `clean-architecture`: 实现清晰的分层架构，明确各层职责边界
- `model-consolidation`: 统一数据模型存放位置，建立模型组织规范
- `naming-convention`: 建立统一的命名规范，消除不一致
- `directory-consolidation`: 将分散的后端代码统一移入 backend/ 目录
- `root-cleanup`: 清理项目根目录，只保留 main.py 作为入口点

### Modified Capabilities
- 无现有 spec 需要修改（这是纯重构，不涉及功能变更）

## Impact

- **根目录的 `interfaces/` 和 `runtime/` 将被移除** - 代码移至 `backend/interfaces/` 和 `backend/runtime/`
- **`core/` 目录将重命名为 `backend/`** - 所有导入路径从 `core.xxx` 变为 `backend.xxx`
- **所有后端导入路径将发生变化** - 需要更新 import 语句
- **测试文件需要同步更新** - 所有测试中的导入路径需要调整
- **CLAUDE.md 文档需要更新** - 架构描述需要与新的目录结构保持一致
- **开发者需要重新熟悉** - 团队需要了解新的架构规范
- **无外部 API 变更** - REST API 和 WebSocket 接口保持不变
