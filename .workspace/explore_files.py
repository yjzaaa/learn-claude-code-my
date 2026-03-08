import os
import json

def explore_directory(path=".", keywords=None):
    """探索目录结构并查找包含关键词的文件"""
    if keywords is None:
        keywords = ["财务", "budget", "采购", "purchase", "finance", "fiscal"]
    
    results = []
    
    for root, dirs, files in os.walk(path):
        # 跳过一些常见的虚拟环境目录
        if any(skip in root for skip in ['.venv', '__pycache__', '.git']):
            continue
            
        for file in files:
            file_lower = file.lower()
            file_path = os.path.join(root, file)
            
            # 检查文件名是否包含关键词
            for keyword in keywords:
                if keyword.lower() in file_lower:
                    results.append({
                        'file': file,
                        'path': file_path,
                        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    })
                    break
    
    return results

if __name__ == "__main__":
    print("开始探索工作空间...")
    
    # 在当前目录和.workspace目录中搜索
    search_paths = [".", ".workspace"]
    
    all_results = []
    for path in search_paths:
        if os.path.exists(path):
            results = explore_directory(path)
            all_results.extend(results)
    
    print(f"找到 {len(all_results)} 个相关文件:")
    for i, result in enumerate(all_results, 1):
        print(f"{i}. {result['file']} - {result['path']} ({result['size']} bytes)")
    
    # 保存结果到JSON文件
    with open('.workspace/search_results.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到 .workspace/search_results.json")