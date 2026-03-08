import os

def list_directory(path, indent=0):
    prefix = "  " * indent
    try:
        items = os.listdir(path)
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                print(f"{prefix}[DIR] {item}/")
                list_directory(full_path, indent + 1)
            else:
                print(f"{prefix}[FILE] {item}")
    except Exception as e:
        print(f"{prefix}[ERROR] Error accessing {path}: {e}")

print("Skills directory structure:")
list_directory("skills")