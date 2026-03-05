from __future__ import annotations

import json
from pathlib import Path


class CapabilityRegistry:
    """Persists reusable capabilities to JSON and Markdown."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.json_path = project_root / "state" / "capabilities.json"
        self.md_path = project_root / "state" / "capabilities.md"

    def register_or_update(self, capability: dict) -> None:
        data = self._load_json()
        items = data.get("capabilities", [])
        run_success = bool(capability.pop("run_success", False))

        existing = next((c for c in items if c.get("name") == capability.get("name")), None)
        if existing:
            existing.update(capability)
            existing["times_used"] = int(existing.get("times_used", 0)) + 1
            existing["success_count"] = int(existing.get("success_count", 0))
            existing["failure_count"] = int(existing.get("failure_count", 0))
            if run_success:
                existing["success_count"] = existing["success_count"] + 1
            else:
                existing["failure_count"] = existing["failure_count"] + 1
            self._update_score_fields(existing)
        else:
            capability = {
                **capability,
                "times_used": 1,
                "success_count": 1 if run_success else 0,
                "failure_count": 0 if run_success else 1,
            }
            self._update_score_fields(capability)
            items.append(capability)

        data["capabilities"] = items
        self.json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._write_markdown(items)

    def list_capabilities(self) -> list[dict]:
        data = self._load_json()
        return data.get("capabilities", [])

    def best_for_route(self, route: str) -> dict | None:
        candidates = [c for c in self.list_capabilities() if c.get("route") == route]
        if not candidates:
            return None
        return max(candidates, key=lambda c: float(c.get("reliability_score", 0.0)))

    def _load_json(self) -> dict:
        if not self.json_path.exists():
            return {"version": 1, "capabilities": []}
        try:
            return json.loads(self.json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"version": 1, "capabilities": []}

    def _write_markdown(self, capabilities: list[dict]) -> None:
        lines = [
            "# Capabilities Memory",
            "",
            "This file is a human-readable companion to `state/capabilities.json`.",
            "",
            "## Registered Capabilities",
            "",
        ]

        if not capabilities:
            lines.append("None yet.")
        else:
            for cap in capabilities:
                lines.append(f"### {cap.get('name', 'unnamed')}")
                lines.append(f"- route: `{cap.get('route', 'unknown')}`")
                lines.append(f"- purpose: {cap.get('purpose', 'n/a')}")
                lines.append(f"- last_status: `{cap.get('last_status', 'unknown')}`")
                lines.append(f"- times_used: {cap.get('times_used', 1)}")
                lines.append(f"- success_count: {cap.get('success_count', 0)}")
                lines.append(f"- failure_count: {cap.get('failure_count', 0)}")
                lines.append(f"- success_rate: {cap.get('success_rate', 0.0):.2f}")
                lines.append(f"- reliability_score: {cap.get('reliability_score', 0.0):.2f}")
                deps = cap.get("dependencies", [])
                lines.append(f"- dependencies: {', '.join(deps) if deps else 'none'}")
                if cap.get("last_tool"):
                    lines.append(f"- last_tool: `{cap.get('last_tool')}`")
                    lines.append(f"- last_tool_status: `{cap.get('last_tool_status', 'unknown')}`")
                lines.append("")

        self.md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _update_score_fields(self, capability: dict) -> None:
        success = int(capability.get("success_count", 0))
        failure = int(capability.get("failure_count", 0))
        total = max(1, success + failure)
        success_rate = success / total
        # Reliability score softly rewards higher sample sizes.
        capability["success_rate"] = round(success_rate, 4)
        capability["reliability_score"] = round(success_rate * min(1.0, total / 10), 4)
