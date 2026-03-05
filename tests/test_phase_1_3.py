import json
import tempfile
import unittest
from pathlib import Path

from agent.capability_registry import CapabilityRegistry
from agent.llm_client import LLMClient
from agent.memory_manager import MemoryManager
from agent.safety_policy import SafetyPolicy
from agent.skill_discovery import SkillDiscovery


class Phase123Tests(unittest.TestCase):
    def test_llm_client_falls_back_when_model_invalid(self):
        class _Msg:
            content = "ok"

        class _Choice:
            message = _Msg()

        class _Usage:
            prompt_tokens = 1
            completion_tokens = 1
            total_tokens = 2

        class _Resp:
            choices = [_Choice()]
            usage = _Usage()

        class _ChatCompletions:
            def __init__(self):
                self.calls = 0

            def create(self, model, messages):
                self.calls += 1
                if self.calls == 1:
                    raise Exception("not a valid model ID")
                return _Resp()

        class _Chat:
            def __init__(self):
                self.completions = _ChatCompletions()

        class _Client:
            def __init__(self):
                self.chat = _Chat()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            llm = LLMClient(root)
            llm.client = _Client()
            text, meta = llm.reason("hello", {}, model_override="invalid/model")
            self.assertEqual(text, "ok")
            self.assertIn("model", meta)
            self.assertEqual(meta.get("effective_model"), "openrouter/auto")

    def test_memory_manager_extracts_brain_refs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mem = root / "state" / "memory"
            mem.mkdir(parents=True, exist_ok=True)
            (mem / "brain.md").write_text("- `Soul.md`\n- `Persona.md`\n", encoding="utf-8")
            (mem / "Soul.md").write_text("soul", encoding="utf-8")
            (mem / "Persona.md").write_text("persona", encoding="utf-8")
            mm = MemoryManager(root)
            bundle = mm.load_brain_bundle()
            self.assertIn("brain.md", bundle)
            self.assertIn("Soul.md", bundle)
            self.assertIn("Persona.md", bundle)

    def test_safety_policy_blocks_destructive_pattern(self):
        policy = SafetyPolicy()
        allowed, reason = policy.is_allowed("rm -rf /")
        self.assertFalse(allowed)
        self.assertIn("Blocked", reason)

    def test_capability_registry_scores(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state").mkdir(parents=True, exist_ok=True)
            reg = CapabilityRegistry(root)
            reg.register_or_update({
                "name": "x",
                "route": "demo",
                "purpose": "demo",
                "last_status": "completed",
                "dependencies": [],
                "run_success": True,
            })
            reg.register_or_update({
                "name": "x",
                "route": "demo",
                "purpose": "demo",
                "last_status": "blocked",
                "dependencies": [],
                "run_success": False,
            })
            data = json.loads((root / "state" / "capabilities.json").read_text(encoding="utf-8"))
            cap = data["capabilities"][0]
            self.assertEqual(cap["success_count"], 1)
            self.assertEqual(cap["failure_count"], 1)
            self.assertAlmostEqual(cap["success_rate"], 0.5, places=3)

    def test_skill_discovery_reads_memory_skills(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mem = root / "state" / "memory"
            mem.mkdir(parents=True, exist_ok=True)
            (mem / "Skills.md").write_text("## Audio\nTranscribe audio files\n", encoding="utf-8")
            sd = SkillDiscovery(root)
            found = sd.discover()
            self.assertTrue(any(s.name == "Audio" for s in found))


if __name__ == "__main__":
    unittest.main()
