from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskContext:
    prompt: str
    input_file: str | None = None
    steps_taken: int = 0
    done: bool = False
    blocked: bool = False
    notes: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
