from __future__ import annotations

import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent.audio_processor import AudioProcessor
from agent.capability_router import CapabilityRouter
from agent.capability_registry import CapabilityRegistry
from agent.command_runner import CommandRunner
from agent.dependency_manager import DependencyManager
from agent.llm_client import LLMClient
from agent.planner import Planner
from agent.redaction import Redactor
from agent.retry_policy import RetryPolicy
from agent.skill_discovery import SkillDiscovery
from agent.tool_generator import ToolGenerator
from agent.types import TaskContext
from providers.crypto_coingecko import CryptoCoingeckoProvider
from providers.crypto_coinpaprika import CryptoCoinpaprikaProvider
from providers.crypto_binance import CryptoBinanceProvider
from providers.transcription_openai import OpenAIWhisperProvider


class AgentExecutor:
    def __init__(self, project_root: Path, memory_manager) -> None:
        self.project_root = project_root
        self.memory_manager = memory_manager
        self.router = CapabilityRouter(project_root)
        self.deps = DependencyManager(project_root)
        self.planner = Planner()
        self.llm = LLMClient(project_root)
        self.capabilities = CapabilityRegistry(project_root)
        self.runner = CommandRunner()
        self.tool_generator = ToolGenerator(project_root, llm_client=self.llm)
        self.skill_discovery = SkillDiscovery(project_root)
        self.audio_processor = AudioProcessor()
        self.retry_policy = RetryPolicy()
        self.redactor = Redactor()

        self.crypto_providers = [
            CryptoCoingeckoProvider(),
            CryptoCoinpaprikaProvider(),
            CryptoBinanceProvider(),
        ]
        self.whisper_provider = OpenAIWhisperProvider(project_root)

    def run(
        self,
        prompt: str,
        input_file: str | None = None,
        max_steps: int = 8,
        model_override: str | None = None,
    ) -> dict:
        task_id = f"task_{uuid4().hex[:8]}"
        started = datetime.now(timezone.utc).isoformat()
        memory_bundle = self.memory_manager.load_brain_bundle()
        route = self.router.route(prompt, input_file)
        ctx = TaskContext(prompt=prompt, input_file=input_file)
        ctx.data["task_id"] = task_id
        ctx.data["install_events"] = []
        ctx.data["llm_trace"] = []
        ctx.data["llm_usage"] = {
            "model": model_override or self.llm.model,
            "calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        }
        self._bootstrap_context(route, ctx)

        # Prime reasoning with brain context.
        if self.llm.is_configured():
            try:
                analysis, meta = self.llm.reason(prompt, memory_bundle, model_override=model_override)
                ctx.data["analysis"] = analysis
                self._record_llm_meta(ctx, meta, stage="initial_analysis")
            except Exception as exc:  # noqa: BLE001
                ctx.notes.append(f"LLM reasoning unavailable: {exc}")
        else:
            ctx.notes.append("LLM reasoning unavailable: OPENROUTER_API_KEY not configured")

        while ctx.steps_taken < max_steps and not (ctx.done or ctx.blocked):
            self._llm_step_reflection(route, ctx, memory_bundle, model_override=model_override, stage="before_action")
            action = self.planner.next_action(route, ctx)
            self._execute_action(route, action, ctx)
            self._llm_step_reflection(route, ctx, memory_bundle, model_override=model_override, stage="after_action")
            ctx.steps_taken += 1

        finished = datetime.now(timezone.utc).isoformat()
        self._append_task_log(started, finished, route, ctx)
        self._persist_learning(route, ctx)
        safe_notes = self.redactor.redact_list(ctx.notes)
        safe_data = self._redact_obj(ctx.data)

        return {
            "task_id": task_id,
            "route": route,
            "steps_taken": ctx.steps_taken,
            "done": ctx.done,
            "blocked": ctx.blocked,
            "notes": safe_notes,
            "data": safe_data,
        }

    def _execute_action(self, route: str, action: str, ctx: TaskContext) -> None:
        if action == "ensure_http":
            ok, msg, event = self.deps.ensure_command(
                "curl",
                "curl",
                task_id=ctx.data.get("task_id"),
                reason="HTTP capability required for provider API requests",
            )
            ctx.notes.append(msg)
            ctx.data["install_events"].append(event)
            if ok:
                ctx.data["http_ready"] = True
            else:
                ctx.blocked = True
            return

        if action == "query_crypto_providers":
            results: list[dict] = []
            provider_failures = 0
            for provider in self.crypto_providers:
                try:
                    result = self._run_with_retry(
                        lambda p=provider: p.get_historical_btc_price(ctx.prompt),
                        ctx=ctx,
                        label=f"provider_{provider.name}",
                    )
                    if result is not None:
                        results.append(result)
                        self.memory_manager.update_provider_status(
                            provider.name,
                            "healthy",
                            task_id=ctx.data.get("task_id"),
                        )
                except Exception as exc:  # noqa: BLE001
                    provider_failures += 1
                    self.memory_manager.update_provider_status(
                        provider.name,
                        "degraded",
                        task_id=ctx.data.get("task_id"),
                    )
                    ctx.notes.append(self.redactor.redact_text(f"Provider '{provider.name}' failed: {exc}"))
            if results:
                ctx.data["provider_results"] = results
                ctx.data["provider_result"] = self._select_consensus_result(
                    results,
                    attempted=len(self.crypto_providers),
                    failures=provider_failures,
                )
                ctx.data["provider_selection_reason"] = "weighted_consensus_by_price_and_reliability"
            else:
                ctx.blocked = True
                ctx.notes.append("All crypto providers failed")
            return

        if action == "ensure_video_stack":
            ok, msg, event = self.deps.ensure_command(
                "yt-dlp",
                "yt-dlp",
                task_id=ctx.data.get("task_id"),
                reason="Video download workflow requires yt-dlp",
            )
            ctx.notes.append(msg)
            ctx.data["install_events"].append(event)
            if ok:
                ctx.data["video_stack_ready"] = True
            else:
                ctx.blocked = True
            return

        if action == "run_youtube_download":
            url = self._extract_url(ctx.prompt)
            if not url:
                ctx.blocked = True
                ctx.notes.append("No valid URL found in prompt")
                return

            preferred_tool = ctx.data.get("preferred_tool")
            if preferred_tool:
                cmd = ["python3", str(preferred_tool), str(url), "--out-dir", str(self.project_root / "artifacts")]
                preferred_result = self.runner.run(cmd, timeout=1800)
                if preferred_result.returncode == 0:
                    ctx.data["download_result"] = {
                        "url": url,
                        "status": "completed",
                        "method": "preferred_capability_tool",
                        "tool_path": preferred_tool,
                    }
                    self.memory_manager.update_tool_benchmark(
                        Path(preferred_tool).name,
                        "execution_success",
                        task_id=ctx.data.get("task_id"),
                    )
                    return
                ctx.notes.append("Preferred capability tool failed, trying direct yt-dlp path")

            out_tpl = self.project_root / "artifacts" / "%(title)s.%(ext)s"
            cmd = ["yt-dlp", "-f", "bestvideo+bestaudio/best", "-o", str(out_tpl), str(url)]
            result = self.runner.run(cmd, timeout=1800)
            if result.blocked:
                ctx.blocked = True
                ctx.notes.append(f"Command blocked: {result.block_reason}")
                return
            if result.returncode == 0:
                ctx.data["download_result"] = {
                    "url": url,
                    "status": "completed",
                    "method": "yt-dlp",
                }
            else:
                tool_path, gen_status = self.tool_generator.generate_tool(
                    route="youtube_download",
                    prompt=ctx.prompt,
                    tool_name="download_youtube_dynamic",
                )
                ctx.data["generated_tool_attempted"] = str(tool_path)
                ctx.data["generated_tool_status"] = gen_status
                self.memory_manager.update_tool_benchmark(
                    Path(tool_path).name,
                    gen_status,
                    task_id=ctx.data.get("task_id"),
                )
                ctx.notes.append(f"Direct yt-dlp path failed, fallback to generated tool: {result.stderr[:300]}")
            return

        if action == "run_generated_youtube_tool":
            url = self._extract_url(ctx.prompt)
            tool_path = ctx.data.get("generated_tool_attempted")
            if not url or not tool_path:
                ctx.blocked = True
                ctx.notes.append("Generated tool fallback missing URL or tool path")
                return
            cmd = ["python3", str(tool_path), str(url), "--out-dir", str(self.project_root / "artifacts")]
            result = self.runner.run(cmd, timeout=1800)
            if result.blocked:
                ctx.blocked = True
                ctx.notes.append(f"Command blocked: {result.block_reason}")
                return
            if result.returncode == 0:
                ctx.data["download_result"] = {
                    "url": url,
                    "status": "completed",
                    "method": "generated_tool",
                    "tool_path": tool_path,
                }
                self.memory_manager.update_tool_benchmark(
                    Path(tool_path).name,
                    "execution_success",
                    task_id=ctx.data.get("task_id"),
                )
            else:
                ctx.blocked = True
                self.memory_manager.update_tool_benchmark(
                    Path(tool_path).name,
                    "execution_failed",
                    task_id=ctx.data.get("task_id"),
                )
                ctx.notes.append(f"Generated tool failed: {result.stderr[:300]}")
            return

        if action == "ensure_audio_stack":
            ok, msg, event = self.deps.ensure_command(
                "ffmpeg",
                "ffmpeg",
                task_id=ctx.data.get("task_id"),
                reason="Audio decode/transcription pipeline requires ffmpeg",
            )
            ctx.notes.append(msg)
            ctx.data["install_events"].append(event)
            if ok:
                ctx.data["audio_ready"] = True
            else:
                ctx.blocked = True
            return

        if action == "run_transcription":
            if not ctx.input_file:
                ctx.blocked = True
                ctx.notes.append("No input audio file provided")
                return
            try:
                input_path = Path(ctx.input_file)
                inspection = self.audio_processor.inspect(input_path)
                prepared_path = self.audio_processor.prepare_for_whisper(input_path, self.project_root / "artifacts")
                text = self._run_with_retry(
                    lambda: self.whisper_provider.transcribe(prepared_path),
                    ctx=ctx,
                    label="whisper_transcription",
                )
                transcript_path = self.project_root / "artifacts" / f"transcript_{int(datetime.now().timestamp())}.txt"
                transcript_path.write_text(text + "\n", encoding="utf-8")
                ctx.data["transcript"] = str(transcript_path)
                ctx.data["audio_inspection"] = inspection
                ctx.data["transcription_input"] = str(prepared_path)
                self.memory_manager.update_provider_status(
                    self.whisper_provider.name,
                    "healthy",
                    task_id=ctx.data.get("task_id"),
                )
            except Exception as exc:  # noqa: BLE001
                self.memory_manager.update_provider_status(
                    self.whisper_provider.name,
                    "degraded",
                    task_id=ctx.data.get("task_id"),
                )
                ctx.blocked = True
                ctx.notes.append(self.redactor.redact_text(f"Transcription failed: {exc}"))
            return

        if action == "scaffold_extension_interface":
            p = ctx.prompt.lower()
            generated_tools = self.project_root / "tools"
            generated_tools.mkdir(parents=True, exist_ok=True)

            if "telegram" in p:
                target = generated_tools / "telegram_interface.py"
                target.write_text(
                    """#!/usr/bin/env python3
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Agent Telegram interface is running.")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()


if __name__ == "__main__":
    main()
""",
                    encoding="utf-8",
                )
                target.chmod(0o755)
                ctx.data["generated_tool_attempted"] = str(target)
                ctx.data["generated_tool_status"] = "template_tool_generated"
                ctx.data["extension_type"] = "telegram"
                dep = "python-telegram-bot"
            else:
                target = generated_tools / "rest_api_interface.py"
                target.write_text(
                    """#!/usr/bin/env python3
from fastapi import FastAPI
from pydantic import BaseModel


class PromptIn(BaseModel):
    prompt: str


app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/task")
def task(inp: PromptIn):
    return {"status": "stub", "prompt": inp.prompt}
""",
                    encoding="utf-8",
                )
                target.chmod(0o755)
                ctx.data["generated_tool_attempted"] = str(target)
                ctx.data["generated_tool_status"] = "template_tool_generated"
                ctx.data["extension_type"] = "rest_api"
                dep = "fastapi"

            ctx.data["extension_dependency"] = dep
            ctx.data["extension_scaffolded"] = True
            self.memory_manager.update_tool_benchmark(target.name, "generated", task_id=ctx.data.get("task_id"))
            return

        if action == "test_extension_health":
            tool_path = ctx.data.get("generated_tool_attempted")
            if not tool_path:
                ctx.blocked = True
                ctx.notes.append("No scaffolded extension tool found")
                return
            result = self.runner.run(["python3", "-m", "py_compile", str(tool_path)], timeout=60)
            if result.returncode != 0:
                ctx.blocked = True
                ctx.notes.append(self.redactor.redact_text(f"Extension health check failed: {result.stderr[:300]}"))
                self.memory_manager.update_tool_benchmark(Path(tool_path).name, "health_check_failed", task_id=ctx.data.get("task_id"))
                return
            ctx.data["extension_health_checked"] = True
            self.memory_manager.update_tool_benchmark(Path(tool_path).name, "health_check_passed", task_id=ctx.data.get("task_id"))
            return

        if action == "analyze_prompt":
            ctx.data.setdefault("analysis", "No LLM analysis available")
            return

        if action == "finalize":
            ctx.done = True
            return

        ctx.notes.append(f"Unknown action: {action}")
        ctx.blocked = True

    def _append_task_log(self, started: str, finished: str, route: str, ctx: TaskContext) -> None:
        log_path = self.project_root / "logs" / "tasks.log.jsonl"
        redacted_notes = self.redactor.redact_list(ctx.notes)
        record = {
            "task_id": ctx.data.get("task_id"),
            "started_at": started,
            "finished_at": finished,
            "route": route,
            "prompt": self.redactor.redact_text(ctx.prompt),
            "input_file": ctx.input_file,
            "steps_taken": ctx.steps_taken,
            "done": ctx.done,
            "blocked": ctx.blocked,
            "install_events": ctx.data.get("install_events", []),
            "llm_usage": ctx.data.get("llm_usage", {}),
            "notes": redacted_notes,
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _persist_learning(self, route: str, ctx: TaskContext) -> None:
        capability_name = f"{route}_workflow"
        deps: list[str] = []
        if route == "crypto_price":
            deps = ["curl", "requests"]
        elif route == "audio_transcription":
            deps = ["ffmpeg", "openai"]
        elif route == "youtube_download":
            deps = ["yt-dlp"]
        elif route == "self_extension":
            deps = [str(ctx.data.get("extension_dependency", "unknown"))]

        self.capabilities.register_or_update(
            {
                "name": capability_name,
                "route": route,
                "purpose": f"Reusable workflow for route '{route}'",
                "last_status": "completed" if ctx.done else "blocked",
                "dependencies": deps,
                "last_tool": ctx.data.get("generated_tool_attempted"),
                "last_tool_status": ctx.data.get("generated_tool_status"),
                "run_success": bool(ctx.done and not ctx.blocked),
            }
        )
        if ctx.data.get("generated_tool_attempted"):
            self.memory_manager.register_tool_skill(
                route=route,
                tool_path=str(ctx.data.get("generated_tool_attempted")),
                status=str(ctx.data.get("generated_tool_status", "unknown")),
                task_id=ctx.data.get("task_id"),
            )

        if route == "general_reasoning":
            self.memory_manager.append_persona_snapshot("User asked for a general reasoning task.")

        note_lines = [f"- {n}" for n in ctx.notes] if ctx.notes else ["- none"]
        episode = [
            f"# {ctx.data.get('task_id', 'task')}",
            "",
            f"- route: `{route}`",
            f"- done: `{ctx.done}`",
            f"- blocked: `{ctx.blocked}`",
            f"- steps: `{ctx.steps_taken}`",
            "",
            "## Prompt",
            ctx.prompt,
            "",
            "## Notes",
            *note_lines,
        ]
        self.memory_manager.write_task_episode(ctx.data.get("task_id", "task"), "\n".join(episode) + "\n")
        if ctx.blocked:
            self.memory_manager.append_failure(
                self.redactor.redact_text(f"route={route} task={ctx.data.get('task_id')} notes={'; '.join(ctx.notes[:2])}"),
                task_id=ctx.data.get("task_id"),
            )

    def _select_consensus_result(self, results: list[dict], *, attempted: int, failures: int) -> dict:
        confidence = "high"
        degraded = False
        if len(results) == 1:
            chosen = results[0]
            if attempted > 1 or failures > 0:
                confidence = "degraded"
                degraded = True
            return {
                **chosen,
                "consensus": "single_source",
                "sample_size": 1,
                "providers_attempted": attempted,
                "provider_failures": failures,
                "confidence": confidence,
                "degraded_confidence": degraded,
            }

        prices = [float(r["price"]) for r in results]
        median_price = statistics.median(prices)
        provider_scores = self.memory_manager.get_provider_scores()
        weighted = []
        for r in results:
            score = provider_scores.get(str(r.get("provider")), 0.5)
            distance = abs(float(r["price"]) - median_price)
            weighted_score = score * 0.7 + (1 / (1 + distance)) * 0.3
            weighted.append((weighted_score, r))
        chosen = max(weighted, key=lambda x: x[0])[1]
        spread = max(prices) - min(prices)
        return {
            **chosen,
            "consensus": "multi_provider",
            "sample_size": len(results),
            "median_price": median_price,
            "spread": spread,
            "provider_scores": provider_scores,
            "providers_attempted": attempted,
            "provider_failures": failures,
            "confidence": "medium" if failures > 0 else "high",
            "degraded_confidence": failures > 0,
        }

    def _extract_url(self, text: str) -> str | None:
        m = re.search(r"https?://\S+", text)
        if not m:
            return None
        return m.group(0).rstrip(".,)")

    def _bootstrap_context(self, route: str, ctx: TaskContext) -> None:
        discovered = self.skill_discovery.discover()
        ctx.data["discovered_skills"] = [
            {"name": s.name, "source": s.source, "summary": s.summary} for s in discovered
        ]

        best_capability = self.capabilities.best_for_route(route)
        if best_capability:
            ctx.data["best_capability"] = best_capability.get("name")
            if best_capability.get("last_tool"):
                ctx.data["preferred_tool"] = best_capability["last_tool"]

    def _run_with_retry(self, fn, *, ctx: TaskContext, label: str):
        attempt = 1
        while True:
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                if not self.retry_policy.should_retry(exc, attempt):
                    raise
                delay = self.retry_policy.sleep_for_attempt(attempt)
                ctx.notes.append(self.redactor.redact_text(f"{label} retry attempt={attempt} delay={delay}s due_to={exc}"))
                attempt += 1

    def _llm_step_reflection(
        self,
        route: str,
        ctx: TaskContext,
        memory_bundle: dict[str, str],
        *,
        model_override: str | None,
        stage: str,
    ) -> None:
        if not self.llm.is_configured():
            return
        short_state = {
            "route": route,
            "stage": stage,
            "steps_taken": ctx.steps_taken,
            "done": ctx.done,
            "blocked": ctx.blocked,
            "keys": sorted(list(ctx.data.keys()))[:24],
        }
        try:
            text, meta = self.llm.reason(
                f"Task prompt: {ctx.prompt}\nCurrent state: {json.dumps(short_state)}\n"
                "Provide one short next-step reflection.",
                memory_bundle,
                model_override=model_override,
            )
            ctx.data["llm_trace"].append({"stage": stage, "reflection": text[:500]})
            self._record_llm_meta(ctx, meta, stage=stage)
        except Exception as exc:  # noqa: BLE001
            ctx.notes.append(f"LLM reflection unavailable at {stage}: {exc}")

    def _record_llm_meta(self, ctx: TaskContext, meta: dict, *, stage: str) -> None:
        usage = ctx.data.get("llm_usage", {})
        usage["model"] = meta.get("effective_model", meta.get("model", usage.get("model")))
        usage["calls"] = int(usage.get("calls", 0)) + 1
        usage["prompt_tokens"] = int(usage.get("prompt_tokens", 0)) + int(meta.get("prompt_tokens", 0))
        usage["completion_tokens"] = int(usage.get("completion_tokens", 0)) + int(meta.get("completion_tokens", 0))
        usage["total_tokens"] = int(usage.get("total_tokens", 0)) + int(meta.get("total_tokens", 0))
        usage["estimated_cost_usd"] = round(float(usage.get("estimated_cost_usd", 0.0)) + float(meta.get("estimated_cost_usd", 0.0)), 8)
        ctx.data["llm_usage"] = usage
        ctx.data["llm_trace"].append(
            {
                "stage": f"{stage}_meta",
                "model": meta.get("effective_model", meta.get("model")),
                "prompt_tokens": meta.get("prompt_tokens", 0),
                "completion_tokens": meta.get("completion_tokens", 0),
                "total_tokens": meta.get("total_tokens", 0),
                "estimated_cost_usd": meta.get("estimated_cost_usd", 0.0),
            }
        )

    def _redact_obj(self, obj):
        if isinstance(obj, str):
            return self.redactor.redact_text(obj)
        if isinstance(obj, list):
            return [self._redact_obj(i) for i in obj]
        if isinstance(obj, dict):
            return {k: self._redact_obj(v) for k, v in obj.items()}
        return obj
