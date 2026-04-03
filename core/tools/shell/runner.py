"""
Shell Runner - Shell 命令执行

安全的 Shell 命令执行功能。
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from core.tools.security.guard import DefaultCommandGuard


class ShellRunner:
    """Shell 命令执行器"""

    def __init__(self, workdir: Path, command_guard: Optional[DefaultCommandGuard] = None):
        self.workdir = workdir
        self.command_guard = command_guard or DefaultCommandGuard()

    def run_bash(self, command: str, timeout: int = 120) -> str:
        """执行 bash 命令"""
        # 检查命令安全性
        allowed, reason = self.command_guard.is_allowed(command)
        if not allowed:
            return f"Command blocked: {reason}"

        # 设置环境变量
        env = os.environ.copy()
        env["PWD"] = str(self.workdir)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.workdir,
                timeout=timeout,
                env=env,
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"

            return output or "Command completed with no output"

        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Command failed: {e}"

    @staticmethod
    def _extract_command_paths(command: str) -> list[Path]:
        """从命令中提取路径"""
        paths = []
        tokens = re.split(r'[\s\|&;<>]', command)
        for token in tokens:
            if not token:
                continue
            if token.startswith(("./", "../", "/", "~/")):
                paths.append(Path(token).expanduser().resolve())
        return paths
