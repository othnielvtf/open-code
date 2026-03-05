from __future__ import annotations

import subprocess
from pathlib import Path


class ToolValidator:
    """Validates generated tool scripts before execution."""

    def validate_python_tool(self, path: Path) -> tuple[bool, str]:
        compile_cmd = ["python3", "-m", "py_compile", str(path)]
        compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if compile_result.returncode != 0:
            return False, f"py_compile failed: {compile_result.stderr.strip() or compile_result.stdout.strip()}"

        smoke_cmd = ["python3", str(path), "--help"]
        smoke_result = subprocess.run(smoke_cmd, capture_output=True, text=True)
        if smoke_result.returncode != 0:
            return False, f"--help smoke test failed: {smoke_result.stderr.strip() or smoke_result.stdout.strip()}"

        return True, "validation_passed"
