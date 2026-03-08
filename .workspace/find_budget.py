#!/usr/bin/env python3
import os
import re

def find_budget_files():
    """查找预算相关文件"""
    budget_keywords = [
        'budget', '预算', 'finance', '财务', 'FY26', '财年',
        'HR', 'human resource', '人力资源', 'salary', '薪酬',
        'cost', '费用', 'forecast', '预测', 'plan', '计划'
    ]
    
    found_files = []
    
    # 遍历当前目录
    for root, dirs, files in os.walk('.'):
        for file in files:
            file_lower = file.lower()
            # 检查文件名是否包含预算关键词
            for keyword in budget_keywords:
                if keyword.lower() in file_lower:
                    found_files.append(os.path.join(root, file))
                    break
    
    return found_files

def search_hr_budget_in_files(files):
    """在文件中搜索HR预算信息"""
    hr_budget_patterns = [
        r'HR.*预算.*?(\d[\d,\.]+)',
        r'人力资源.*费用.*?(\d[\d,\.]+)',
        r'FY26.*HR.*?(\d[\d,\.]+)',
        r'26财年.*HR.*?(\d[\d,\.]+)',
        r'personnel.*cost.*?(\d[\d,\.]+)',
        r'薪酬.*预算.*?(\d[\d,\.]+)',
        r'salary.*budget.*?(\d[\d,\.]+)'
    ]
    
    results = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in hr_budget_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    results.append({
                        'file': file_path,
                        'pattern': pattern,
                        'matches': matches
                    })
        except Exception as e:
            continue
    
    return results

if __name__ == "__main__":
    print("正在查找预算相关文件...")
    budget_files = find_budget_files()
    
    print(f"找到 {len(budget_files)} 个预算相关文件:")
    for file in budget_files:
        print(f"  - {file}")
    
    print("\n正在搜索HR预算信息...")
    hr_budget_results = search_hr_budget_in_files(budget_files)
    
    if hr_budget_results:
        print("\n找到HR预算信息:")
        for result in hr_budget_results:
            print(f"\n文件: {result['file']}")
            print(f"匹配模式: {result['pattern']}")
            print(f"匹配结果: {result['matches']}")
    else:
        print("\n未找到HR预算信息")