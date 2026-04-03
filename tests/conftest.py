"""
Pytest configuration - 测试配置

自动添加项目根目录到 Python 路径
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 打印路径用于调试
print(f"[conftest] Added to path: {PROJECT_ROOT}")
