import os
import re

def search_project_files(startpath):
    # 排除虚拟环境目录
    exclude_dirs = ['.venv', '.git', '__pycache__', '.ruff_cache', '.runtime']
    found_files = []
    
    for root, dirs, files in os.walk(startpath):
        # 排除不需要的目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            # 检查是否是数据文件
            if file.endswith(('.xlsx', '.xls', '.csv', '.json', '.txt', '.md')):
                found_files.append(file_path)
            # 检查是否包含财务相关关键词
            elif any(keyword in file.lower() for keyword in ['财务', '预算', '采购', '费用', 'finance', 'budget']):
                found_files.append(file_path)
    
    return found_files

if __name__ == "__main__":
    files = search_project_files('.')
    print(f"找到 {len(files)} 个可能相关的项目文件:")
    for file in files:
        print(f"  {file}")