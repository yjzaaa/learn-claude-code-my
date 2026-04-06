"""Backward-compatible wrapper for allocation SQL generation."""

import sys
from pathlib import Path

# 添加当前目录到模块搜索路径
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from allocation_utils import ALLOC_TEMPLATE, generate_alloc_sql

__all__ = ["ALLOC_TEMPLATE", "generate_alloc_sql"]
