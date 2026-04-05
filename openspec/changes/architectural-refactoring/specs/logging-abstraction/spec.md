## ADDED Requirements

### Requirement: 日志工厂必须提供统一接口
系统 SHALL 提供 `backend/infrastructure/logging/logger_factory.py`，用于统一创建和配置 logger。

#### Scenario: 通过工厂获取 logger
- **WHEN** 调用 `LoggerFactory.get_logger(__name__)`
- **THEN** 返回配置好的 logger 实例
- **AND** 所有 logger 使用相同的 formatter 和 handler 配置

#### Scenario: 消除重复代码
- **WHEN** 搜索 `logger = logging.getLogger(__name__)`
- **THEN** 后端代码中只找到工厂内部的这行代码
- **AND** 其他所有模块都使用工厂方法

### Requirement: 现有代码必须迁移到日志工厂
系统 SHALL 将所有 22 个现有的 logger 定义迁移到使用 LoggerFactory。

#### Scenario: 迁移验证
- **WHEN** 检查任意后端 Python 文件
- **THEN** 如果文件需要 logger，它 SHALL 从工厂导入
- **AND** 不应有直接创建 logger 的代码

#### Scenario: 配置一致性
- **WHEN** 比较不同模块的日志输出
- **THEN** 所有日志 SHALL 使用相同的格式
- **AND** 日志级别配置 SHALL 集中管理

### Requirement: ProviderManager 必须拆分
系统 SHALL 将 `backend/infrastructure/services/provider_manager.py` (746 行) 拆分为专注的模块。

#### Scenario: 模型发现分离
- **WHEN** 检查 `backend/infrastructure/services/model_discovery.py`
- **THEN** 它 SHALL 只包含从环境变量发现模型的逻辑
- **AND** 代码行数 SHALL 小于 200 行

#### Scenario: 连通性测试分离
- **WHEN** 检查 `backend/infrastructure/services/model_connectivity.py`
- **THEN** 它 SHALL 只包含测试 LLM 连通性的逻辑
- **AND** 代码行数 SHALL 小于 250 行

#### Scenario: 模型工厂分离
- **WHEN** 检查 `backend/infrastructure/services/model_factory.py`
- **THEN** 它 SHALL 只包含创建 ChatLiteLLM/ChatAnthropic 实例的逻辑
- **AND** 代码行数 SHALL 小于 200 行
