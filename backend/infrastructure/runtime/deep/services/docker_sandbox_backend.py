"""Docker Sandbox Backend - Docker 容器隔离后端

基于 deepagents BaseSandbox 实现，将文件操作与 Shell 命令全部转发到
Docker 容器内执行。容器通过 Volume 挂载 skills 目录，保证文件持久化。
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional

import sys
import tempfile

from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.protocol import ExecuteResponse, FileDownloadResponse, FileUploadResponse
from deepagents.backends.sandbox import BaseSandbox
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 120
DEFAULT_IMAGE = "deep-agent-sandbox:latest"
DEFAULT_CONTAINER_NAME = "deep-agent-sandbox"
DEFAULT_ENV_ALLOWLIST = [
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
]


def _docker_available() -> bool:
    """检查 Docker daemon 是否可访问。"""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=False,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


class DockerSandboxBackend(BaseSandbox):
    """Docker 容器隔离后端

    通过 docker exec 在已启动的守护容器内执行命令，所有文件操作与 shell
    调用均在容器内完成。skills 目录通过 volume 挂载到容器内 /workspace/skills。
    """

    def __init__(
        self,
        root_dir: str,
        image: str = DEFAULT_IMAGE,
        container_name: str = DEFAULT_CONTAINER_NAME,
        env_allowlist: Optional[list[str]] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.root_dir = str(Path(root_dir).resolve())
        self.image = image
        self.container_name = container_name
        self.env_allowlist = env_allowlist or list(DEFAULT_ENV_ALLOWLIST)
        self._default_timeout = timeout
        self._max_output_bytes = 100_000
        self._ensure_container_running()

    def _ensure_container_running(self) -> None:
        """检测容器是否存活，未启动则创建并启动。"""
        try:
            inspect = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            running = inspect.stdout.strip().lower() == "true"
        except Exception:
            running = False

        if running:
            return

        # 尝试先删除可能存在的已停止容器（避免冲突）
        subprocess.run(
            ["docker", "rm", "-f", self.container_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        # 启动新的守护容器
        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "-v", f"{self.root_dir}:/workspace/skills",
            "-w", "/workspace/skills",
            self.image,
            "sleep", "infinity",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Failed to start sandbox container: {err}")

    def execute(
        self,
        command: str,
        *,
        timeout: Optional[int] = None,
    ) -> ExecuteResponse:
        """通过 docker exec 在容器内执行命令。"""
        effective_timeout = timeout if timeout is not None else self._default_timeout
        if effective_timeout <= 0:
            raise ValueError(f"timeout must be positive, got {effective_timeout}")

        if not command or not isinstance(command, str):
            return ExecuteResponse(
                output="Error: Command must be a non-empty string.",
                exit_code=1,
                truncated=False,
            )

        # 透传允许的环境变量
        env_args: list[str] = []
        for key in self.env_allowlist:
            val = os.environ.get(key)
            if val is not None:
                # 使用 -e KEY=VAL 避免 shell 解析问题
                env_args.extend(["-e", f"{key}={val}"])

        exec_cmd = [
            "docker", "exec",
            *env_args,
            self.container_name,
            "sh", "-c", command,
        ]

        try:
            result = subprocess.run(
                exec_cmd,
                check=False,
                capture_output=True,
                text=False,
                timeout=effective_timeout,
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
            msg = (
                f"Error: Command timed out after {effective_timeout} seconds. "
                "For long-running commands, re-run using the timeout parameter."
            )
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

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """通过 docker cp 从容器的指定路径下载文件。"""
        results: list[FileDownloadResponse] = []
        for path in paths:
            container_path = path.replace("\\", "/")
            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = Path(tmpdir) / Path(container_path).name
                cp_result = subprocess.run(
                    ["docker", "cp", f"{self.container_name}:{container_path}", str(local_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,
                )
                if cp_result.returncode != 0 or not local_path.exists():
                    results.append(
                        FileDownloadResponse(
                            path=path,
                            content=b"",
                            error=cp_result.stderr.strip() or "docker cp failed",
                        )
                    )
                    continue
                results.append(
                    FileDownloadResponse(
                        path=path,
                        content=local_path.read_bytes(),
                    )
                )
        return results

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """通过 docker cp 将文件上传到容器的指定路径。"""
        results: list[FileUploadResponse] = []
        for path, data in files:
            container_path = path.replace("\\", "/")
            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = Path(tmpdir) / Path(container_path).name
                local_path.write_bytes(data)
                cp_result = subprocess.run(
                    ["docker", "cp", str(local_path), f"{self.container_name}:{container_path}"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,
                )
                if cp_result.returncode != 0:
                    results.append(
                        FileUploadResponse(
                            path=path,
                            error=cp_result.stderr.strip() or "docker cp failed",
                        )
                    )
                    continue
                results.append(FileUploadResponse(path=path))
        return results

    @property
    def id(self) -> str:
        return self.container_name


def create_sandbox_backend(
    root_dir: str,
    virtual_mode: bool = True,  # noqa: FBT001,FBT002
    inherit_env: bool = True,   # noqa: FBT001,FBT002
) -> BaseSandbox:
    """创建 Sandbox Backend，Docker 不可用时自动降级到 LocalShellBackend。"""
    if _docker_available():
        try:
            return DockerSandboxBackend(
                root_dir=root_dir,
                env_allowlist=DEFAULT_ENV_ALLOWLIST,
            )
        except Exception as e:
            logger.warning(
                "Docker sandbox init failed (%s), falling back to LocalShellBackend", e
            )
    if sys.platform == "win32":
        from backend.infrastructure.runtime.services.windows_shell_backend import WindowsShellBackend
        return WindowsShellBackend(
            root_dir=root_dir,
            virtual_mode=virtual_mode,
            inherit_env=inherit_env,
        )
    return LocalShellBackend(
        root_dir=root_dir,
        virtual_mode=virtual_mode,
        inherit_env=inherit_env,
    )


__all__ = [
    "DockerSandboxBackend",
    "create_sandbox_backend",
    "DEFAULT_IMAGE",
    "DEFAULT_CONTAINER_NAME",
    "DEFAULT_ENV_ALLOWLIST",
]
