"""Base Mixins - 基础 Mixin 类

提供通用的基础 Mixin 功能，其他 Mixin 可以继承这些基类获得标准行为。
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T", bound="ComparableMixin")


class ComparableMixin:
    """可比较 Mixin

    提供标准的 __eq__ 和 __hash__ 实现，基于对象的 id 字段。

    Example:
        class MyModel(ComparableMixin):
            def __init__(self, id: str):
                self.id = id

        m1 = MyModel("a")
        m2 = MyModel("a")
        assert m1 == m2
        assert hash(m1) == hash(m2)
    """

    def __eq__(self, other: object) -> bool:
        """基于 id 字段的相等性比较"""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return getattr(self, "id", None) == getattr(other, "id", None)

    def __hash__(self) -> int:
        """基于 id 字段的哈希值"""
        return hash(getattr(self, "id", id(self)))


class SerializableMixin(ABC):
    """可序列化 Mixin

    提供标准的 to_dict() 和 from_dict() 接口。
    子类需要实现 _to_dict_impl() 和 _from_dict_impl()。

    Example:
        class MyModel(SerializableMixin):
            def __init__(self, name: str):
                self.name = name

            def _to_dict_impl(self) -> Dict[str, Any]:
                return {"name": self.name}

            @classmethod
            def _from_dict_impl(cls, data: Dict[str, Any]) -> "MyModel":
                return cls(name=data["name"])
    """

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = self._to_dict_impl()
        # 自动添加 id 字段（如果有）
        if hasattr(self, "id") and "id" not in result:
            result["id"] = self.id
        return result

    @abstractmethod
    def _to_dict_impl(self) -> dict[str, Any]:
        """子类实现：转换为字典的具体逻辑"""
        raise NotImplementedError

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """从字典创建实例"""
        return cls._from_dict_impl(data)

    @classmethod
    @abstractmethod
    def _from_dict_impl(cls: type[T], data: dict[str, Any]) -> T:
        """子类实现：从字典创建实例的具体逻辑"""
        raise NotImplementedError


class ValidatableMixin(ABC):
    """可验证 Mixin

    提供标准的 validate() 接口。
    子类需要实现 _validate_impl()。

    Example:
        class MyModel(ValidatableMixin):
            def __init__(self, value: int):
                self.value = value

            def _validate_impl(self) -> tuple[bool, str]:
                if self.value < 0:
                    return False, "value must be >= 0"
                return True, ""
    """

    def validate(self) -> tuple[bool, str]:
        """验证对象有效性

        Returns:
            (is_valid, error_message) 元组
        """
        return self._validate_impl()

    def is_valid(self) -> bool:
        """是否有效"""
        is_valid, _ = self.validate()
        return is_valid

    def get_validation_error(self) -> str:
        """获取验证错误信息"""
        _, error = self.validate()
        return error

    @abstractmethod
    def _validate_impl(self) -> tuple[bool, str]:
        """子类实现：验证逻辑

        Returns:
            (is_valid, error_message) 元组
        """
        raise NotImplementedError


class LoggerMixin:
    """日志 Mixin（可选，替代外部 logger 定义）

    为类提供自动 logger 属性。需要配合 LoggerFactory 使用。

    Example:
        from backend.infrastructure.logging import LoggerMixin

        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("Doing something")
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._logger_name = cls.__module__ + "." + cls.__name__

    @property
    def logger(self):
        """获取 logger 实例（延迟初始化）"""
        if not hasattr(self, "_logger"):
            from backend.infrastructure.logging import get_logger

            self._logger = get_logger(self._logger_name)
        return self._logger


__all__ = [
    "ComparableMixin",
    "SerializableMixin",
    "ValidatableMixin",
    "LoggerMixin",
]
