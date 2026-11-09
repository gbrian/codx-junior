"""
SSH shell access for computer sessions.

VNC gives the AI the screen; it does not give it a terminal.  Tasks such as
"build the iOS app" need both: Xcode/Simulator on screen and ``xcodebuild`` in a
shell.  Remote sessions can therefore carry an SSH endpoint (host, user, key or
password) used by ``computer_action(action="run_command")``.

The implementation shells out to the system OpenSSH client (already present in
the API image) instead of adding ``paramiko``/``asyncssh`` as a dependency:

* key auth uses ``-i`` and ``BatchMode=yes``;
* password auth uses ``sshpass -e`` when installed (the password is passed in
  the environment, never on the command line);
* host keys are accepted on first use (``StrictHostKeyChecking=accept-new``),
  which is the same trust model as opening the VNC connection.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

MAX_OUTPUT = 20000


class SSHError(RuntimeError):
    """SSH is not configured or the command failed to start."""


class SSHRunner:
    """Run commands on a remote computer over SSH."""

    def __init__(
        self,
        host: Optional[str],
        user: Optional[str] = None,
        port: int = 22,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        os_kind: str = "remote",
        timeout: float = 60,
    ):
        self.host = (host or "").strip()
        self.user = (user or "").strip()
        self.port = int(port or 22)
        self.key_path = (key_path or "").strip()
        self.password = password or ""
        self.os_kind = (os_kind or "remote").lower()
        self.timeout = float(timeout or 60)

    @property
    def configured(self) -> bool:
        """True when a host is configured."""
        return bool(self.host)

    def _target(self) -> str:
        return f"{self.user}@{self.host}" if self.user else self.host

    def _wrap(self, command: str) -> str:
        """Wrap a command in the remote OS shell."""
        command = str(command or "")
        if self.os_kind == "windows":
            return f'powershell -NoProfile -NonInteractive -Command {_powershell_quote(command)}'
        if self.os_kind == "macos":
            return f"/bin/zsh -lc {_shell_quote(command)}"
        return f"/bin/bash -lc {_shell_quote(command)}"

    def run(self, command: str, timeout: float = None) -> Dict[str, Any]:
        """Execute *command* over SSH and return stdout/stderr/exit code."""
        if not self.configured:
            raise SSHError("This session has no SSH host configured")
        if self.host.startswith("-") or (self.user and self.user.startswith("-")):
            raise SSHError("Invalid SSH host/user")
        if not shutil.which("ssh"):
            raise SSHError("The ssh client is not installed in the API image")
        timeout = max(1.0, float(timeout or self.timeout))
        args: List[str] = [
            "ssh",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=2",
            "-p", str(self.port),
        ]
        env = dict(os.environ)
        if self.key_path:
            if not os.path.isfile(os.path.expanduser(self.key_path)):
                raise SSHError(f"SSH key not found: {self.key_path}")
            args.extend(["-i", os.path.expanduser(self.key_path)])
            args.extend(["-o", "BatchMode=yes"])
        elif self.password:
            if not shutil.which("sshpass"):
                raise SSHError(
                    "Password SSH requires sshpass in the API image; use an SSH key instead"
                )
            args = ["sshpass", "-e", *args]
            env["SSHPASS"] = self.password
        else:
            args.extend(["-o", "BatchMode=yes"])
        args.extend([self._target(), "--", self._wrap(command)])
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired as ex:
            raise SSHError(f"SSH command timed out after {timeout}s") from ex
        return {
            "exit_code": result.returncode,
            "stdout": (result.stdout or "")[:MAX_OUTPUT],
            "stderr": (result.stderr or "")[:MAX_OUTPUT],
            "truncated": len(result.stdout or "") > MAX_OUTPUT,
            "host": self.host,
        }


def _shell_quote(value: str) -> str:
    """Quote a string for a POSIX shell."""
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def _powershell_quote(value: str) -> str:
    """Quote a string for PowerShell's -Command."""
    return "'" + str(value).replace("'", "''") + "'"
