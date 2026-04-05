# 重复代码整合设计

## 1. Logger 重复代码整合

### 当前问题
**22 个文件**包含相同的 logger 定义模式：
```python
import logging
logger = logging.getLogger(__name__)
```

### 影响文件清单
```
backend/interfaces/websocket/broadcast.py
backend/interfaces/websocket/server.py
backend/infrastructure/websocket_buffer/buffer.py
backend/interfaces/websocket/handler.py
backend/infrastructure/event_bus/queued_event_bus.py
backend/infrastructure/event_bus/handlers.py
backend/application/engine.py
backend/infrastructure/agent_queue/task_queue.py
backend/infrastructure/llm_adapter/streaming.py
backend/infrastructure/runtime/middleware/claude_compression.py
backend/infrastructure/runtime/services/docker_sandbox_backend.py
backend/infrastructure/runtime/event_bus.py
backend/interfaces/http/routes/dialogs.py
backend/domain/models/dialog/manager.py
backend/infrastructure/services/dialog_manager.py
backend/infrastructure/services/memory_manager.py
backend/infrastructure/services/model_discovery.py
backend/infrastructure/services/provider_manager.py
backend/infrastructure/services/skill_manager.py
backend/infrastructure/services/state_manager.py
backend/infrastructure/services/tool_manager.py
backend/interfaces/http/routes/messages.py
```

### 整合方案

#### 1.1 创建 LoggerFactory
```python
# backend/infrastructure/logging/factory.py
import logging
from typing import Optional

class LoggerFactory:
    """统一日志工厂，集中管理所有 logger 配置"""
    
    _configured_loggers: set[str] = set()
    
    @staticmethod
    def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
        """
        获取配置好的 logger
        
        Args:
            name: logger 名称，通常使用 __name__
            level: 可选的日志级别，默认使用配置中的级别
            
        Returns:
            配置好的 Logger 实例
        """
        logger = logging.getLogger(name)
        
        # 只配置一次
        if name not in LoggerFactory._configured_loggers:
            LoggerFactory._configure_logger(logger, level)
            LoggerFactory._configured_loggers.add(name)
            
        return logger
    
    @staticmethod
    def _configure_logger(logger: logging.Logger, level: Optional[int] = None) -> None:
        """配置 logger 的 formatter 和 handler"""
        if level:
            logger.setLevel(level)
        
        # 如果 logger 没有 handler，添加默认 handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)


# 便捷函数，用于快速导入
def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """快捷获取 logger"""
    return LoggerFactory.get_logger(name, level)
```

#### 1.2 使用方式变更
```python
# 重构前
import logging
logger = logging.getLogger(__name__)

# 重构后
from backend.infrastructure.logging import get_logger
logger = get_logger(__name__)
```

#### 1.3 迁移脚本 (伪代码)
```bash
# 1. 批量替换导入
find backend -name "*.py" -exec sed -i 's/^import logging$/from backend.infrastructure.logging import get_logger/' {} \;

# 2. 批量替换 logger 定义
find backend -name "*.py" -exec sed -i 's/^logger = logging.getLogger(__name__)$/logger = get_logger(__name__)/' {} \;

# 3. 手动检查特殊情况（如 logging 用于其他用途）
```

---

## 2. 时间戳函数重复整合

### 当前问题
`timestamp_ms()` 和 `iso_timestamp()` 在多个地方被使用，且只在 `dialog_service.py` 中定义。

### 使用位置
```python
# backend/domain/services/dialog_service.py (定义处)
def timestamp_ms() -> int:
    return int(time.time() * 1000)

def iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

# 使用位置：
backend/interfaces/websocket/handler.py
backend/interfaces/http/routes/agent.py
backend/interfaces/http/routes/messages.py
backend/infrastructure/event_bus/handlers.py (多处使用)
```

### 整合方案

#### 2.1 创建时间工具模块
```python
# backend/domain/utils/time_utils.py
import time
from datetime import datetime, timezone
from typing import Union

class TimeUtils:
    """时间工具类，提供统一的时间戳生成方法"""
    
    @staticmethod
    def timestamp_ms() -> int:
        """获取毫秒级时间戳"""
        return int(time.time() * 1000)
    
    @staticmethod
    def timestamp_sec() -> int:
        """获取秒级时间戳"""
        return int(time.time())
    
    @staticmethod
    def iso_timestamp() -> str:
        """获取 ISO 格式 UTC 时间戳"""
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def iso_timestamp_with_tz() -> str:
        """获取带时区的 ISO 时间戳"""
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def format_duration_ms(start_ms: int, end_ms: Optional[int] = None) -> str:
        """格式化持续时间（毫秒）"""
        if end_ms is None:
            end_ms = TimeUtils.timestamp_ms()
        duration = end_ms - start_ms
        return f"{duration}ms"


# 便捷导入
from backend.domain.utils.time_utils import TimeUtils as time_utils

timestamp_ms = time_utils.timestamp_ms
iso_timestamp = time_utils.iso_timestamp
```

#### 2.2 使用方式变更
```python
# 重构前 (dialog_service.py)
from backend.domain.services.dialog_service import timestamp_ms

# 重构后
from backend.domain.utils.time_utils import timestamp_ms, iso_timestamp
```

---

## 3. Snapshot 构建逻辑重复

### 当前问题
`build_snapshot()` 和 `build_dialog_snapshot()` 逻辑分散在多个地方。

### 使用位置
```python
backend/domain/models/dialog/manager.py       # DialogSessionManager.build_snapshot()
backend/domain/services/dialog_service.py     # build_dialog_snapshot()
backend/infrastructure/event_bus/handlers.py  # 多处调用
backend/interfaces/http/routes/dialogs.py     # 调用 dialog_service
backend/interfaces/http/routes/messages.py    # 调用 dialog_service
backend/interfaces/websocket/handler.py       # 调用 dialog_service
```

### 整合方案

#### 3.1 创建 Snapshot 构建器
```python
# backend/domain/utils/snapshot_builder.py
from typing import Optional, Dict, Any, List
from backend.domain.models.dialog.session import DialogSession

class SnapshotBuilder:
    """对话快照构建器，统一处理快照构建逻辑"""
    
    @staticmethod
    def build_from_session(
        session: DialogSession,
        status: str = "idle",
        streaming_msg: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """从 DialogSession 构建快照"""
        # 合并 manager.py 和 dialog_service.py 中的构建逻辑
        messages = SnapshotBuilder._convert_messages(session)
        
        return {
            "id": session.dialog_id,
            "title": session.metadata.title or "New Dialog",
            "status": status,
            "messages": messages,
            "streaming_message": streaming_msg,
            "metadata": SnapshotBuilder._build_metadata(session),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "selected_model_id": getattr(session, 'selected_model_id', None),
        }
    
    @staticmethod
    def _convert_messages(session: DialogSession) -> List[Dict]:
        """转换消息格式"""
        messages = []
        for msg in session.history.messages:
            role = SnapshotBuilder._get_message_role(msg)
            msg_id = getattr(msg, 'msg_id', '') or str(id(msg))[:12]
            
            msg_dict = {
                "id": msg_id,
                "role": role,
                "content": msg.content,
                "content_type": "text",
                "status": "completed",
                "timestamp": session.updated_at.isoformat(),
            }
            
            # 添加模型信息
            msg_metadata = getattr(msg, 'additional_kwargs', {}) or {}
            if msg_metadata.get('model'):
                msg_dict["model"] = msg_metadata['model']
            if msg_metadata.get('provider'):
                msg_dict["provider"] = msg_metadata['provider']
            if msg_metadata.get('reasoning_content'):
                msg_dict["reasoning_content"] = msg_metadata['reasoning_content']
                
            messages.append(msg_dict)
        return messages
    
    @staticmethod
    def _get_message_role(msg) -> str:
        """获取消息角色"""
        from langchain_core.messages import HumanMessage, AIMessage
        if isinstance(msg, HumanMessage):
            return "user"
        elif isinstance(msg, AIMessage):
            return "assistant"
        else:
            return "tool"
    
    @staticmethod
    def _build_metadata(session: DialogSession) -> Dict[str, Any]:
        """构建元数据"""
        import os
        from backend.infrastructure.services.provider_manager import ProviderManager
        
        try:
            pm = ProviderManager()
            model_config = pm.get_model_config()
            current_model = model_config.model
        except Exception:
            current_model = os.getenv("MODEL_ID", "unknown")
        
        return {
            "model": current_model,
            "agent_name": "hana",
            "tool_calls_count": session.metadata.tool_calls_count,
            "total_tokens": session.metadata.token_count,
        }


# 保持向后兼容的函数接口
def build_dialog_snapshot(
    dialog_id: str,
    session_manager,
    status: str = "idle",
    streaming_msg: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """向后兼容的函数"""
    session = session_manager.get_session_sync(dialog_id)
    if not session:
        return None
    return SnapshotBuilder.build_from_session(session, status, streaming_msg)
```

---

## 4. Mixin 类整合优化

### 当前问题
Mixin 类分散在多个文件中，部分功能可以进一步抽象。

### 现有 Mixin 分布
```
backend/domain/models/shared/mixins.py
  - TimestampMixin
  - DialogRefMixin
  - MetadataMixin
  - IdMixin

backend/infrastructure/runtime/mixins.py
  - ManagerLifecycleMixin
  - EventMixin
  - MemoryMixin
  - SkillMixin
  - ToolMixin
  - LifecycleMixin
  - HitlMixin
  - DialogMixin

backend/infrastructure/runtime/services/logging_mixin.py
  - DeepLoggingMixin (195行)
  - UnifiedLoggingMixin
```

### 整合方案

#### 4.1 创建基础 Mixin 模块
```python
# backend/domain/models/shared/base_mixins.py

class ComparableMixin:
    """提供对象比较功能的 Mixin"""
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._get_comparison_key() == other._get_comparison_key()
    
    def __hash__(self) -> int:
        return hash(self._get_comparison_key())
    
    def _get_comparison_key(self):
        """子类需要重写此方法返回用于比较的关键字"""
        raise NotImplementedError


class SerializableMixin:
    """提供序列化功能的 Mixin"""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items() 
            if not k.startswith('_')
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建实例"""
        return cls(**data)


class ValidatableMixin:
    """提供验证功能的 Mixin"""
    
    def validate(self) -> list[str]:
        """
        验证对象状态
        
        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []
        for name in dir(self):
            if name.startswith('_validate_'):
                error = getattr(self, name)()
                if error:
                    errors.append(error)
        return errors
```

#### 4.2 整合 Logging Mixin
```python
# backend/infrastructure/logging/mixins.py

from backend.infrastructure.logging import get_logger

class LoggerMixin:
    """
    自动为类添加 logger 属性的 Mixin
    
    使用方式：
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("Doing something")
    """
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._logger_name = cls.__module__ + '.' + cls.__name__
    
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self._logger_name)
        return self._logger
```

#### 4.3 使用 LoggerMixin 简化代码
```python
# 重构前
from backend.infrastructure.logging import get_logger
logger = get_logger(__name__)

class MyService:
    def do_something(self):
        logger.info("Doing something")

# 重构后
from backend.infrastructure.logging.mixins import LoggerMixin

class MyService(LoggerMixin):
    def do_something(self):
        self.logger.info("Doing something")
```

---

## 5. 异常类整合

### 当前问题
异常类分散在多个文件中，部分异常定义重复。

### 现有异常分布
```
backend/domain/models/dialog/exceptions.py
  - SessionError
  - SessionNotFoundError
  - SessionAlreadyExistsError
  - StreamingStateError
  - InvalidTransitionError
  - SessionFullError

backend/application/services/skill.py
  - SkillNotFoundError

backend/application/services/dialog.py
  - DialogNotFoundError

backend/infrastructure/queue/base.py
  - QueueFull

backend/infrastructure/tools/toolkit.py
  - ToolDefinitionError
```

### 整合方案

#### 5.1 创建统一异常层次结构
```python
# backend/domain/exceptions/base.py

class DomainError(Exception):
    """领域层基础异常"""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}


class NotFoundError(DomainError):
    """资源未找到"""
    pass


class AlreadyExistsError(DomainError):
    """资源已存在"""
    pass


class StateError(DomainError):
    """状态错误"""
    pass


class ValidationError(DomainError):
    """验证错误"""
    pass


class LimitExceededError(DomainError):
    """超出限制"""
    pass
```

#### 5.2 具体异常继承基础异常
```python
# backend/domain/exceptions/dialog.py
from .base import NotFoundError, AlreadyExistsError, StateError, LimitExceededError

class SessionNotFoundError(NotFoundError):
    """对话会话未找到"""
    def __init__(self, dialog_id: str):
        super().__init__(
            message=f"Dialog session not found: {dialog_id}",
            code="SESSION_NOT_FOUND",
            details={"dialog_id": dialog_id}
        )


class SessionAlreadyExistsError(AlreadyExistsError):
    """对话会话已存在"""
    def __init__(self, dialog_id: str):
        super().__init__(
            message=f"Dialog session already exists: {dialog_id}",
            code="SESSION_ALREADY_EXISTS",
            details={"dialog_id": dialog_id}
        )


class InvalidTransitionError(StateError):
    """无效的状态转换"""
    def __init__(self, dialog_id: str, from_state: str, to_state: str):
        super().__init__(
            message=f"Invalid transition from {from_state} to {to_state} for dialog {dialog_id}",
            code="INVALID_TRANSITION",
            details={
                "dialog_id": dialog_id,
                "from_state": from_state,
                "to_state": to_state
            }
        )


class SessionFullError(LimitExceededError):
    """会话数量超出限制"""
    def __init__(self, max_sessions: int):
        super().__init__(
            message=f"Maximum number of sessions ({max_sessions}) reached",
            code="SESSION_LIMIT_REACHED",
            details={"max_sessions": max_sessions}
        )
```

#### 5.3 统一异常处理
```python
# backend/interfaces/http/error_handlers.py
from backend.domain.exceptions.base import DomainError

async def domain_error_handler(request, exc: DomainError):
    """统一处理领域异常"""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
```

---

## 6. 实施计划

### Phase 1: Logger 整合 (优先级: 高)
```
任务:
1. 创建 backend/infrastructure/logging/factory.py
2. 创建 backend/infrastructure/logging/mixins.py
3. 批量替换 22 个文件中的 logger 定义
4. 测试日志输出是否正常
```

### Phase 2: 工具函数整合 (优先级: 高)
```
任务:
1. 创建 backend/domain/utils/time_utils.py
2. 迁移 timestamp_ms, iso_timestamp 到工具模块
3. 更新所有使用位置
4. 更新 dialog_service.py 使用工具模块
```

### Phase 3: Snapshot 构建整合 (优先级: 中)
```
任务:
1. 创建 backend/domain/utils/snapshot_builder.py
2. 合并 manager.py 和 dialog_service.py 的构建逻辑
3. 创建向后兼容的函数接口
4. 测试所有快照构建场景
```

### Phase 4: Mixin 优化 (优先级: 中)
```
任务:
1. 创建 backend/domain/models/shared/base_mixins.py
2. 优化现有 Mixin 类继承关系
3. 使用 LoggerMixin 简化需要 logger 的类
4. 保持向后兼容
```

### Phase 5: 异常整合 (优先级: 低)
```
任务:
1. 创建 backend/domain/exceptions/ 目录结构
2. 创建基础异常类
3. 重构具体异常继承基础异常
4. 创建统一异常处理器
```

---

## 7. 代码统计

### 重构前重复代码统计

| 类型 | 位置数 | 影响行数 | 优先级 |
|------|--------|----------|--------|
| Logger 定义 | 22 处 | ~66 行 | 高 |
| 时间戳函数使用 | 17 处 | ~17 行 | 高 |
| Snapshot 构建 | 2 处实现 + 6 处使用 | ~200 行 | 中 |
| Mixin 类 | 12 个类分散 | ~400 行 | 中 |
| 异常定义 | 9 个类分散 | ~80 行 | 低 |

### 重构后预期

| 类型 | 实现位置 | 代码行数 | 减少重复 |
|------|----------|----------|----------|
| Logger | 1 个工厂 | ~50 行 | 消除 22 处重复 |
| 时间工具 | 1 个工具类 | ~30 行 | 统一 17 处使用 |
| Snapshot | 1 个构建器 | ~80 行 | 统一 2 处实现 |
| Mixin | 3 个基础 Mixin | ~60 行 | 简化继承关系 |
| 异常 | 5 个基础 + 具体异常 | ~100 行 | 统一错误处理 |

**总计**: 消除约 400 行重复代码，提升可维护性。
