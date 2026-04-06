"""
Workspace Operations - 工作区操作

封装路径安全校验、命令执行以及常用文件读写编辑。
从原始 agents/base/basetool.py 迁移而来。
"""

import subprocess
import os
import re
from pathlib import Path
from typing import Optional, Any, Callable, Literal, overload, Union

from .security.guard import DefaultCommandGuard
from .file.operations import read_text_safe


class WorkspaceOps:
    """工作区操作抽象。

    封装路径安全校验、命令执行以及常用文件读写编辑，
    供各章节脚本复用。
    """

    def __init__(
        self,
        workdir: Path,
        command_guard: Optional[DefaultCommandGuard] = None,
        shell_runner: Optional[Callable[..., subprocess.CompletedProcess]] = None,
        auto_build_tools: bool = True,
    ):
        """初始化工作目录上下文。"""
        self.workdir = workdir
        self.command_guard = command_guard or DefaultCommandGuard()
        self.shell_runner = shell_runner or subprocess.run
        self._dotenv_values = self._load_env_file(self.workdir / ".env")
        self.bash_script_whitelist = self._resolve_bash_script_whitelist()
        self.bash_script_scopes, self.allow_skills_scripts_pattern = self._build_bash_script_scopes(
            self.bash_script_whitelist
        )
        self.write_tool_whitelist = self._resolve_path_whitelist("WRITE_TOOL_WHITELIST", ".workspace;skills")
        self.edit_tool_whitelist = self._resolve_path_whitelist("EDIT_TOOL_WHITELIST", ".workspace;skills")
        self.read_tool_blacklist = self._resolve_path_whitelist("READ_TOOL_BLACKLIST", ".env")
        self.write_scopes = self._build_simple_scopes(self.write_tool_whitelist)
        self.edit_scopes = self._build_simple_scopes(self.edit_tool_whitelist)
        self.read_blacklist_scopes = self._build_simple_scopes(self.read_tool_blacklist)
        self.write_scope = self.write_scopes[0]
        self.bash_script_ext_whitelist = {".py", ".ps1", ".bat", ".cmd"}
        # Inline Python is enabled by default; set ALLOW_INLINE_PYTHON=0/false to disable.
        self.allow_inline_python = self._resolve_bool_flag("ALLOW_INLINE_PYTHON", True)
        # 默认在构造阶段构建基础工具列表，供外部直接复用。
        self.tools: list[Callable[..., Any]] = (
            self.build_default_tools() if auto_build_tools else []
        )

    def _resolve_bool_flag(self, env_key: str, default: bool) -> bool:
        env_value = os.environ.get(env_key)
        dotenv_value = self._dotenv_values.get(env_key)
        raw = (env_value if env_value is not None else dotenv_value)
        if raw is None:
            return default
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _split_list_value(raw_value: Optional[str]) -> list[str]:
        if not raw_value:
            return []
        return [item.strip() for item in re.split(r"[;,]", raw_value) if item.strip()]

    def _resolve_bash_script_whitelist(self) -> list[str]:
        env_value = os.environ.get("BASH_SCRIPT_WHITELIST")
        dotenv_value = self._dotenv_values.get("BASH_SCRIPT_WHITELIST")

        # Keep a secure default when not configured.
        raw_tokens = self._split_list_value(env_value or dotenv_value)
        if not raw_tokens:
            return [".workspace", "skills/**/scripts"]
        return raw_tokens

    def _resolve_path_whitelist(self, env_key: str, default_value: str) -> list[str]:
        env_value = os.environ.get(env_key)
        dotenv_value = self._dotenv_values.get(env_key)
        raw_tokens = self._split_list_value(env_value or dotenv_value)
        if raw_tokens:
            return raw_tokens

        default_tokens = self._split_list_value(default_value)
        return default_tokens if default_tokens else [default_value]

    def _build_simple_scopes(self, whitelist: list[str]) -> list[Path]:
        scopes: list[Path] = []
        seen_scopes: set[str] = set()

        for token in whitelist:
            normalized = token.replace("\\", "/").strip()
            normalized = normalized[2:] if normalized.startswith("./") else normalized
            if "*" in normalized:
                continue

            candidate = Path(normalized)
            resolved = candidate.resolve() if candidate.is_absolute() else (self.workdir / candidate).resolve()
            if not resolved.is_relative_to(self.workdir):
                continue

            key = str(resolved).lower()
            if key in seen_scopes:
                continue
            seen_scopes.add(key)
            scopes.append(resolved)

        if not scopes:
            scopes.append((self.workdir / ".workspace").resolve())

        return scopes

    def _build_bash_script_scopes(self, whitelist: list[str]) -> tuple[list[Path], bool]:
        scopes: list[Path] = []
        seen_scopes: set[str] = set()
        allow_skills_scripts = False

        for token in whitelist:
            normalized = token.replace("\\", "/").strip()
            normalized = normalized[2:] if normalized.startswith("./") else normalized

            if normalized == "skills/**/scripts":
                allow_skills_scripts = True
                continue

            candidate = Path(normalized)
            resolved = candidate.resolve() if candidate.is_absolute() else (self.workdir / candidate).resolve()

            # Keep whitelist bounded to current workspace.
            if not resolved.is_relative_to(self.workdir):
                continue

            key = str(resolved).lower()
            if key in seen_scopes:
                continue
            seen_scopes.add(key)
            scopes.append(resolved)

        if not scopes and not allow_skills_scripts:
            scopes.append(self.write_scope)

        return scopes, allow_skills_scripts

    @staticmethod
    def _to_rel_path_str(path_obj: Path) -> str:
        return str(path_obj).replace("\\", "/")

    def _normalize_scoped_path(self, path: str, scopes: list[Path]) -> str:
        """Force relative write/edit targets into first scope unless already under a whitelisted scope."""
        candidate = Path(path)
        if candidate.is_absolute():
            return path

        rel_candidate = self._to_rel_path_str(candidate)
        for scope in scopes:
            try:
                scope_rel = self._to_rel_path_str(scope.relative_to(self.workdir))
            except ValueError:
                continue

            if rel_candidate == scope_rel or rel_candidate.startswith(f"{scope_rel}/"):
                return path

        default_scope_rel = self._to_rel_path_str(scopes[0].relative_to(self.workdir))
        return self._to_rel_path_str(Path(default_scope_rel) / candidate)

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

    @staticmethod
    def _load_env_file(dotenv_path: Path) -> dict[str, str]:
        """Parse a simple .env file into key/value pairs."""
        if not dotenv_path.exists() or not dotenv_path.is_file():
            return {}

        raw = WorkspaceOps._read_text_safe(dotenv_path)
        values: dict[str, str] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            # Remove optional surrounding quotes.
            if len(value) >= 2 and (
                (value[0] == '"' and value[-1] == '"')
                or (value[0] == "'" and value[-1] == "'")
            ):
                value = value[1:-1]

            values[key] = value

        return values

    def safe_path(self, relative_path: str) -> Path:
        """解析并校验相对路径，防止逃逸出工作区。"""
        path = (self.workdir / relative_path).resolve()
        if not path.is_relative_to(self.workdir):
            raise ValueError(f"Path escapes workspace: {relative_path}")
        return path

    @staticmethod
    def _is_in_any_scope(file_path: Path, scopes: list[Path]) -> bool:
        for scope in scopes:
            if file_path == scope:
                return True
            if scope.is_dir() and file_path.is_relative_to(scope):
                return True
        return False

    def _is_env_blocked_path(self, file_path: Path) -> bool:
        """是否命中读黑名单路径（例如 .env）。"""
        return self._is_in_any_scope(file_path, self.read_blacklist_scopes)

    def _is_skills_path(self, file_path: Path) -> bool:
        """是否位于 skills 目录下。"""
        skills_root = (self.workdir / "skills").resolve()
        return file_path.is_relative_to(skills_root)

    @staticmethod
    def _looks_like_path_token(token: str) -> bool:
        if not token:
            return False
        # Ignore inline code/script fragments (e.g. python -c "from x import y; ...").
        if any(ch in token for ch in [";", "|", "(", ")", "{", "}", "$"]):
            return False
        if " " in token:
            return False
        if token.startswith("-"):
            return False
        if token.lower().startswith(("http://", "https://")):
            return False
        if token.startswith((".", "~", "/", "\\")):
            return True
        if "\\" in token or "/" in token:
            return True
        if re.match(r"^[a-zA-Z]:", token):
            return True
        return False

    def _extract_command_paths(self, command: str) -> list[Path]:
        # Extract simple quoted/unquoted tokens and keep only path-like entries.
        token_pattern = r'"([^"]+)"|\'([^\']+)\'|([^\s]+)'
        paths: list[Path] = []

        for match in re.finditer(token_pattern, command):
            token = next((group for group in match.groups() if group), "").strip()
            token = token.rstrip(";|,")
            if not self._looks_like_path_token(token):
                continue

            candidate = Path(token)
            resolved = candidate.resolve() if candidate.is_absolute() else (self.workdir / candidate).resolve()
            paths.append(resolved)

        return paths

    def _is_allowed_bash_script(self, path: Path) -> bool:
        if path.suffix.lower() not in self.bash_script_ext_whitelist:
            return False

        for scope in self.bash_script_scopes:
            if path.is_relative_to(scope):
                return True

        if not self.allow_skills_scripts_pattern:
            return False

        # Optional wildcard rule for skills/**/scripts/*.
        skills_root = (self.workdir / "skills").resolve()
        if not path.is_relative_to(skills_root):
            return False

        rel_parts = path.relative_to(skills_root).parts
        return "scripts" in rel_parts

    def _validate_bash_script_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Allow approved script execution and selected inline commands."""
        if re.search(r"\bpython(?:\.exe)?\s+-c\b", command, flags=re.IGNORECASE):
            if self.allow_inline_python:
                return True, None
            return False, "Inline python (-c) is not allowed; run a script from BASH_SCRIPT_WHITELIST."
        if re.search(r"\bpowershell(?:\.exe)?\s+-Command\b", command, flags=re.IGNORECASE):
            return True, None

        for resolved_path in self._extract_command_paths(command):
            if self._is_allowed_bash_script(resolved_path):
                return True, None

        return (
            False,
            "bash is restricted to scripts in BASH_SCRIPT_WHITELIST (e.g. python .workspace/run.py or python skills/finance/scripts/sql_query.py)",
        )

    def run_bash(self, command: str, timeout: int = 60) -> str:
        """执行 shell 命令并返回截断后的输出。"""
        allowed, reason = self.command_guard.is_allowed(command)
        if not allowed:
            return f"Error: {reason}"

        access_allowed, access_reason = self._validate_bash_script_command(command)
        if not access_allowed:
            return f"Error: {access_reason}"

        # Temporary platform hard-limit: only support Windows runtime now.
        if os.name != "nt":
            return "Error: Only Windows is supported for shell execution right now."

        try:
            env = os.environ.copy()

            # Load workspace .env so approved scripts can read DB_* settings.
            dotenv_values = self._dotenv_values
            for key, value in dotenv_values.items():
                env.setdefault(key, value)

            # Ensure Python commands executed from approved scripts can import project modules.
            current_pythonpath = env.get("PYTHONPATH", "")
            pythonpath_parts = [str(self.workdir)]
            if current_pythonpath:
                pythonpath_parts.append(current_pythonpath)
            env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

            # Prefer workspace virtual environment when present.
            venv_scripts = self.workdir / ".venv" / "Scripts"
            if venv_scripts.exists():
                current_path = env.get("PATH", "")
                env["PATH"] = f"{venv_scripts}{os.pathsep}{current_path}" if current_path else str(venv_scripts)

            result = self.shell_runner(
                ["powershell.exe", "-NoProfile", "-Command", command],
                shell=False,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            output = (result.stdout + result.stderr).strip()
            return output[:50000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout}s. For long-running commands, consider running in background or increasing timeout."

    def run_read(self, path: str, limit: Optional[int] = None) -> str:
        """读取文件内容，可选按行数限制并提示剩余行数。"""
        try:
            file_path = self.safe_path(path)
            if self._is_env_blocked_path(file_path):
                return "Error: read_file is blocked by READ_TOOL_BLACKLIST"

            lines = self._read_text_safe(file_path).splitlines()
            if limit and limit < len(lines):
                lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
            return "\n".join(lines)[:50000]
        except Exception as e:
            return f"Error: {e}"

    def run_write(self, path: str, content: str) -> str:
        """写入文件内容（自动创建父目录）。"""
        try:
            normalized_path = self._normalize_scoped_path(path, self.write_scopes)
            file_path = self.safe_path(normalized_path)
            if self._is_env_blocked_path(file_path):
                return "Error: write_file is blocked for this path"
            if not self._is_in_any_scope(file_path, self.write_scopes):
                return "Error: write_file is restricted by WRITE_TOOL_WHITELIST"

            # 仅允许在 skills 下修改已有文件；禁止通过 write_file 新建。
            if self._is_skills_path(file_path) and not file_path.exists():
                return "Error: write_file cannot create new files under skills; use edit_file on existing files"

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} bytes to {normalized_path}"
        except Exception as e:
            return f"Error: {e}"

    def run_edit(self, path: str, old_text: str, new_text: str) -> str:
        """在文件中做一次精确文本替换。"""
        try:
            normalized_path = self._normalize_scoped_path(path, self.edit_scopes)
            file_path = self.safe_path(normalized_path)
            if self._is_env_blocked_path(file_path):
                return "Error: edit_file is blocked for this path"
            if not self._is_in_any_scope(file_path, self.edit_scopes):
                return "Error: edit_file is restricted by EDIT_TOOL_WHITELIST"
            content = self._read_text_safe(file_path)
            if old_text not in content:
                return f"Error: Text not found in {path}"

            replaced = content.replace(old_text, new_text, 1)
            file_path.write_text(replaced, encoding="utf-8")
            return f"Edited {normalized_path}"
        except Exception as e:
            return f"Error: {e}"

    def build_default_tools(
        self,
        *,
        include_bash: bool = True,
        include_read: bool = True,
        include_write: bool = True,
        include_edit: bool = True,
        bash_timeout: int = 60,
    ) -> list[Callable[..., Any]]:
        """构建默认工具函数列表（已带 @tool 标记）。"""
        from .toolkit import tool

        tools: list[Callable[..., Any]] = []

        if include_bash:
            @tool(
                name="bash",
                description="Run a command in Windows PowerShell only. Script files from BASH_SCRIPT_WHITELIST are executable (default: .workspace;skills/**/scripts). Inline Python (-c) is allowed by default. Inline PowerShell (-Command) is allowed.",
            )
            def bash(command: str) -> str:
                return self.run_bash(command, timeout=bash_timeout)

            tools.append(bash)

        if include_read:
            @tool(
                name="read_file",
                description="Read file contents, except paths blocked by READ_TOOL_BLACKLIST (default: .env).",
            )
            def read_file(path: str, limit: Optional[int] = None) -> str:
                return self.run_read(path, limit)

            tools.append(read_file)

        if include_write:
            @tool(
                name="write_file",
                description="Write content to files allowed by WRITE_TOOL_WHITELIST (default: .workspace); relative paths are auto-prefixed to the first whitelist path.",
            )
            def write_file(path: str, content: str) -> str:
                return self.run_write(path, content)

            tools.append(write_file)

        if include_edit:
            @tool(
                name="edit_file",
                description="Replace exact text in files allowed by EDIT_TOOL_WHITELIST (default: .workspace); relative paths are auto-prefixed to the first whitelist path.",
            )
            def edit_file(path: str, old_text: str, new_text: str) -> str:
                return self.run_edit(path, old_text, new_text)

            tools.append(edit_file)

        return tools

    @overload
    def get_tools(self, *, as_dict: Literal[False] = ...) -> list[Callable[..., Any]]: ...
    @overload
    def get_tools(self, *, as_dict: Literal[True]) -> dict[str, Callable[..., Any]]: ...
    def get_tools(self, *, as_dict: bool = False) -> Union[list[Callable[..., Any]], dict[str, Callable[..., Any]]]:
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
