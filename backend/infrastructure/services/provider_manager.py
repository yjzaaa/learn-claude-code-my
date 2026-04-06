"""
Provider Manager - Provider 管理器

**已重构**: 代码已迁移到 provider/ 子模块。
此文件保留以维持向后兼容的导入路径。

新位置:
- backend/infrastructure/services/provider/manager.py - 主管理器
- backend/infrastructure/services/provider/discovery.py - 模型发现
- backend/infrastructure/services/provider/factory.py - 实例创建
"""

# 向后兼容导入 - 所有实现已迁移到子模块
from backend.infrastructure.services.provider import (
    ModelConfig,
    ProviderManager,
    create_model_instance,
    discover_available_models,
)

__all__ = [
    "ProviderManager",
    "ModelConfig",
    "discover_available_models",
    "create_model_instance",
]
