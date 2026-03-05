import json
import tempfile
import unittest
from pathlib import Path

from agent.memory_manager import MemoryManager


class Phase2MemoryTests(unittest.TestCase):
    def test_loads_canonical_state_brain(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = root / "state"
            mem = state / "memory"
            mem.mkdir(parents=True, exist_ok=True)

            (state / "brain.md").write_text("- `Soul.md`\n- `Persona.md`\n", encoding="utf-8")
            (mem / "Soul.md").write_text("soul", encoding="utf-8")
            (mem / "Persona.md").write_text("persona", encoding="utf-8")

            mm = MemoryManager(root)
            bundle = mm.load_brain_bundle()
            self.assertIn("brain.md", bundle)
            self.assertIn("Soul.md", bundle)
            self.assertIn("Persona.md", bundle)

    def test_immutable_files_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mem = root / "state" / "memory"
            mem.mkdir(parents=True, exist_ok=True)
            (mem / "Directives.md").write_text("doctrine", encoding="utf-8")
            mm = MemoryManager(root)
            with self.assertRaises(PermissionError):
                mm.update_memory_doc("Directives.md", "new", mode="replace", reason="test")

    def test_append_only_policy_for_persona(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mem = root / "state" / "memory"
            mem.mkdir(parents=True, exist_ok=True)
            (mem / "Persona.md").write_text("# Persona\n", encoding="utf-8")
            mm = MemoryManager(root)
            with self.assertRaises(PermissionError):
                mm.update_memory_doc("Persona.md", "overwrite", mode="replace", reason="test")

    def test_memory_update_pipeline_logs_events(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mem = root / "state" / "memory"
            mem.mkdir(parents=True, exist_ok=True)
            (mem / "Persona.md").write_text("# Persona\n", encoding="utf-8")
            mm = MemoryManager(root)
            mm.update_memory_doc("Persona.md", "- 2026-03-05: snapshot\n", mode="append", task_id="task_x", reason="persona_snapshot")

            log_path = root / "logs" / "memory_updates.jsonl"
            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(lines), 1)
            record = json.loads(lines[-1])
            self.assertEqual(record["task_id"], "task_x")
            self.assertEqual(record["target"], "Persona.md")
            self.assertEqual(record["mode"], "append")


if __name__ == "__main__":
    unittest.main()
