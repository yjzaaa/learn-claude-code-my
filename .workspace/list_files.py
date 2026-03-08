import os

def list_files_and_dirs(path='.', indent=0):
    """递归列出文件和目录"""
    try:
        items = os.listdir(path)
        for item in items:
            full_path = os.path.join(path, item)
            prefix = '  ' * indent
            if os.path.isdir(full_path):
                print(f'{prefix}[DIR] {item}/')
                # 递归列出子目录
                list_files_and_dirs(full_path, indent + 1)
            else:
                print(f'{prefix}[FILE] {item}')
    except PermissionError:
        print(f'{prefix}[PERMISSION ERROR] {path}')
    except Exception as e:
        print(f'{prefix}[ERROR] {e}')

if __name__ == '__main__':
    print("当前目录结构:")
    print("=" * 50)
    list_files_and_dirs()