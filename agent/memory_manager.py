from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re


class MemoryManager:
    """Loads master brain file and referenced memory documents."""

    STATE_DIR = Path("state")
    MEMORY_DIR = Path("state/memory")
    IMMUTABLE_FILES = {"Directives.md", "Soul.md"}
    APPEND_ONLY_FILES = {"Persona.md", "Failures.md"}

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.state_root = project_root / self.STATE_DIR
        self.memory_root = project_root / self.MEMORY_DIR
        self.logs_root = project_root / "logs"
        self.logs_root.mkdir(parents=True, exist_ok=True)
        self.memory_root.mkdir(parents=True, exist_ok=True)

    def load_brain_bundle(self) -> dict[str, str]:
        bundle: dict[str, str] = {}
        brain_path = self._get_master_brain_path()
        if not brain_path.exists():
            return bundle

        brain_text = brain_path.read_text(encoding="utf-8")
        bundle["brain.md"] = brain_text

        for name in self._extract_references(brain_text):
            p = self._resolve_reference_path(name)
            if p.exists():
                bundle[name] = p.read_text(encoding="utf-8")

        return bundle

    def _get_master_brain_path(self) -> Path:
        canonical = self.state_root / "brain.md"
        if canonical.exists():
            return canonical
        return self.memory_root / "brain.md"

    def _extract_references(self, brain_text: str) -> list[str]:
        refs: list[str] = []
        for line in brain_text.splitlines():
            m = re.match(r"^\s*-\s*`?([A-Za-z0-9_.-]+\.md)`?\s*$", line)
            if m:
                refs.append(m.group(1))
        # Keep deterministic defaults when references are missing.
        defaults = [
            "Soul.md",
            "Persona.md",
            "Directives.md",
            "Skills.md",
            "Failures.md",
            "ProviderReliability.md",
            "ToolBenchmarks.md",
        ]
        for d in defaults:
            if d not in refs:
                refs.append(d)
        return refs

    def append_persona_snapshot(self, note: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        line = f"- {timestamp}: {note}\n"
        self.update_memory_doc("Persona.md", line, mode="append", reason="persona_snapshot")

    def update_provider_status(self, provider_name: str, status: str, *, task_id: str | None = None) -> None:
        p = self._assert_mutable("ProviderReliability.md")
        existing = p.read_text(encoding="utf-8") if p.exists() else "# ProviderReliability.md\n\n## Crypto Providers\n"
        key = f"- {provider_name}:"
        lines = existing.splitlines()
        replaced = False
        success_count = 0
        failure_count = 0
        for i, line in enumerate(lines):
            if line.startswith(key):
                success_count, failure_count = self._parse_provider_counts(line)
                if status == "healthy":
                    success_count += 1
                else:
                    failure_count += 1
                score = round(success_count / max(1, success_count + failure_count), 4)
                lines[i] = f"{key} {status} | success={success_count} | failure={failure_count} | score={score}"
                replaced = True
                break
        if not replaced:
            if status == "healthy":
                success_count, failure_count = 1, 0
            else:
                success_count, failure_count = 0, 1
            score = round(success_count / max(1, success_count + failure_count), 4)
            lines.append(f"{key} {status} | success={success_count} | failure={failure_count} | score={score}")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._record_memory_update(
            task_id=task_id,
            target="ProviderReliability.md",
            mode="replace",
            reason=f"provider_status:{provider_name}:{status}",
        )

    def get_provider_scores(self) -> dict[str, float]:
        p = self.memory_root / "ProviderReliability.md"
        if not p.exists():
            return {}
        scores: dict[str, float] = {}
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*-\s*([a-zA-Z0-9_.-]+):.*score=([0-9.]+)", line)
            if m:
                scores[m.group(1)] = float(m.group(2))
        return scores

    def write_task_episode(self, task_id: str, content: str) -> None:
        episode_dir = self._assert_mutable("TaskEpisodes")
        episode_dir.mkdir(parents=True, exist_ok=True)
        path = episode_dir / f"{task_id}.md"
        path.write_text(content, encoding="utf-8")
        self._record_memory_update(
            task_id=task_id,
            target=f"TaskEpisodes/{task_id}.md",
            mode="replace",
            reason="task_episode",
        )

    def update_tool_benchmark(self, tool_name: str, status: str, *, task_id: str | None = None) -> None:
        path = self._assert_mutable("ToolBenchmarks.md")
        existing = path.read_text(encoding="utf-8") if path.exists() else "# ToolBenchmarks.md\n\n## Tool Stats\n"
        key = f"- {tool_name}:"
        lines = existing.splitlines()
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith(key):
                lines[i] = f"{key} {status}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{key} {status}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._record_memory_update(
            task_id=task_id,
            target="ToolBenchmarks.md",
            mode="replace",
            reason=f"tool_benchmark:{tool_name}:{status}",
        )

    def append_failure(self, note: str, *, task_id: str | None = None) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.update_memory_doc(
            "Failures.md",
            f"- {timestamp}: {note}\n",
            mode="append",
            task_id=task_id,
            reason="failure_append",
        )

    def register_tool_skill(
        self,
        *,
        route: str,
        tool_path: str,
        status: str,
        task_id: str | None = None,
    ) -> None:
        skills_path = self._assert_mutable("Skills.md")
        if not skills_path.exists():
            skills_path.write_text("# Skills.md\n\n", encoding="utf-8")

        existing = skills_path.read_text(encoding="utf-8")
        section_header = "## Generated Tools"
        entry = f"- route: `{route}` | tool: `{tool_path}` | status: `{status}`"

        if entry in existing:
            self._record_memory_update(
                task_id=task_id,
                target="Skills.md",
                mode="replace",
                reason=f"register_tool_skill:noop:{route}",
            )
            return

        if section_header not in existing:
            if not existing.endswith("\n"):
                existing += "\n"
            existing += f"\n{section_header}\n"
        updated = existing.rstrip() + "\n" + entry + "\n"
        skills_path.write_text(updated, encoding="utf-8")
        self._record_memory_update(
            task_id=task_id,
            target="Skills.md",
            mode="replace",
            reason=f"register_tool_skill:{route}",
        )

    def update_memory_doc(
        self,
        name: str,
        content: str,
        *,
        mode: str = "append",
        task_id: str | None = None,
        reason: str = "",
    ) -> Path:
        path = self._assert_mutable(name)
        if name in self.APPEND_ONLY_FILES and mode != "append":
            raise PermissionError(f"Memory file '{name}' is append-only by policy")

        if mode == "append":
            with path.open("a", encoding="utf-8") as f:
                f.write(content)
        elif mode == "replace":
            path.write_text(content, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported memory update mode: {mode}")

        self._record_memory_update(task_id=task_id, target=name, mode=mode, reason=reason)
        return path

    def _assert_mutable(self, name: str) -> Path:
        if name in self.IMMUTABLE_FILES:
            raise PermissionError(f"Memory file '{name}' is immutable by policy")
        return self.memory_root / name

    def _resolve_reference_path(self, ref: str) -> Path:
        ref = ref.strip()
        if "/" in ref:
            p = self.project_root / ref
            if p.exists():
                return p
        p = self.memory_root / ref
        if p.exists():
            return p
        # last resort under state root for future extensibility
        return self.state_root / ref

    def _record_memory_update(self, *, task_id: str | None, target: str, mode: str, reason: str) -> None:
        log_path = self.logs_root / "memory_updates.jsonl"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "target": target,
            "mode": mode,
            "reason": reason,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _parse_provider_counts(self, line: str) -> tuple[int, int]:
        success = 0
        failure = 0
        m1 = re.search(r"success=(\d+)", line)
        m2 = re.search(r"failure=(\d+)", line)
        if m1:
            success = int(m1.group(1))
        if m2:
            failure = int(m2.group(1))
        return success, failure
