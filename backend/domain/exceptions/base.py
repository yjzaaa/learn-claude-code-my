"""Domain Exceptions - 领域层异常基类

提供统一的异常层次结构，消除代码中分散的异常定义。
"""

from typing import Optional, Dict, Any


class DomainError(Exception):
    """领域错误基类

    所有领域异常的基类，提供统一的错误码、消息和详情。

    Attributes:
        code: 错误码，用于程序识别错误类型
        message: 错误消息，用于人类阅读
        details: 额外详情字典

    Example:
        raise DomainError(
            code="DIALOG_NOT_FOUND",
            message="Dialog not found",
            details={"dialog_id": "dlg_123"}
        )
    """

    code: str = "DOMAIN_ERROR"
    message: str = "Domain error occurred"
    status_code: int = 500

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} - {self.details}"
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class NotFoundError(DomainError):
    """资源不存在错误"""

    code = "NOT_FOUND"
    message = "Resource not found"
    status_code = 404

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: Optional[str] = None,
        **kwargs
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} '{resource_id}' not found"

        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id
        details.update(kwargs)

        super().__init__(message=message, details=details)


class AlreadyExistsError(DomainError):
    """资源已存在错误"""

    code = "ALREADY_EXISTS"
    message = "Resource already exists"
    status_code = 409

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: Optional[str] = None,
        **kwargs
    ):
        message = f"{resource_type} already exists"
        if resource_id:
            message = f"{resource_type} '{resource_id}' already exists"

        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id
        details.update(kwargs)

        super().__init__(message=message, details=details)


class StateError(DomainError):
    """状态错误"""

    code = "INVALID_STATE"
    message = "Invalid state"
    status_code = 400

    def __init__(
        self,
        current_state: Optional[str] = None,
        expected_state: Optional[str] = None,
        **kwargs
    ):
        message = "Invalid state"
        if current_state and expected_state:
            message = f"Expected state '{expected_state}', got '{current_state}'"
        elif current_state:
            message = f"Invalid current state: '{current_state}'"

        details = {}
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state
        details.update(kwargs)

        super().__init__(message=message, details=details)


class ValidationError(DomainError):
    """验证错误"""

    code = "VALIDATION_ERROR"
    message = "Validation failed"
    status_code = 400

    def __init__(
        self,
        field: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ):
        message = "Validation failed"
        if field and reason:
            message = f"Field '{field}': {reason}"
        elif field:
            message = f"Field '{field}' is invalid"
        elif reason:
            message = reason

        details = {}
        if field:
            details["field"] = field
        if reason:
            details["reason"] = reason
        details.update(kwargs)

        super().__init__(message=message, details=details)


class LimitExceededError(DomainError):
    """限制超出错误"""

    code = "LIMIT_EXCEEDED"
    message = "Limit exceeded"
    status_code = 429

    def __init__(
        self,
        limit_type: str = "Resource",
        current: Optional[int] = None,
        maximum: Optional[int] = None,
        **kwargs
    ):
        message = f"{limit_type} limit exceeded"
        if current and maximum:
            message = f"{limit_type} limit exceeded: {current}/{maximum}"

        details: dict[str, Any] = {"limit_type": limit_type}
        if current is not None:
            details["current"] = current
        if maximum is not None:
            details["maximum"] = maximum
        details.update(kwargs)

        super().__init__(message=message, details=details)


class PermissionError(DomainError):
    """权限错误"""

    code = "PERMISSION_DENIED"
    message = "Permission denied"
    status_code = 403


class ExternalServiceError(DomainError):
    """外部服务错误"""

    code = "EXTERNAL_SERVICE_ERROR"
    message = "External service error"
    status_code = 502

    def __init__(
        self,
        service: str = "External service",
        original_error: Optional[str] = None,
        **kwargs
    ):
        message = f"{service} error"
        if original_error:
            message = f"{service} error: {original_error}"

        details = {"service": service}
        if original_error:
            details["original_error"] = original_error
        details.update(kwargs)

        super().__init__(message=message, details=details)


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
