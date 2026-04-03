"""File Storage - 文件系统状态存储实现

实现 IStateStorage 接口，提供基于文件系统的状态持久化。
"""

import json
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel

from core.infra.interfaces import IStateStorage


class FileStorage(IStateStorage):
    """
    文件系统存储实现

    使用 JSON 文件存储 Pydantic BaseModel 数据。
    """

    def __init__(self, base_dir: Path | str = ".workspace/state"):
        """
        初始化文件存储

        Args:
            base_dir: 存储目录路径
        """
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """获取键对应的文件路径"""
        # 将 key 中的路径分隔符替换为安全字符
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self._base_dir / f"{safe_key}.json"

    async def save(self, key: str, data: BaseModel) -> None:
        """
        保存状态

        Args:
            key: 状态键
            data: Pydantic BaseModel 数据
        """
        file_path = self._get_file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)
            logger.debug(f"[FileStorage] Saved {key} to {file_path}")
        except Exception as e:
            logger.error(f"[FileStorage] Failed to save {key}: {e}")
            raise

    async def load(self, key: str, model_cls: type[BaseModel]) -> Optional[BaseModel]:
        """
        加载状态

        Args:
            key: 状态键
            model_cls: Pydantic 模型类

        Returns:
            BaseModel 实例或 None
        """
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            model = model_cls.model_validate(data)
            logger.debug(f"[FileStorage] Loaded {key} from {file_path}")
            return model
        except Exception as e:
            logger.error(f"[FileStorage] Failed to load {key}: {e}")
            return None

    async def delete(self, key: str) -> None:
        """
        删除状态

        Args:
            key: 状态键
        """
        file_path = self._get_file_path(key)

        if file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"[FileStorage] Deleted {key}")
            except Exception as e:
                logger.error(f"[FileStorage] Failed to delete {key}: {e}")
                raise

    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 状态键

        Returns:
            是否存在
        """
        file_path = self._get_file_path(key)
        return file_path.exists()


__all__ = ["FileStorage"]
