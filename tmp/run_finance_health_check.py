#!/usr/bin/env python3
"""
运行 Finance Skill 健康检查脚本并捕获输出
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, '/')

# 导入并运行健康检查
from skills.finance.scripts.health_check import run_health_check

# 运行测试
result = run_health_check(stream_output=True)

# 输出最终结果
print("\n" + "="*60)
print("JSON 结果:")
print("="*60)
import json
print(json.dumps(result, ensure_ascii=False, indent=2))
