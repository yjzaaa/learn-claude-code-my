"""Domain Exceptions - 领域层异常

提供统一的异常层次结构。
"""

from .base import (
    DomainError,
    NotFoundError,
    AlreadyExistsError,
    StateError,
    ValidationError,
    LimitExceededError,
    PermissionError,
    ExternalServiceError,
)

__all__ = [
    "DomainError",
    "NotFoundError",
    "AlreadyExistsError",
    "StateError",
    "ValidationError",
    "LimitExceededError",
    "PermissionError",
    "ExternalServiceError",
]
