import os
import sys

def explore_directory(path=".", depth=0, max_depth=3):
    """递归探索目录结构"""
    indent = "  " * depth
    
    try:
        items = os.listdir(path)
    except PermissionError:
        print(f"{indent}[权限拒绝: {path}]")
        return
    except FileNotFoundError:
        print(f"{indent}[目录不存在: {path}]")
        return
    
    for item in items:
        full_path = os.path.join(path, item)
        
        # 跳过一些特殊目录
        if item in ['.git', '__pycache__', '.venv', '.idea', '.vscode']:
            continue
            
        try:
            if os.path.isdir(full_path):
                print(f"{indent}[DIR] {item}/")
                if depth < max_depth:
                    explore_directory(full_path, depth + 1, max_depth)
            else:
                # 检查文件类型
                ext = os.path.splitext(item)[1].lower()
                file_types = {
                    '.py': '[PY]',
                    '.sql': '[SQL]',
                    '.csv': '[CSV]',
                    '.xlsx': '[XLSX]',
                    '.xls': '[XLS]',
                    '.txt': '[TXT]',
                    '.json': '[JSON]',
                    '.md': '[MD]',
                    '.pdf': '[PDF]',
                    '.doc': '[DOC]',
                    '.docx': '[DOCX]'
                }
                icon = file_types.get(ext, '[FILE]')
                size = os.path.getsize(full_path)
                print(f"{indent}{icon} {item} ({size:,} bytes)")
        except (PermissionError, OSError) as e:
            print(f"{indent}[ERROR] {item} [错误: {str(e)}]")

if __name__ == "__main__":
    print("=== 目录结构探索 ===")
    print(f"当前工作目录: {os.getcwd()}")
    print("\n目录内容:")
    explore_directory()