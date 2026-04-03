#!/usr/bin/env python3
"""
执行 Finance Skill 体温测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/skills/finance/scripts')
sys.path.insert(0, '/skills/finance')
sys.path.insert(0, '/')

# 导入并执行测试
from health_check import run_health_check

if __name__ == "__main__":
    result = run_health_check(stream_output=True)
    print("\n" + "="*60)
    print("JSON 结果输出:")
    print("="*60)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
