from __future__ import annotations

import re
from pathlib import Path

from agent.tool_validator import ToolValidator


class ToolGenerator:
    """Generates small reusable tools when no existing capability works."""

    def __init__(self, project_root: Path, llm_client=None) -> None:
        self.project_root = project_root
        self.tools_dir = project_root / "tools"
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.llm_client = llm_client
        self.validator = ToolValidator()

    def generate_tool(self, route: str, prompt: str, tool_name: str) -> tuple[Path, str]:
        path = self.tools_dir / f"{tool_name}.py"
        if path.exists():
            return path, "existing_tool_reused"

        code, source = self._build_code(route, prompt)
        path.write_text(code, encoding="utf-8")
        path.chmod(0o755)
        ok, reason = self.validator.validate_python_tool(path)
        if not ok:
            path.unlink(missing_ok=True)
            fallback = self._get_route_template_path(route)
            if fallback:
                return fallback, f"invalid_generated_tool_fallback_template: {reason}"
            return self.ensure_generic_tool(), f"invalid_generated_tool_fallback_generic: {reason}"
        status = "llm_tool_generated" if source == "llm" else "template_tool_generated"
        return path, status

    def ensure_youtube_tool(self) -> Path:
        path = self.tools_dir / "download_youtube.py"
        if path.exists():
            return path

        code = '''#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download YouTube video via yt-dlp")
    parser.add_argument("url")
    parser.add_argument("--out-dir", default="artifacts")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo+bestaudio/best",
        "-o",
        str(out_dir / "%(title)s.%(ext)s"),
        args.url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr or "yt-dlp failed")

    print("download_complete")


if __name__ == "__main__":
    main()
'''
        path.write_text(code, encoding="utf-8")
        path.chmod(0o755)
        return path

    def ensure_generic_tool(self) -> Path:
        path = self.tools_dir / "generic_task_tool.py"
        if path.exists():
            return path
        code = '''#!/usr/bin/env python3
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Generic task helper tool")
    parser.add_argument("--task", default="")
    args = parser.parse_args()
    print(f"generic_tool_received_task={args.task}")


if __name__ == "__main__":
    main()
'''
        path.write_text(code, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _build_code(self, route: str, prompt: str) -> tuple[str, str]:
        if self.llm_client and getattr(self.llm_client, "is_configured", lambda: False)():
            try:
                raw = self.llm_client.generate_python_tool(
                    f"Route: {route}\nTask: {prompt}\n"
                    "Generate a route-appropriate Python CLI tool with argparse."
                )
                extracted = self._extract_python_block(raw)
                if extracted:
                    return extracted, "llm"
            except Exception:
                pass

        fallback = self._get_route_template_path(route)
        if fallback:
            return fallback.read_text(encoding="utf-8"), "template"
        return self.ensure_generic_tool().read_text(encoding="utf-8"), "template"

    def _extract_python_block(self, text: str) -> str | None:
        m = re.search(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if not m:
            return None
        return m.group(1).strip() + "\n"

    def _get_route_template_path(self, route: str) -> Path | None:
        if route == "youtube_download":
            return self.ensure_youtube_tool()
        if route == "general_reasoning":
            return self.ensure_generic_tool()
        return None
