from __future__ import annotations

import re


class Redactor:
    """Redacts common secret patterns from logs and outputs."""

    TOKEN_PATTERNS = [
        re.compile(r"sk-[A-Za-z0-9]{10,}"),
        re.compile(r"(OPENAI_API_KEY|OPENROUTER_API_KEY)\s*=\s*[^\s\n]+", re.IGNORECASE),
        re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}", re.IGNORECASE),
    ]

    def redact_text(self, value: str) -> str:
        text = value
        for pattern in self.TOKEN_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text

    def redact_list(self, values: list[str]) -> list[str]:
        return [self.redact_text(v) for v in values]
