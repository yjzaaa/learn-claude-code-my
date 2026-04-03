"""
Path Guard - 路径安全检查

提供路径白名单、作用域检查等安全功能。
"""
import re
import os
from pathlib import Path
from typing import Optional


class PathGuard:
    """路径安全守卫"""

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self._dotenv_values = self._load_env_file(workdir / ".env")

        # 初始化白名单
        self.bash_script_whitelist = self._resolve_bash_script_whitelist()
        self.bash_script_scopes, self.allow_skills_scripts_pattern = self._build_bash_script_scopes(
            self.bash_script_whitelist
        )
        self.write_tool_whitelist = self._resolve_path_whitelist("WRITE_TOOL_WHITELIST", ".workspace;skills")
        self.edit_tool_whitelist = self._resolve_path_whitelist("EDIT_TOOL_WHITELIST", ".workspace;skills")
        self.read_tool_blacklist = self._resolve_path_whitelist("READ_TOOL_BLACKLIST", ".env")

        # 构建作用域
        self.write_scopes = self._build_simple_scopes(self.write_tool_whitelist)
        self.edit_scopes = self._build_simple_scopes(self.edit_tool_whitelist)
        self.read_blacklist_scopes = self._build_simple_scopes(self.read_tool_blacklist)
        self.write_scope = self.write_scopes[0] if self.write_scopes else self.workdir

    @staticmethod
    def _load_env_file(dotenv_path: Path) -> dict[str, str]:
        """加载 .env 文件"""
        if not dotenv_path.exists():
            return {}

        values = {}
        try:
            content = dotenv_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    values[key.strip()] = value.strip().strip('"\'')
        except Exception:
            pass
        return values

    @staticmethod
    def _split_list_value(raw_value: str | None) -> list[str]:
        """分割列表值"""
        if not raw_value:
            return []
        return [item.strip() for item in re.split(r"[;,]", raw_value) if item.strip()]

    def _resolve_bash_script_whitelist(self) -> list[str]:
        """解析 bash 脚本白名单"""
        env_value = os.environ.get("BASH_SCRIPT_WHITELIST")
        dotenv_value = self._dotenv_values.get("BASH_SCRIPT_WHITELIST")

        raw_tokens = self._split_list_value(env_value or dotenv_value)
        if not raw_tokens:
            return [".workspace", "skills/**/scripts"]
        return raw_tokens

    def _resolve_path_whitelist(self, env_key: str, default_value: str) -> list[str]:
        """解析路径白名单"""
        env_value = os.environ.get(env_key)
        dotenv_value = self._dotenv_values.get(env_key)
        raw_tokens = self._split_list_value(env_value or dotenv_value)
        if raw_tokens:
            return raw_tokens

        default_tokens = self._split_list_value(default_value)
        return default_tokens if default_tokens else [default_value]

    def _build_simple_scopes(self, whitelist: list[str]) -> list[Path]:
        """构建简单作用域"""
        scopes = []
        for token in whitelist:
            if token == ".workspace":
                scopes.append(self.workdir)
            elif "/" in token or "\\" in token:
                scopes.append(Path(token).expanduser().resolve())
            else:
                scopes.append(self.workdir / token)
        return scopes

    def _build_bash_script_scopes(self, whitelist: list[str]) -> tuple[list[Path], bool]:
        """构建 bash 脚本作用域"""
        scopes = []
        allow_skills_scripts = False
        for token in whitelist:
            if token == ".workspace":
                scopes.append(self.workdir)
            elif token == "skills/**/scripts":
                allow_skills_scripts = True
            elif "/" in token or "\\" in token:
                scopes.append(Path(token).expanduser().resolve())
            else:
                scopes.append(self.workdir / token)
        return scopes, allow_skills_scripts

    def safe_path(self, relative_path: str) -> Path:
        """获取安全路径"""
        target = self.workdir / relative_path
        target = target.resolve()

        # 确保在 workdir 内
        try:
            target.relative_to(self.workdir.resolve())
        except ValueError:
            raise ValueError(f"Path outside workspace: {relative_path}")

        return target

    def is_in_any_scope(self, file_path: Path, scopes: list[Path]) -> bool:
        """检查路径是否在任意作用域内"""
        try:
            for scope in scopes:
                if file_path == scope or file_path.is_relative_to(scope):
                    return True
        except Exception:
            pass
        return False

    def is_env_blocked_path(self, file_path: Path) -> bool:
        """检查路径是否在环境黑名单中"""
        return self.is_in_any_scope(file_path, self.read_blacklist_scopes)

    def is_skills_path(self, file_path: Path) -> bool:
        """检查路径是否在 skills 目录下"""
        try:
            skills_dir = self.workdir / "skills"
            return file_path.is_relative_to(skills_dir)
        except Exception:
            return False
