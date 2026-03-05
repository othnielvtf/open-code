import json
import tempfile
import unittest
from pathlib import Path

from agent.executor import AgentExecutor
from agent.memory_manager import MemoryManager
from agent.redaction import Redactor
from agent.retry_policy import RetryPolicy
from agent.command_runner import CommandRunner


class Phase5HardeningTests(unittest.TestCase):
    def test_retry_policy_transient_and_terminal(self):
        rp = RetryPolicy()
        self.assertTrue(rp.should_retry(Exception("Connection timed out"), attempt=1))
        self.assertFalse(rp.should_retry(Exception("402 Client Error: Payment Required"), attempt=1))

    def test_redactor_masks_keys(self):
        r = Redactor()
        text = "OPENAI_API_KEY=sk-1234567890abcdef and Bearer sk-zzzzzzzzzzzz"
        out = r.redact_text(text)
        self.assertNotIn("sk-1234567890abcdef", out)
        self.assertNotIn("sk-zzzzzzzzzzzz", out)
        self.assertIn("[REDACTED]", out)

    def test_executor_redacts_notes_in_output_and_logs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # minimal structure
            (root / "state" / "memory").mkdir(parents=True, exist_ok=True)
            (root / "state" / "brain.md").write_text("- `Soul.md`\n", encoding="utf-8")
            (root / "state" / "memory" / "Soul.md").write_text("soul", encoding="utf-8")
            (root / "logs").mkdir(parents=True, exist_ok=True)
            mm = MemoryManager(root)
            ex = AgentExecutor(project_root=root, memory_manager=mm)

            # inject a secret-like note and force log write via run path
            result = ex.run(prompt="test sk-123456789012345", max_steps=1)
            out_notes = "\n".join(result.get("notes", []))
            self.assertNotIn("sk-123456789012345", out_notes)

            lines = (root / "logs" / "tasks.log.jsonl").read_text(encoding="utf-8").splitlines()
            rec = json.loads(lines[-1])
            log_notes = "\n".join(rec.get("notes", []))
            self.assertNotIn("sk-123456789012345", log_notes)

    def test_executor_redacts_analysis_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state" / "memory").mkdir(parents=True, exist_ok=True)
            (root / "state" / "brain.md").write_text("- `Soul.md`\n", encoding="utf-8")
            (root / "state" / "memory" / "Soul.md").write_text("soul", encoding="utf-8")
            mm = MemoryManager(root)
            ex = AgentExecutor(project_root=root, memory_manager=mm)
            out = ex.run(prompt="show sk-123456789012345 token", max_steps=1)
            analysis = str(out.get("data", {}).get("analysis", ""))
            self.assertNotIn("sk-123456789012345", analysis)

    def test_command_runner_supports_argv_path(self):
        runner = CommandRunner()
        result = runner.run(["python3", "-c", "print('ok')"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("ok", result.stdout)

    def test_self_extension_scaffold_creates_interface_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state" / "memory").mkdir(parents=True, exist_ok=True)
            (root / "state" / "brain.md").write_text("- `Soul.md`\n- `Skills.md`\n", encoding="utf-8")
            (root / "state" / "memory" / "Soul.md").write_text("soul", encoding="utf-8")
            (root / "state" / "memory" / "Skills.md").write_text("# Skills.md\n", encoding="utf-8")
            mm = MemoryManager(root)
            ex = AgentExecutor(project_root=root, memory_manager=mm)

            out = ex.run(prompt="Please create a telegram bot interface for this agent", max_steps=4)
            self.assertEqual(out.get("route"), "self_extension")
            self.assertTrue(out.get("done"))
            generated = out.get("data", {}).get("generated_tool_attempted")
            self.assertTrue(generated and Path(generated).exists())


if __name__ == "__main__":
    unittest.main()
