import json
import tempfile
import unittest
from pathlib import Path

from agent.executor import AgentExecutor
from agent.memory_manager import MemoryManager
from agent.redaction import Redactor
from agent.retry_policy import RetryPolicy
from agent.command_runner import CommandRunner
from agent.command_runner import CommandResult


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

    def test_identity_route_asks_for_name_when_unset_and_persists_when_set(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state" / "memory").mkdir(parents=True, exist_ok=True)
            (root / "state" / "brain.md").write_text("- `Identity.md`\n", encoding="utf-8")
            (root / "state" / "memory" / "Identity.md").write_text(
                "# Identity\n\nname: \nessence: curious helper.\nawaiting_name: false\n", encoding="utf-8"
            )
            mm = MemoryManager(root)
            ex = AgentExecutor(project_root=root, memory_manager=mm)

            q1 = ex.run(prompt="What is your name?", max_steps=2)
            self.assertEqual(q1.get("route"), "identity")
            self.assertIn("Would you like to name me", (q1.get("response") or ""))
            id_state_1 = (root / "state" / "memory" / "Identity.md").read_text(encoding="utf-8")
            self.assertIn("awaiting_name: true", id_state_1)

            q2 = ex.run(prompt="Nova", max_steps=2)
            self.assertEqual(q2.get("route"), "identity")
            self.assertIn("Nova", (q2.get("response") or ""))
            id_state_2 = (root / "state" / "memory" / "Identity.md").read_text(encoding="utf-8")
            self.assertIn("name: Nova", id_state_2)
            self.assertIn("awaiting_name: false", id_state_2)

            q3 = ex.run(prompt="Who are you?", max_steps=2)
            self.assertIn("Nova", (q3.get("response") or ""))

    def test_network_ops_ping_executes_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state" / "memory").mkdir(parents=True, exist_ok=True)
            (root / "state" / "brain.md").write_text("- `Soul.md`\n", encoding="utf-8")
            (root / "state" / "memory" / "Soul.md").write_text("soul", encoding="utf-8")
            mm = MemoryManager(root)
            ex = AgentExecutor(project_root=root, memory_manager=mm)

            ex.runner.run = lambda cmd, timeout=120: CommandResult(  # type: ignore[method-assign]
                command=" ".join(cmd) if isinstance(cmd, list) else str(cmd),
                returncode=0,
                stdout="PING google.com (142.250.0.0): 56 data bytes",
                stderr="",
                blocked=False,
                block_reason=None,
            )

            out = ex.run(prompt="can you ping google.com", max_steps=3)
            self.assertEqual(out.get("route"), "network_ops")
            self.assertTrue(out.get("done"))
            self.assertIn("Ping completed successfully", out.get("response") or "")
            result = out.get("data", {}).get("network_command_result", {})
            self.assertEqual(result.get("returncode"), 0)


if __name__ == "__main__":
    unittest.main()
