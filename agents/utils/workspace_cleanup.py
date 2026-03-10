"""工作区临时目录清理工具。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from loguru import logger


def _env_enabled(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def clear_workspace_dir(workdir: Path) -> tuple[bool, int]:
    """清空 ``.workspace`` 目录内容（保留目录本身）。"""

    if not _env_enabled("AUTO_CLEAR_WORKSPACE_ON_ROUND_END", True):
        return False, 0

    target = (workdir / ".workspace").resolve()
    workdir_resolved = workdir.resolve()
    if not target.is_relative_to(workdir_resolved):
        logger.error(f"[workspace_cleanup] 拒绝清理越界路径: {target}")
        return False, 0

    target.mkdir(parents=True, exist_ok=True)
    removed = 0

    for child in list(target.iterdir()):
        try:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
            removed += 1
        except Exception as e:
            logger.error(f"[workspace_cleanup] 删除失败: {child} -> {e}")

    return True, removed
