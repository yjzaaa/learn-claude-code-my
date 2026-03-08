import os
import re

def search_finance_files():
    print("Searching for finance-related files...")
    
    # 搜索关键词
    keywords = ['budget', '采购', '采购预算', 'finance', '财务', '25财年', '26财年', '实际数', '预算费用']
    
    for root, dirs, files in os.walk('.'):
        # 跳过一些目录
        if any(skip in root for skip in ['.git', '.venv', '__pycache__', '.vscode']):
            continue
            
        for file in files:
            if file.endswith(('.xlsx', '.xls', '.csv', '.json', '.txt', '.md')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(5000)  # 只读取前5000个字符
                        
                    # 检查是否包含关键词
                    found_keywords = []
                    for keyword in keywords:
                        if keyword.lower() in content.lower():
                            found_keywords.append(keyword)
                    
                    if found_keywords:
                        print(f"\nFound in: {filepath}")
                        print(f"Keywords: {found_keywords}")
                        
                        # 显示相关上下文
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if any(keyword.lower() in line.lower() for keyword in found_keywords):
                                start = max(0, i-2)
                                end = min(len(lines), i+3)
                                print(f"  Lines {start+1}-{end}:")
                                for j in range(start, end):
                                    print(f"    {j+1}: {lines[j][:100]}")
                                break
                                
                except Exception as e:
                    continue

if __name__ == "__main__":
    search_finance_files()