from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillRecord:
    name: str
    source: str
    summary: str


class SkillDiscovery:
    """Discovers local skill markdown files and extracts short summaries."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.skills_dir = project_root / "skills"
        self.memory_skills = project_root / "state" / "memory" / "Skills.md"

    def discover(self) -> list[SkillRecord]:
        records: list[SkillRecord] = []

        if self.memory_skills.exists():
            text = self.memory_skills.read_text(encoding="utf-8")
            for block in self._split_sections(text):
                records.append(
                    SkillRecord(
                        name=block["title"],
                        source=str(self.memory_skills),
                        summary=block["summary"],
                    )
                )

        if self.skills_dir.exists():
            for p in sorted(self.skills_dir.glob("*.md")):
                text = p.read_text(encoding="utf-8")
                summary = self._first_non_header_line(text)
                records.append(SkillRecord(name=p.stem, source=str(p), summary=summary))

        return records

    def _split_sections(self, text: str) -> list[dict[str, str]]:
        sections: list[dict[str, str]] = []
        current_title: str | None = None
        current_lines: list[str] = []

        for line in text.splitlines():
            if line.startswith("## "):
                if current_title:
                    sections.append({"title": current_title, "summary": self._summary_from_lines(current_lines)})
                current_title = line.replace("## ", "").strip()
                current_lines = []
                continue
            if current_title is not None:
                current_lines.append(line)

        if current_title:
            sections.append({"title": current_title, "summary": self._summary_from_lines(current_lines)})
        return sections

    def _summary_from_lines(self, lines: list[str]) -> str:
        for line in lines:
            s = line.strip()
            if s and not s.startswith("#"):
                return s[:180]
        return "No summary"

    def _first_non_header_line(self, text: str) -> str:
        for line in text.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                return s[:180]
        return "No summary"
