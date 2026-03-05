import tempfile
import unittest
from pathlib import Path

from agent.memory_manager import MemoryManager
from agent.tool_generator import ToolGenerator


class Phase3CapabilityTests(unittest.TestCase):
    def test_tool_generator_produces_valid_tool(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tg = ToolGenerator(root, llm_client=None)
            tool_path, status = tg.generate_tool(
                route="youtube_download",
                prompt="download youtube video",
                tool_name="download_youtube_dynamic",
            )
            self.assertTrue(tool_path.exists())
            self.assertIn(
                status,
                {
                    "llm_tool_generated",
                    "template_tool_generated",
                    "existing_tool_reused",
                    "invalid_generated_tool_fallback_template",
                    "invalid_generated_tool_fallback_generic",
                },
            )

    def test_register_tool_skill_updates_skills_md_idempotently(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mem = root / "state" / "memory"
            mem.mkdir(parents=True, exist_ok=True)
            (mem / "Skills.md").write_text("# Skills.md\n\n## Audio\n- a\n", encoding="utf-8")

            mm = MemoryManager(root)
            mm.register_tool_skill(
                route="youtube_download",
                tool_path="/tmp/tool.py",
                status="llm_tool_generated",
                task_id="task_1",
            )
            mm.register_tool_skill(
                route="youtube_download",
                tool_path="/tmp/tool.py",
                status="llm_tool_generated",
                task_id="task_1",
            )

            text = (mem / "Skills.md").read_text(encoding="utf-8")
            self.assertIn("## Generated Tools", text)
            self.assertEqual(text.count("route: `youtube_download` | tool: `/tmp/tool.py` | status: `llm_tool_generated`"), 1)


if __name__ == "__main__":
    unittest.main()
