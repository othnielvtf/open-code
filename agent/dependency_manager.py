from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


class DependencyManager:
    """Checks and installs system packages on Ubuntu/macOS."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def has_command(self, command: str) -> bool:
        return shutil.which(command) is not None

    def ensure_command(
        self,
        command: str,
        package: str | None = None,
        *,
        task_id: str | None = None,
        reason: str = "",
    ) -> tuple[bool, str, dict]:
        if self.has_command(command):
            event = {
                "task_id": task_id,
                "command": command,
                "package": package or command,
                "reason": reason,
                "installer": "none",
                "already_present": True,
                "verified": True,
                "success": True,
            }
            return True, f"Command '{command}' already installed", event

        pkg = package or command
        os_name = platform.system().lower()

        if "linux" in os_name:
            ok, msg = self._install_with_apt(pkg)
            if not ok:
                event = {
                    "task_id": task_id,
                    "command": command,
                    "package": pkg,
                    "reason": reason,
                    "installer": "apt-get",
                    "already_present": False,
                    "verified": False,
                    "success": False,
                    "error": msg,
                }
                return False, msg, event
            installer = "apt-get"
        elif "darwin" in os_name:
            ok, msg = self._install_with_brew(pkg)
            if not ok:
                event = {
                    "task_id": task_id,
                    "command": command,
                    "package": pkg,
                    "reason": reason,
                    "installer": "brew",
                    "already_present": False,
                    "verified": False,
                    "success": False,
                    "error": msg,
                }
                return False, msg, event
            installer = "brew"
        else:
            msg = f"Unsupported OS '{os_name}' for auto-install of '{pkg}'"
            event = {
                "task_id": task_id,
                "command": command,
                "package": pkg,
                "reason": reason,
                "installer": "unknown",
                "already_present": False,
                "verified": False,
                "success": False,
                "error": msg,
            }
            return False, msg, event

        if not self.has_command(command):
            msg = f"Installed '{pkg}' but '{command}' still unavailable"
            event = {
                "task_id": task_id,
                "command": command,
                "package": pkg,
                "reason": reason,
                "installer": installer,
                "already_present": False,
                "verified": False,
                "success": False,
                "error": msg,
            }
            return False, msg, event

        event = {
            "task_id": task_id,
            "command": command,
            "package": pkg,
            "reason": reason,
            "installer": installer,
            "already_present": False,
            "verified": True,
            "success": True,
        }
        return True, f"Installed '{pkg}' for command '{command}'", event

    def _install_with_apt(self, package: str) -> tuple[bool, str]:
        update_result = subprocess.run(["apt-get", "update"], capture_output=True, text=True)
        if update_result.returncode != 0:
            return False, f"apt-get update failed: {update_result.stderr.strip()}"

        install_result = subprocess.run(["apt-get", "install", "-y", package], capture_output=True, text=True)
        if install_result.returncode != 0:
            return False, f"apt-get install failed for '{package}': {install_result.stderr.strip()}"
        return True, f"Installed '{package}' with apt-get"

    def _install_with_brew(self, package: str) -> tuple[bool, str]:
        if not self.has_command("brew"):
            return False, "Homebrew not found. Install Homebrew first: https://brew.sh/"

        install_result = subprocess.run(["brew", "install", package], capture_output=True, text=True)
        # `brew install` returns non-zero when already installed in some states; verify command after call.
        if install_result.returncode != 0 and "already installed" not in (install_result.stdout + install_result.stderr).lower():
            return False, f"brew install failed for '{package}': {(install_result.stderr or install_result.stdout).strip()}"
        return True, f"Installed '{package}' with brew"
