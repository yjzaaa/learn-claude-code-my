"""Universal Shell Backend - 统一的 Shell 后端

自动支持 Docker 和 Windows Shell，特性：
1. Docker 可用时优先使用 Docker Sandbox
2. Docker 不可用时自动降级到 Windows Shell
3. 命令转换：自动将 Linux 命令转换为 Windows 等价命令
4. 路径映射：统一虚拟路径，自动转换到实际路径

Example:
    >>> backend = UniversalShellBackend(
    ...     root_dir="D:/learn-claude-code-my/skills",
    ...     virtual_root="/workspace/skills"
    ... )
    >>> backend.execute("ls -la /workspace/skills")  # Windows 上自动转换
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.protocol import ExecuteResponse, FileDownloadResponse, FileUploadResponse

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Linux -> Windows 命令映射
COMMAND_MAP = {
    # 文件列表
    r"^ls\b": "dir",
    r"^ls\s+-la\b": "dir",
    r"^ls\s+-l\b": "dir",
    r"^ls\s+-a\b": "dir /a",
    # 查看文件
    r"^cat\b": "type",
    r"^cat\s+(-n|--number)\b": "type",  # 忽略行号选项
    # 搜索
    r"^grep\b": "findstr",
    r"^grep\s+-i\b": "findstr /i",
    r"^grep\s+-r\b": "findstr /s",
    r"^grep\s+-i\s+-r\b": "findstr /i /s",
    # 目录操作
    r"^pwd\b": "cd",
    r"^mkdir\s+-p\b": "mkdir",
    # 文本处理（简化版）
    r"^touch\b": "type nul >",
    r"^rm\b": "del",
    r"^rm\s+-rf\b": "rmdir /s /q",
    r"^cp\b": "copy",
    r"^mv\b": "move",
    # 权限（Windows 不支持，忽略）
    r"^chmod\b": "echo chmod_not_supported_on_windows",
    r"^chown\b": "echo chown_not_supported_on_windows",
}

# 路径映射配置
VIRTUAL_PATH_PREFIXES = [
    "/workspace",
    "/skills",
    "/tmp",
    "/home",
]


class UniversalShellBackend(LocalShellBackend):
    """统一的 Shell 后端

    自动处理 Docker/Windows 降级，命令转换，路径映射。
    """

    def __init__(
        self,
        root_dir: str,
        virtual_root: str = "/workspace/skills",
        virtual_mode: bool = True,
        inherit_env: bool = True,
    ) -> None:
        """初始化 Universal Shell Backend

        Args:
            root_dir: 实际根目录路径（Windows 绝对路径）
            virtual_root: 虚拟根目录路径（如 /workspace/skills）
            virtual_mode: 是否启用虚拟路径模式
            inherit_env: 是否继承环境变量
        """
        super().__init__(
            root_dir=root_dir,
            virtual_mode=virtual_mode,
            inherit_env=inherit_env,
        )
        self._actual_root = Path(root_dir).resolve()
        self._virtual_root = virtual_root
        self._docker_backend: Any = None
        self._use_docker = False

        # 尝试初始化 Docker Backend
        self._try_init_docker()

    def _try_init_docker(self) -> None:
        """尝试初始化 Docker Backend"""
        from .docker_sandbox_backend import DockerSandboxBackend, _docker_available

        if not _docker_available():
            logger.info("[ShellBackend] ❌ Docker不可用，将使用Windows本地Shell")
            return

        try:
            self._docker_backend = DockerSandboxBackend(
                root_dir=str(self._actual_root),
                env_allowlist=[
                    "ANTHROPIC_API_KEY",
                    "OPENAI_API_KEY",
                    "MODEL_ID",
                    "ANTHROPIC_BASE_URL",
                    "DB_HOST",
                    "DB_NAME",
                    "DB_USER",
                    "DB_PASSWORD",
                    "DB_PORT",
                    "DB_DRIVER",
                ],
            )
            self._use_docker = True
            logger.info("[ShellBackend] ✅ Docker模式 - 命令将在容器中执行")
        except Exception as e:
            logger.warning(f"[ShellBackend] ⚠️ Docker启动失败: {e}，降级到Windows本地Shell")
            self._docker_backend = None
            self._use_docker = False

    def _convert_path(self, path: str) -> str:
        """将虚拟路径转换为实际路径

        Args:
            path: 路径（虚拟或实际）

        Returns:
            实际路径
        """
        if not path:
            return str(self._actual_root)

        # 已经是 Windows 绝对路径
        if re.match(r"^[A-Za-z]:[/\\]", path):
            return path

        # 转换为 Path 对象处理
        path_obj = Path(path)

        # 虚拟路径转换
        virtual_path = Path(self._virtual_root)
        try:
            # 计算相对路径
            rel_path = path_obj.relative_to(virtual_path)
            actual = self._actual_root / rel_path
            return str(actual)
        except ValueError:
            # 不是虚拟路径的子路径，尝试其他前缀
            for prefix in VIRTUAL_PATH_PREFIXES:
                if path.startswith(prefix):
                    # /workspace/skills/xxx -> D:/.../skills/xxx
                    rel = path[len(prefix) :].lstrip("/")
                    actual = self._actual_root / rel
                    return str(actual)

        # 无法转换，原样返回
        return path

    def _convert_command(self, command: str) -> str:
        """将 Linux 命令转换为 Windows 命令

        Args:
            command: Linux 风格命令

        Returns:
            Windows 风格命令
        """
        # 如果使用 Docker，不需要转换
        if self._use_docker:
            return command

        converted = command

        # 路径转换：将命令中的虚拟路径转换为实际路径
        for prefix in VIRTUAL_PATH_PREFIXES:
            if prefix in converted:
                # 提取路径部分
                pattern = rf"{prefix}[/\\]?[^\s]*"
                matches = re.findall(pattern, converted)
                for match in matches:
                    actual_path = self._convert_path(match)
                    converted = converted.replace(match, actual_path)

        # 命令转换
        for pattern, replacement in COMMAND_MAP.items():
            converted = re.sub(pattern, replacement, converted, flags=re.IGNORECASE)

        return converted

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间

        Returns:
            执行响应
        """
        if not command or not isinstance(command, str):
            return ExecuteResponse(
                output="Error: Command must be a non-empty string.",
                exit_code=1,
                truncated=False,
            )

        # 如果使用 Docker，委托给 Docker backend
        if self._use_docker and self._docker_backend:
            logger.info(f"[Shell] Docker -> {command[:80]}{'...' if len(command) > 80 else ''}")
            return self._docker_backend.execute(command, timeout=timeout)

        # 转换命令
        converted_command = self._convert_command(command)
        logger.info(
            f"[Shell] Windows -> '{command[:60]}{'...' if len(command) > 60 else ''}' | Converted: '{converted_command[:60]}{'...' if len(converted_command) > 60 else ''}'"
        )

        # 执行转换后的命令
        return self._execute_windows(converted_command, timeout)

    def _execute_windows(
        self,
        command: str,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """在 Windows 上执行命令"""
        effective_timeout = timeout if timeout is not None else self._default_timeout
        if effective_timeout <= 0:
            msg = f"timeout must be positive, got {effective_timeout}"
            raise ValueError(msg)

        try:
            result = subprocess.run(
                command,
                check=False,
                shell=True,
                capture_output=True,
                text=False,
                timeout=effective_timeout,
                env=self._env,
                cwd=str(self.cwd),
            )

            def _decode(data: bytes) -> str:
                if not data:
                    return ""
                for enc in ("utf-8", "gbk", "cp936", "latin-1"):
                    try:
                        return data.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return data.decode("utf-8", errors="replace")

            stdout = _decode(result.stdout)
            stderr = _decode(result.stderr)

            output_parts = []
            if stdout:
                output_parts.append(stdout)
            if stderr:
                stderr_lines = stderr.strip().split("\n")
                output_parts.extend(f"[stderr] {line}" for line in stderr_lines)

            output = "\n".join(output_parts) if output_parts else "<no output>"

            truncated = False
            if len(output) > self._max_output_bytes:
                output = output[: self._max_output_bytes]
                output += f"\n\n... Output truncated at {self._max_output_bytes} bytes."
                truncated = True

            if result.returncode != 0:
                output = f"{output.rstrip()}\n\nExit code: {result.returncode}"

            return ExecuteResponse(
                output=output,
                exit_code=result.returncode,
                truncated=truncated,
            )

        except subprocess.TimeoutExpired:
            msg = f"Error: Command timed out after {effective_timeout} seconds."
            return ExecuteResponse(
                output=msg,
                exit_code=124,
                truncated=False,
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Error executing command ({type(e).__name__}): {e}",
                exit_code=1,
                truncated=False,
            )

    def _resolve_path(self, key: str) -> Path:
        """解析路径，将虚拟路径转换为实际路径

        覆盖父类方法，使用 _convert_path 进行正确的虚拟路径映射。

        Args:
            key: 文件路径（虚拟或实际）

        Returns:
            解析后的实际 Path 对象
        """
        actual_path = self._convert_path(key)
        return Path(actual_path).resolve()

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """读取文件内容

        覆盖父类方法，使用正确的路径转换。

        Args:
            file_path: 文件路径（支持虚拟路径）
            offset: 起始行偏移
            limit: 最大行数

        Returns:
            带行号的文件内容
        """
        # 转换路径
        actual_path = self._convert_path(file_path)
        # 调用父类的 read，但传入实际路径
        return super().read(actual_path, offset=offset, limit=limit)

    async def aread(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """异步读取文件内容"""
        actual_path = self._convert_path(file_path)
        return await super().aread(actual_path, offset=offset, limit=limit)

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """下载文件"""
        # 转换路径
        actual_paths = [self._convert_path(p) for p in paths]

        if self._use_docker and self._docker_backend:
            return self._docker_backend.download_files(actual_paths)

        return super().download_files(actual_paths)

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """上传文件"""
        # 转换路径
        converted_files = []
        for path, data in files:
            actual_path = self._convert_path(path)
            converted_files.append((actual_path, data))

        if self._use_docker and self._docker_backend:
            return self._docker_backend.upload_files(converted_files)

        return super().upload_files(converted_files)

    @property
    def id(self) -> str:
        """Backend 标识"""
        if self._use_docker:
            return f"universal_docker_{self._docker_backend.id}"
        return f"universal_windows_{self._actual_root.name}"


def create_universal_backend(
    root_dir: str,
    virtual_root: str = "/workspace/skills",
    virtual_mode: bool = True,
    inherit_env: bool = True,
) -> UniversalShellBackend:
    """创建 Universal Shell Backend

    工厂函数，自动处理 Docker/Windows 选择。

    Args:
        root_dir: 实际根目录
        virtual_root: 虚拟根目录
        virtual_mode: 虚拟路径模式
        inherit_env: 继承环境变量

    Returns:
        UniversalShellBackend 实例
    """
    return UniversalShellBackend(
        root_dir=root_dir,
        virtual_root=virtual_root,
        virtual_mode=virtual_mode,
        inherit_env=inherit_env,
    )


__all__ = [
    "UniversalShellBackend",
    "create_universal_backend",
    "COMMAND_MAP",
]
