"""
File Operations - 文件操作

安全的文件读写编辑操作。
"""
from pathlib import Path


def read_text_safe(path: Path) -> str:
    """安全读取文本文件，支持多种编码。"""
    encodings = ["utf-8", "utf-8-sig", "gbk", "latin1"]
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode file: {path}")


def read_file(path: str, workdir: Path, limit: int | None = None) -> str:
    """读取文件内容。"""
    target = workdir / path
    content = read_text_safe(target)
    if limit and len(content) > limit:
        content = content[:limit] + f"\n... (truncated, total {len(content)} chars)"
    return content


def write_file(path: str, content: str, workdir: Path) -> str:
    """写入文件内容。"""
    target = workdir / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written {len(content)} chars to {path}"


def edit_file(path: str, old_text: str, new_text: str, workdir: Path) -> str:
    """编辑文件内容。"""
    target = workdir / path
    content = read_text_safe(target)
    if old_text not in content:
        raise ValueError(f"old_text not found in {path}")
    content = content.replace(old_text, new_text, 1)
    target.write_text(content, encoding="utf-8")
    return f"Edited {path}"
