"""
Domain Repositories - 领域仓库接口

定义数据访问的抽象契约，遵循依赖倒置原则。
"""

from .dialog_repository import IDialogRepository
from .skill_repository import ISkillRepository

__all__ = [
    "IDialogRepository",
    "ISkillRepository",
]
