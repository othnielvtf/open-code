from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


class LLMClient:
    """OpenRouter-backed LLM client with configurable default model."""

    def __init__(self, project_root: Path) -> None:
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.api_key = api_key
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("OPENROUTER_MODEL", "openai5.2")
        self.input_cost_per_million = float(os.getenv("OPENROUTER_INPUT_COST_PER_M", "0"))
        self.output_cost_per_million = float(os.getenv("OPENROUTER_OUTPUT_COST_PER_M", "0"))

        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def reason(self, prompt: str, memory_bundle: dict[str, str], model_override: str | None = None) -> tuple[str, dict]:
        memory_context = "\n\n".join(f"[{k}]\n{v[:1500]}" for k, v in memory_bundle.items())
        model = model_override or self.model
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an autonomous problem-solving coding agent. "
                    "Use provided memory context and return concise operational reasoning."
                ),
            },
            {
                "role": "user",
                "content": f"Prompt:\n{prompt}\n\nMemory:\n{memory_context}",
            },
        ]

        resp, effective_model = self._create_completion_with_fallback(model=model, messages=messages)
        text = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens))
        estimated_cost = (
            (prompt_tokens / 1_000_000) * self.input_cost_per_million
            + (completion_tokens / 1_000_000) * self.output_cost_per_million
        )
        meta = {
            "model": model,
            "effective_model": effective_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 8),
        }
        return text, meta

    def generate_python_tool(self, task_prompt: str, model_override: str | None = None) -> str:
        model = model_override or self.model
        messages = [
            {
                "role": "system",
                "content": (
                    "Generate a safe Python CLI tool script. "
                    "Return only Python code in one fenced block. "
                    "The script must support '--help' and avoid destructive behavior."
                ),
            },
            {
                "role": "user",
                "content": f"Generate a Python tool for this task:\n{task_prompt}",
            },
        ]
        resp, _ = self._create_completion_with_fallback(model=model, messages=messages)
        return (resp.choices[0].message.content or "").strip()

    def _create_completion_with_fallback(self, *, model: str, messages: list[dict]):
        try:
            return self.client.chat.completions.create(model=model, messages=messages), model
        except Exception as exc:  # noqa: BLE001
            text = str(exc).lower()
            if "not a valid model id" in text or "model" in text and "not available" in text:
                # OpenRouter supports auto model routing and is safer than hard-failing runs.
                fallback = "openrouter/auto"
                return self.client.chat.completions.create(model=fallback, messages=messages), fallback
            raise
