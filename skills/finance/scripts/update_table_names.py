#!/usr/bin/env python3
"""
批量更新finance技能中的表名和字段名
将旧表名替换为新表名，将旧字段名替换为新字段名
"""

import os
import re
from pathlib import Path

# 定义要替换的模式
REPLACEMENTS = {
    # 表名替换
    'cost_database': 'cost_database',
    '"cost_database"': 'cost_database',
    "'cost_database'": 'cost_database',
    'rate_table': 'rate_table',
    '"rate_table"': 'rate_table',
    "'rate_table'": 'rate_table',
    
    # 字段名替换（注意：需要区分大小写，因为数据库是小写字段）
    'amount': 'amount',
    'amount': 'amount',
    'rate_no': 'rate_no',
    'rate_no': 'rate_no',
    'rate_no': 'rate_no',  # 原大写
    'rate_no': 'rate_no',  # 可能的大小写变体
    'year': 'year',
    'year': 'year',
    'month': 'month',
    'month': 'month',
    'scenario': 'scenario',
    'scenario': 'scenario',
    'function': 'function',
    'function': 'function',
    'key': 'key',
    'key': 'key',
    'account': 'account',
    'account': 'account',
    'bl': 'bl',
    'bl': 'bl',
    'cc': 'cc',
    'cc': 'cc',
}

def update_file(file_path):
    """更新单个文件中的内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 执行替换
        for old_str, new_str in REPLACEMENTS.items():
            content = content.replace(old_str, new_str)
        
        # 检查是否发生变化
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已更新: {file_path}")
            return True
        else:
            print(f" 未变化: {file_path}")
            return False
            
    except Exception as e:
        print(f"✗ 错误处理 {file_path}: {e}")
        return False

def main():
    # 设置工作目录
    base_dir = Path(__file__).parent.parent
    print(f"工作目录: {base_dir}")
    
    # 要处理的文件扩展名
    extensions = ['.md', '.py', '.sql', '.txt']
    
    updated_count = 0
    
    # 递归遍历所有文件
    for ext in extensions:
        for file_path in base_dir.rglob(f'*{ext}'):
            if update_file(file_path):
                updated_count += 1
    
    print(f"\n总计更新了 {updated_count} 个文件")
    
    # 显示当前表结构
    print("\n当前数据库表结构:")
    print("-" * 50)
    print("表名: cost_database, rate_table")
    print("字段名: 全部小写 (year, month, scenario, function, amount, key, account, bl, cc, rate_no)")
    print("-" * 50)

if __name__ == '__main__':
    main()