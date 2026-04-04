"""Windows-compatible shell backend with proper encoding handling."""
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from deepagents.backends.local_shell import LocalShellBackend, DEFAULT_EXECUTE_TIMEOUT
from deepagents.backends.protocol import ExecuteResponse

if TYPE_CHECKING:
    from pathlib import Path


class WindowsShellBackend(LocalShellBackend):
    """LocalShellBackend with Windows encoding support.
    
    Fixes UnicodeDecodeError when Windows shell outputs GBK encoded characters.
    """

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Execute shell command with proper encoding handling for Windows."""
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
            # Use bytes mode to avoid automatic decoding
            result = subprocess.run(
                command,
                check=False,
                shell=True,
                capture_output=True,
                text=False,  # Get bytes instead of str
                timeout=effective_timeout,
                env=self._env,
                cwd=str(self.cwd),
            )

            # Try to decode with multiple encodings
            def decode_bytes(data: bytes) -> str:
                if not data:
                    return ""
                # Try UTF-8 first
                try:
                    return data.decode('utf-8')
                except UnicodeDecodeError:
                    pass
                # Try GBK (Chinese Windows)
                try:
                    return data.decode('gbk')
                except UnicodeDecodeError:
                    pass
                # Try system default encoding
                try:
                    import locale
                    return data.decode(locale.getpreferredencoding())
                except UnicodeDecodeError:
                    pass
                # Fallback: replace invalid bytes
                return data.decode('utf-8', errors='replace')

            stdout = decode_bytes(result.stdout)
            stderr = decode_bytes(result.stderr)

            # Combine stdout and stderr
            output_parts = []
            if stdout:
                output_parts.append(stdout)
            if stderr:
                stderr_lines = stderr.strip().split("\n")
                output_parts.extend(f"[stderr] {line}" for line in stderr_lines)

            output = "\n".join(output_parts) if output_parts else "<no output>"

            # Check for truncation
            truncated = False
            if len(output) > self._max_output_bytes:
                output = output[: self._max_output_bytes]
                output += f"\n\n... Output truncated at {self._max_output_bytes} bytes."
                truncated = True

            # Add exit code info if non-zero
            if result.returncode != 0:
                output = f"{output.rstrip()}\n\nExit code: {result.returncode}"

            return ExecuteResponse(
                output=output,
                exit_code=result.returncode,
                truncated=truncated,
            )

        except subprocess.TimeoutExpired:
            if timeout is not None:
                msg = f"Error: Command timed out after {effective_timeout} seconds (custom timeout). The command may be stuck or require more time."
            else:
                msg = f"Error: Command timed out after {effective_timeout} seconds. For long-running commands, re-run using the timeout parameter."
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
