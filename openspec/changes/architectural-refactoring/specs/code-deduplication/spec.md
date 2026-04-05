## ADDED Requirements

### Requirement: Logger 定义必须统一
系统 SHALL 消除所有重复的 `logger = logging.getLogger(__name__)` 定义，统一使用 LoggerFactory。

#### Scenario: LoggerFactory 创建
- **WHEN** 检查 `backend/infrastructure/logging/factory.py`
- **THEN** 它 SHALL 包含 LoggerFactory 类
- **AND** 它 SHALL 提供 `get_logger(name)` 方法
- **AND** 所有 logger SHALL 使用相同的 formatter 和 level 配置

#### Scenario: 重复 logger 定义消除
- **WHEN** 搜索整个后端代码库的 `logger = logging.getLogger(__name__)`
- **THEN** 只在 `backend/infrastructure/logging/factory.py` 中找到
- **AND** 所有其他文件 SHALL 使用 `from backend.infrastructure.logging import get_logger`

#### Scenario: LoggerMixin 可用性
- **WHEN** 类继承 `LoggerMixin`
- **THEN** 它 SHALL 自动拥有 `self.logger` 属性
- **AND** 无需在类外部定义 logger

### Requirement: 时间戳函数必须统一
系统 SHALL 将所有时间戳相关函数集中到一个工具模块。

#### Scenario: TimeUtils 工具类
- **WHEN** 检查 `backend/domain/utils/time_utils.py`
- **THEN** 它 SHALL 包含 `TimeUtils` 类
- **AND** 它 SHALL 提供 `timestamp_ms()`, `iso_timestamp()` 方法

#### Scenario: 时间函数使用统一
- **WHEN** 检查使用 `timestamp_ms` 或 `iso_timestamp` 的代码
- **THEN** 所有导入 SHALL 来自 `backend.domain.utils.time_utils`
- **AND** 不应有其他实现或重复定义

### Requirement: Snapshot 构建逻辑必须统一
系统 SHALL 将所有对话快照构建逻辑统一到一个构建器类。

#### Scenario: SnapshotBuilder 创建
- **WHEN** 检查 `backend/domain/utils/snapshot_builder.py`
- **THEN** 它 SHALL 包含 `SnapshotBuilder` 类
- **AND** 它 SHALL 提供 `build_from_session()` 静态方法
- **AND** 它 SHALL 处理消息转换、元数据构建等所有逻辑

#### Scenario: 原有构建逻辑迁移
- **WHEN** 检查 `backend/domain/models/dialog/manager.py` 的 `build_snapshot()`
- **THEN** 它 SHALL 调用 `SnapshotBuilder.build_from_session()`
- **AND** 不应有独立的构建逻辑

#### Scenario: 向后兼容
- **WHEN** 调用 `build_dialog_snapshot()` 函数
- **THEN** 它 SHALL 继续工作
- **AND** 它 SHALL 内部使用 `SnapshotBuilder`

### Requirement: Mixin 类层次必须优化
系统 SHALL 创建基础 Mixin 类，优化现有 Mixin 继承关系。

#### Scenario: 基础 Mixin 创建
- **WHEN** 检查 `backend/domain/models/shared/base_mixins.py`
- **THEN** 它 SHALL 包含 `ComparableMixin`
- **AND** 它 SHALL 包含 `SerializableMixin`
- **AND** 它 SHALL 包含 `ValidatableMixin`

#### Scenario: LoggerMixin 可用
- **WHEN** 检查 `backend/infrastructure/logging/mixins.py`
- **THEN** 它 SHALL 包含 `LoggerMixin`
- **AND** 继承它的类 SHALL 自动拥有 `self.logger` 属性

#### Scenario: Mixin 使用优化
- **WHEN** 检查现有使用 Mixin 的类
- **THEN** 它们 SHALL 继承最基础的 Mixin
- **AND** 不应有重复功能的不同 Mixin

### Requirement: 异常层次必须统一
系统 SHALL 创建统一的异常层次结构。

#### Scenario: 基础异常创建
- **WHEN** 检查 `backend/domain/exceptions/base.py`
- **THEN** 它 SHALL 定义 `DomainError` 基础类
- **AND** 它 SHALL 定义常见异常类型：`NotFoundError`, `AlreadyExistsError`, `StateError`

#### Scenario: 具体异常继承
- **WHEN** 检查 `backend/domain/exceptions/dialog.py`
- **THEN** `SessionNotFoundError` SHALL 继承 `NotFoundError`
- **AND** `SessionAlreadyExistsError` SHALL 继承 `AlreadyExistsError`
- **AND** `InvalidTransitionError` SHALL 继承 `StateError`

#### Scenario: 异常信息标准化
- **WHEN** 捕获 `DomainError` 异常
- **THEN** 它 SHALL 有 `code`, `message`, `details` 属性
- **AND** 错误响应 SHALL 使用统一格式
