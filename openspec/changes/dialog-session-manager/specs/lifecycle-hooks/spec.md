# Lifecycle Hooks 规范

## 设计目标

提供扩展点，允许在会话生命周期的关键节点插入自定义逻辑，如：
- 日志记录
- 指标统计
- 权限检查
- 消息拦截/转换
- 外部通知

## Hook 类型

```python
from typing import Callable, Awaitable, Protocol
from dataclasses import dataclass

HookResult = dict | None  # 返回 None 表示继续，返回 dict 可修改上下文

class LifecycleHook(Protocol):
    """生命周期钩子协议"""
    priority: int = 100  # 优先级，数字越小越先执行

    async def before_transition(
        self,
        dialog_id: str,
        from_status: SessionStatus,
        to_status: SessionStatus,
        context: dict
    ) -> HookResult:
        """状态转换前触发，可阻止转换或修改上下文"""
        ...

    async def after_transition(
        self,
        dialog_id: str,
        from_status: SessionStatus,
        to_status: SessionStatus,
        context: dict
    ) -> None:
        """状态转换后触发"""
        ...

class MessageHook(Protocol):
    """消息钩子协议"""
    priority: int = 100

    async def before_message_add(
        self,
        dialog_id: str,
        message: BaseMessage,
        context: dict
    ) -> BaseMessage | None:
        """
        消息添加前触发

        Returns:
            修改后的消息，或 None 表示阻止添加
        """
        ...

    async def after_message_add(
        self,
        dialog_id: str,
        message: BaseMessage,
        context: dict
    ) -> None:
        """消息添加后触发"""
        ...
```

## 钩子注册

```python
@dataclass
class HookRegistry:
    """钩子注册表"""
    lifecycle_hooks: list[LifecycleHook] = field(default_factory=list)
    message_hooks: list[MessageHook] = field(default_factory=list)

    def register_lifecycle(self, hook: LifecycleHook) -> None:
        """注册生命周期钩子"""
        self.lifecycle_hooks.append(hook)
        self.lifecycle_hooks.sort(key=lambda h: h.priority)

    def register_message(self, hook: MessageHook) -> None:
        """注册消息钩子"""
        self.message_hooks.append(hook)
        self.message_hooks.sort(key=lambda h: h.priority)

    def unregister(self, hook: LifecycleHook | MessageHook) -> None:
        """注销钩子"""
        if hook in self.lifecycle_hooks:
            self.lifecycle_hooks.remove(hook)
        if hook in self.message_hooks:
            self.message_hooks.remove(hook)
```

## 预定义钩子

### 1. 日志钩子

```python
class LoggingHook(LifecycleHook, MessageHook):
    """记录所有状态转换和消息操作"""
    priority = 10  # 高优先级，先执行

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def after_transition(self, dialog_id, from_status, to_status, context):
        self.logger.info(
            "Session %s: %s -> %s",
            dialog_id, from_status, to_status
        )

    async def after_message_add(self, dialog_id, message, context):
        self.logger.debug(
            "Session %s: added %s message (id=%s)",
            dialog_id, message.type, message.id
        )
```

### 2. 指标统计钩子

```python
class MetricsHook(LifecycleHook, MessageHook):
    """收集会话指标"""
    priority = 20

    def __init__(self, metrics_client):
        self.metrics = metrics_client

    async def after_transition(self, dialog_id, from_status, to_status, context):
        # 记录状态分布
        self.metrics.increment(f"session.status.{to_status}")

        # 记录流式耗时
        if from_status == SessionStatus.STREAMING:
            duration = context.get("streaming_duration_ms", 0)
            self.metrics.timing("session.streaming_duration", duration)

    async def after_message_add(self, dialog_id, message, context):
        if isinstance(message, AIMessage):
            token_count = context.get("token_count", 0)
            self.metrics.histogram("message.ai_tokens", token_count)
```

### 3. 上下文压缩钩子

```python
class ContextCompressionHook(MessageHook):
    """
    在添加上下文前检查 token 数，触发压缩

    优先级较低，在其他钩子处理完成后执行
    """
    priority = 200

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens

    async def before_message_add(
        self,
        dialog_id: str,
        message: BaseMessage,
        context: dict
    ) -> BaseMessage | None:
        # 检查添加这条消息后是否超限
        current_tokens = context.get("current_tokens", 0)
        msg_tokens = estimate_tokens(message)

        if current_tokens + msg_tokens > self.max_tokens:
            # 触发压缩（通过 context 通知上层）
            context["needs_compression"] = True
            context["excess_tokens"] = current_tokens + msg_tokens - self.max_tokens

        return message  # 继续添加
```

### 4. 审计日志钩子

```python
class AuditLogHook(LifecycleHook):
    """
    记录完整的会话生命周期用于审计

    写入独立的审计日志文件或外部系统
    """
    priority = 5  # 最高优先级

    async def after_transition(self, dialog_id, from_status, to_status, context):
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "dialog_id": dialog_id,
            "event": "status_change",
            "from": from_status,
            "to": to_status,
            "user_id": context.get("user_id"),
            "ip": context.get("client_ip"),
        }
        await self.write_audit_log(audit_entry)
```

## 使用示例

```python
# 初始化 SessionManager 时注册钩子
manager = DialogSessionManager(config)

# 添加日志
manager.hooks.register_lifecycle(LoggingHook(logger))

# 添加指标
manager.hooks.register_lifecycle(MetricsHook(metrics_client))

# 添加自定义钩子
class MyCustomHook(LifecycleHook):
    async def before_transition(self, dialog_id, from_status, to_status, context):
        # 在特定状态转换时发送通知
        if to_status == SessionStatus.ERROR:
            await send_alert(f"Session {dialog_id} encountered error")
        return None  # 继续转换

manager.hooks.register_lifecycle(MyCustomHook())
```

## 执行流程

```
状态转换请求
    │
    ▼
┌─────────────────────────────────────┐
│ 按优先级排序执行 before_transition  │
│                                     │
│ 如果有钩子返回 None（阻止）：       │
│   停止转换，触发阻止事件            │
│                                     │
│ 如果有钩子修改 context：            │
│   合并修改后的 context              │
└─────────────────────────────────────┘
    │
    ▼
执行实际状态转换
    │
    ▼
┌─────────────────────────────────────┐
│ 按优先级排序执行 after_transition   │
└─────────────────────────────────────┘
    │
    ▼
触发事件通知（EventCoordinator）
```

## 错误处理

钩子执行中的异常不应影响主流程：

```python
async def _run_hooks_safe(self, hooks: list[Hook], method: str, *args, **kwargs):
    """安全执行钩子，捕获异常"""
    for hook in hooks:
        try:
            handler = getattr(hook, method)
            result = await handler(*args, **kwargs)
            if result is None:
                continue  # 钩子阻止了操作
            if isinstance(result, dict):
                kwargs["context"].update(result)
        except Exception as e:
            self.logger.error(f"Hook {hook.__class__.__name__}.{method} failed: {e}")
            # 继续执行其他钩子
```
