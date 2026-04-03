"""Dependency Injection Container - 依赖注入容器

简易 DI 容器实现，管理各层接口实例的生命周期。
遵循依赖倒置原则：上层依赖下层接口，下层通过容器注册实现。

使用示例:
    container = Container()
    container.register(IEventBus, EventBus(), scope="singleton")
    container.register(IDialogManager, lambda: DialogManager(...), scope="factory")

    bridge = container.resolve(IAgentRuntimeBridge)
"""

from typing import TypeVar, Type, Callable, Any, Optional
from loguru import logger

T = TypeVar("T")


class Container:
    """
    简易依赖注入容器

    支持两种作用域：
    - singleton: 单例，只创建一次
    - factory: 工厂，每次解析创建新实例
    """

    def __init__(self):
        # 注册表: 接口类型 -> (工厂函数, 作用域)
        self._registry: dict[Type[Any], tuple[Callable[[], Any], str]] = {}
        # 单例缓存: 接口类型 -> 实例
        self._singletons: dict[Type[Any], Any] = {}

    def register(
        self,
        interface: Type[T],
        factory: Callable[[], T] | T,
        scope: str = "factory"
    ) -> None:
        """
        注册接口实现

        Args:
            interface: 接口类型（如 IEventBus）
            factory: 工厂函数或实例
            scope: 作用域（"singleton" | "factory"）

        Raises:
            ValueError: 如果作用域无效
        """
        if scope not in ("singleton", "factory"):
            raise ValueError(f"Invalid scope: {scope}. Use 'singleton' or 'factory'")

        # 如果是实例而不是工厂函数，包装成工厂
        if not callable(factory):
            instance = factory
            factory = lambda: instance

        self._registry[interface] = (factory, scope)
        logger.debug(f"[Container] Registered {interface.__name__} as {scope}")

    def resolve(self, interface: Type[T]) -> T:
        """
        解析接口实例

        Args:
            interface: 接口类型

        Returns:
            接口实现实例

        Raises:
            KeyError: 如果接口未注册
        """
        if interface not in self._registry:
            raise KeyError(f"Interface not registered: {interface.__name__}")

        factory, scope = self._registry[interface]

        if scope == "singleton":
            if interface not in self._singletons:
                self._singletons[interface] = factory()
                logger.debug(f"[Container] Created singleton {interface.__name__}")
            return self._singletons[interface]
        else:
            logger.debug(f"[Container] Created factory instance {interface.__name__}")
            return factory()

    def is_registered(self, interface: Type[T]) -> bool:
        """检查接口是否已注册"""
        return interface in self._registry

    def clear(self) -> None:
        """清空容器（主要用于测试）"""
        self._registry.clear()
        self._singletons.clear()


def create_default_container() -> Container:
    """
    创建默认配置的容器

    注册所有层的默认实现：
    - 基础设施层: IEventBus, IStateStorage
    - 能力层: IDialogManager, IToolManager, ISkillManager, IMemoryManager
    - 运行时层: IAgentRuntimeFactory
    - 桥接层: IAgentRuntimeBridge

    Returns:
        配置好的容器实例
    """
    container = Container()

    # 基础设施层（单例）
    from core.infra.interfaces import IEventBus, IStateStorage
    from runtime.event_bus import EventBus
    from core.infra.file_storage import FileStorage

    container.register(IEventBus, EventBus(), scope="singleton")
    container.register(IStateStorage, FileStorage(), scope="singleton")

    # 能力层（工厂 - 每次创建新实例）
    # 这些将在后续任务中实现，暂时跳过
    # container.register(IDialogManager, lambda: DialogManager(...), scope="factory")
    # container.register(IToolManager, lambda: ToolManager(...), scope="factory")

    # 运行时层（工厂）
    # container.register(IAgentRuntimeFactory, AgentRuntimeFactory(), scope="singleton")

    # 桥接层（单例）
    # container.register(IAgentRuntimeBridge, lambda: AgentRuntimeBridge(...), scope="singleton")

    logger.info("[Container] Default container created")
    return container


# 全局容器实例（懒加载）
_default_container: Optional[Container] = None


def get_container() -> Container:
    """获取全局默认容器"""
    global _default_container
    if _default_container is None:
        _default_container = create_default_container()
    return _default_container


def reset_container() -> None:
    """重置全局容器（主要用于测试）"""
    global _default_container
    _default_container = None


__all__ = [
    "Container",
    "create_default_container",
    "get_container",
    "reset_container",
]
