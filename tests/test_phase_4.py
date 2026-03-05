import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.capability_router import CapabilityRouter
from agent.executor import AgentExecutor
from agent.audio_processor import AudioProcessor
from agent.memory_manager import MemoryManager
from agent.tool_generator import ToolGenerator


class _ProcResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Phase4WorkflowTests(unittest.TestCase):
    def test_router_treats_webm_input_as_audio_transcription(self):
        with tempfile.TemporaryDirectory() as td:
            router = CapabilityRouter(Path(td))
            route = router.route("please process this", input_file="/tmp/sample.webm")
            self.assertEqual(route, "audio_transcription")

    def test_tool_generator_status_and_generic_fallback_not_youtube_biased(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tg = ToolGenerator(root, llm_client=None)

            path, status = tg.generate_tool(
                route="rest_api_scaffold",
                prompt="build rest api helper",
                tool_name="rest_api_dynamic",
            )
            self.assertEqual(status, "template_tool_generated")
            text = path.read_text(encoding="utf-8")
            self.assertIn("Generic task helper tool", text)
            self.assertNotIn("yt-dlp", text)

    def test_consensus_marks_degraded_on_partial_provider_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mm = MemoryManager(root)
            ex = AgentExecutor(project_root=root, memory_manager=mm)
            result = ex._select_consensus_result(
                [{"provider": "coingecko", "date": "2026-03-03", "currency": "USD", "price": 123.45}],
                attempted=3,
                failures=2,
            )
            self.assertTrue(result["degraded_confidence"])
            self.assertEqual(result["confidence"], "degraded")

    def test_provider_reliability_updates_counts_and_scores(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mem = root / "state" / "memory"
            mem.mkdir(parents=True, exist_ok=True)
            (mem / "ProviderReliability.md").write_text("# ProviderReliability.md\n\n## Crypto Providers\n", encoding="utf-8")
            mm = MemoryManager(root)

            mm.update_provider_status("coingecko", "healthy", task_id="t1")
            mm.update_provider_status("coingecko", "healthy", task_id="t2")
            mm.update_provider_status("coingecko", "degraded", task_id="t3")

            scores = mm.get_provider_scores()
            self.assertIn("coingecko", scores)
            self.assertAlmostEqual(scores["coingecko"], 2 / 3, places=3)

    def test_audio_processor_inspect_and_prepare(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            in_file = root / "sample.xyz"
            in_file.write_bytes(b"fake")
            artifacts = root / "artifacts"
            ap = AudioProcessor()

            ffprobe_json = '{"streams":[{"codec_type":"audio","codec_name":"pcm_s16le","channels":1,"sample_rate":"16000"}],"format":{"duration":"1.23"}}'

            with patch("subprocess.run") as run:
                run.side_effect = [
                    _ProcResult(0, stdout=ffprobe_json),
                    _ProcResult(0, stdout="ok"),
                ]
                info = ap.inspect(in_file)
                self.assertEqual(info["codec"], "pcm_s16le")
                out = ap.prepare_for_whisper(in_file, artifacts)
                self.assertTrue(str(out).endswith("normalized_sample.wav"))


if __name__ == "__main__":
    unittest.main()
