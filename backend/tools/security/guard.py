"""
Security Guards - 安全守卫

路径安全和命令安全检查。
"""
from pathlib import Path
from typing import Callable
import subprocess


class DefaultCommandGuard:
    """默认命令安全策略。"""

    def __init__(self, blocked_tokens: list[str] | None = None):
        self.blocked_tokens = blocked_tokens or ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]

    def is_allowed(self, command: str) -> tuple[bool, str | None]:
        """返回命令是否允许执行及拒绝原因。"""
        for token in self.blocked_tokens:
            if token in command:
                return False, f"Dangerous command blocked: {token}"
        return True, None


def is_in_any_scope(file_path: Path, scopes: list[Path]) -> bool:
    """检查文件路径是否在任意作用域内。"""
    try:
        return any(
            file_path == scope or (file_path.is_relative_to(scope) if hasattr(file_path, 'is_relative_to') else scope in file_path.parents or file_path == scope)
            for scope in scopes
        )
    except Exception:
        return False
