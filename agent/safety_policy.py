from __future__ import annotations


class SafetyPolicy:
    """Simple command safety policy for autonomous execution."""

    def __init__(self) -> None:
        self.blocked_patterns = [
            "rm -rf /",
            "mkfs",
            "shutdown",
            "reboot",
            "> /dev/sd",
            ":(){:|:&};:",
        ]

    def is_allowed(self, command: str) -> tuple[bool, str]:
        lower = command.lower()
        for pattern in self.blocked_patterns:
            if pattern in lower:
                return False, f"Blocked by safety policy pattern: {pattern}"
        return True, "allowed"
