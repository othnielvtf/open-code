from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence

from agent.safety_policy import SafetyPolicy


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    blocked: bool = False
    block_reason: str | None = None


class CommandRunner:
    def __init__(self, policy: SafetyPolicy | None = None) -> None:
        self.policy = policy or SafetyPolicy()

    def run(self, command: str | Sequence[str], timeout: int = 120) -> CommandResult:
        command_str = command if isinstance(command, str) else " ".join(command)
        allowed, reason = self.policy.is_allowed(command_str)
        if not allowed:
            return CommandResult(
                command=command_str,
                returncode=126,
                stdout="",
                stderr="",
                blocked=True,
                block_reason=reason,
            )

        if isinstance(command, str):
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            proc = subprocess.run(list(command), shell=False, capture_output=True, text=True, timeout=timeout)
        return CommandResult(
            command=command_str,
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            blocked=False,
            block_reason=None,
        )
