
import subprocess
from pathlib import Path
from typing import Any, Callable
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


class WorkspaceOps:
    """工作区操作抽象。

    封装路径安全校验、命令执行以及常用文件读写编辑，
    供各章节脚本复用。
    """

    def __init__(
        self,
        workdir: Path,
        command_guard: DefaultCommandGuard | None = None,
        shell_runner: Callable[..., subprocess.CompletedProcess] | None = None,
        auto_build_tools: bool = True,
    ):
        """初始化工作目录上下文。"""
        self.workdir = workdir
        self.command_guard = command_guard or DefaultCommandGuard()
        self.shell_runner = shell_runner or subprocess.run
        # 默认在构造阶段构建基础工具列表，供外部直接复用。
        self.tools: list[Callable[..., Any]] = (
            self.build_default_tools() if auto_build_tools else []
        )

    @staticmethod
    def _read_text_safe(path: Path) -> str:
        """Read text with explicit encodings to avoid Windows locale decode issues."""
        for enc in ("utf-8", "utf-8-sig", "gbk"):
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        # Final fallback: preserve process continuity for mixed-encoding files.
        return path.read_text(encoding="utf-8", errors="replace")
    def safe_path(self, relative_path: str) -> Path:
        """解析并校验相对路径，防止逃逸出工作区。"""
        path = (self.workdir / relative_path).resolve()
        if not path.is_relative_to(self.workdir):
            raise ValueError(f"Path escapes workspace: {relative_path}")
        return path

    def run_bash(self, command: str, timeout: int = 120) -> str:
        """执行 shell 命令并返回截断后的输出。"""
        allowed, reason = self.command_guard.is_allowed(command)
        if not allowed:
            return f"Error: {reason}"
        try:
            result = self.shell_runner(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (result.stdout + result.stderr).strip()
            return output[:50000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return f"Error: Timeout ({timeout}s)"

    def run_read(self, path: str, limit: int = None) -> str:
        """读取文件内容，可选按行数限制并提示剩余行数。"""
        try:
            lines = self._read_text_safe(self.safe_path(path)).splitlines()
            if limit and limit < len(lines):
                lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
            return "\n".join(lines)[:50000]
        except Exception as e:
            return f"Error: {e}"

    def run_write(self, path: str, content: str) -> str:
        """写入文件内容（自动创建父目录）。"""
        try:
            file_path = self.safe_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} bytes"
        except Exception as e:
            return f"Error: {e}"

    def run_edit(self, path: str, old_text: str, new_text: str) -> str:
        """在文件中做一次精确文本替换。"""
        try:
            file_path = self.safe_path(path)
            content = self._read_text_safe(file_path)
            if old_text not in content:
                return f"Error: Text not found in {path}"
            file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
            return f"Edited {path}"
        except Exception as e:
            return f"Error: {e}"

    def build_default_tools(
        self,
        *,
        include_bash: bool = True,
        include_read: bool = True,
        include_write: bool = True,
        include_edit: bool = True,
        bash_timeout: int = 120,
    ) -> list[Callable[..., Any]]:
        """构建默认工具函数列表（已带 @tool 标记）。"""
        from .toolkit import tool

        tools: list[Callable[..., Any]] = []

        if include_bash:
            @tool(name="bash", description="Run a shell command.")
            def bash(command: str) -> str:
                return self.run_bash(command, timeout=bash_timeout)

            tools.append(bash)

        if include_read:
            @tool(name="read_file", description="Read file contents.")
            def read_file(path: str, limit: int | None = None) -> str:
                return self.run_read(path, limit)

            tools.append(read_file)

        if include_write:
            @tool(name="write_file", description="Write content to file.")
            def write_file(path: str, content: str) -> str:
                return self.run_write(path, content)

            tools.append(write_file)

        if include_edit:
            @tool(name="edit_file", description="Replace exact text in file.")
            def edit_file(path: str, old_text: str, new_text: str) -> str:
                return self.run_edit(path, old_text, new_text)

            tools.append(edit_file)

        return tools

    def get_tools(self, *, as_dict: bool = False) -> list[Callable[..., Any]] | dict[str, Callable[..., Any]]:
        """返回当前 WorkspaceOps 暴露的工具。

        - `as_dict=False`：返回工具函数列表。
        - `as_dict=True`：按工具名返回映射，便于按名称索引。
        """
        if not as_dict:
            return list(self.tools)

        mapping: dict[str, Callable[..., Any]] = {}
        for fn in self.tools:
            spec = getattr(fn, "__tool_spec__", None)
            if not spec or not spec.get("name"):
                continue
            mapping[spec["name"]] = fn
        return mapping
