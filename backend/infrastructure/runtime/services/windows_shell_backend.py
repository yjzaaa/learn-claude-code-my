"""Windows Shell Backend - Windows 命令行后端

为 deepagents 提供 Windows 系统上的文件和命令执行支持。
直接继承 LocalShellBackend 复用文件操作，并重写 execute 以处理 Windows
命令行输出的 GBK/UTF-8 编码混用问题。
"""

from __future__ import annotations

import subprocess

from deepagents.backends.local_shell import LocalShellBackend
from deepagents.backends.protocol import ExecuteResponse


class WindowsShellBackend(LocalShellBackend):
    """Windows Shell 后端

    继承 LocalShellBackend 获得完整的文件操作能力，并覆盖 execute() 方法以
    兼容 Windows 中文环境下 shell 输出常见的 GBK/CP936 编码，避免 UTF-8
    解码失败导致 UnicodeDecodeError。
    """

    def __init__(
        self,
        root_dir: str,
        virtual_mode: bool = True,  # noqa: FBT001,FBT002
        inherit_env: bool = True,   # noqa: FBT001,FBT002
    ) -> None:
        super().__init__(
            root_dir=root_dir,
            virtual_mode=virtual_mode,
            inherit_env=inherit_env,
        )

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """执行 shell 命令，兼容 Windows 中文编码。"""
        if not command or not isinstance(command, str):
            return ExecuteResponse(
                output="Error: Command must be a non-empty string.",
                exit_code=1,
                truncated=False,
            )

        effective_timeout = timeout if timeout is not None else self._default_timeout
        if effective_timeout <= 0:
            msg = f"timeout must be positive, got {effective_timeout}"
            raise ValueError(msg)

        try:
            result = subprocess.run(  # noqa: S602
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
                # 优先尝试 UTF-8，再尝试中文 Windows 常用编码
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
            if timeout is not None:
                msg = (
                    f"Error: Command timed out after {effective_timeout} seconds "
                    "(custom timeout). The command may be stuck or require more time."
                )
            else:
                msg = (
                    f"Error: Command timed out after {effective_timeout} seconds. "
                    "For long-running commands, re-run using the timeout parameter."
                )
            return ExecuteResponse(
                output=msg,
                exit_code=124,
                truncated=False,
            )
        except Exception as e:  # noqa: BLE001
            return ExecuteResponse(
                output=f"Error executing command ({type(e).__name__}): {e}",
                exit_code=1,
                truncated=False,
            )


__all__ = ["WindowsShellBackend"]
