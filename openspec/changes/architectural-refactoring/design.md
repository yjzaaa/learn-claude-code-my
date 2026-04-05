## 上下文

当前代码库存在几个架构反模式：

1. **单体文件**：
   - `deep.py` (939 行) 处理 agent 生命周期、事件流、模型切换、错误处理和 checkpoint 管理
   - `provider_manager.py` (746 行) 混合了模型发现、连通性测试、配置管理
   - `InputArea.tsx` (776 行) 组合了消息输入、模型选择、斜杠命令和文件上传

2. **代码重复**：
   - 后端文件中有 22 处 `logger = logging.getLogger(__name__)` 的重复定义
   - 多个服务中重复模型配置逻辑
   - 前端中类似的 WebSocket 事件处理模式分散在各处

3. **目录结构问题**：
   - 日志文件分散在 `logs/` 目录下，没有清晰的分类
   - 中间件文件混合在 runtime 目录中，没有按功能分组
   - 大 UI 文件中组件职责模糊

## 目标 / 非目标

**目标**：
- 将超过 500 行的文件拆分为职责单一的专注模块
- 建立集中式日志工厂，消除重复的 logger 设置
- 为日志、中间件和组件创建一致的目录结构
- 提高代码可维护性，降低认知负荷
- 重构期间保持 100% 向后兼容

**非目标**：
- 不更改外部 API 或行为
- 不添加新功能
- 不更改数据库 schema
- 不升级或移除依赖

## 决策

### 1. 后端文件拆分策略

**决策**：将 `deep.py` 拆分为 4 个专注模块：
- `deep_agent.py`：核心 agent 生命周期和初始化
- `deep_events.py`：事件流和处理
- `deep_model.py`：模型切换和 provider 管理
- `deep_checkpoint.py`：Checkpoint 和状态管理

**理由**：每个模块将少于 250 行，符合项目的 300 行限制。模块间依赖通过构造函数注入显式声明。

### 2. Provider Manager 重构

**决策**：将 `provider_manager.py` 拆分为：
- `provider_discovery.py`：从环境变量发现模型
- `provider_connectivity.py`：使用真实 LLM 调用进行连通性测试
- `provider_factory.py`：模型实例创建（ChatLiteLLM/ChatAnthropic）

**理由**：分离关注点，使每个组件可独立测试。发现可以缓存，连通性可异步测试，工厂逻辑简化。

### 3. 日志抽象

**决策**：创建 `backend/infrastructure/logging/logger_factory.py`：
```python
class LoggerFactory:
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        # 所有 logger 使用一致的配置
        return logger
```

**理由**：集中日志配置（formatter、handler、level）并消除 22 处重复设置模式。

### 4. 前端组件分解

**决策**：将 `InputArea.tsx` 拆分为：
- `InputArea.tsx`：核心输入和提交逻辑（~200 行）
- `ModelSelector.tsx`：模型下拉选择和切换（~150 行）
- `SlashCommandMenu.tsx`：命令建议和过滤（~100 行）
- `FileAttachment.tsx`：文件上传和预览（~100 行）

**理由**：每个组件职责单一。ModelSelector 可以在其他上下文中复用。

### 5. 目录重组

**决策**：
- `logs/` → `logs/{runtime,debug,connectivity,snapshots}/`
- `backend/infrastructure/runtime/middleware/` → 按功能组织（compression、caching、skills）
- 保持现有模块结构，但改进内部组织

**理由**：清晰的分离使日志轮转、调试和导航更容易。

## 风险 / 权衡

**风险**：重构可能引入事件处理时序的微妙 bug
→ **缓解**：拆分前后进行全面测试；保持集成测试

**风险**：文件拆分可能增加导入复杂度
→ **缓解**：清晰的 `__init__.py` 导出；保持向后兼容的导入

**风险**：大型 PR 难以审查
→ **缓解**：按能力拆分为增量 PR；先合并到功能分支

**风险**：deep.py 中的 checkpoint/状态管理耦合复杂
→ **缓解**：先提取接口，再提取实现；完全保留现有行为

## 迁移计划

1. **阶段 1**：日志抽象（低风险，高影响）
2. **阶段 2**：Provider manager 拆分（独立组件）
3. **阶段 3**：前端组件分解
4. **阶段 4**：Deep.py 模块化（最高复杂度）
5. **阶段 5**：目录清理和最终验证

每个阶段包括：
- 提取代码到新文件
- 更新现有文件中的导入
- 运行完整测试套件
- 部署到 staging 环境
- 进入下一阶段前监控 24 小时

## 待解决问题

1. 应该使用依赖注入框架还是手动构造函数注入？
2. 如何处理拆分后的 deep.py 模块间的共享状态？
3. 是否应该立即为每个新模块创建单独的测试文件？
