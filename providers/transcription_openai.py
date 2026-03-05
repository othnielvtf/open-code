from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


class OpenAIWhisperProvider:
    name = "openai_whisper"

    def __init__(self, project_root: Path) -> None:
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def transcribe(self, input_path: Path) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        if not input_path.exists():
            raise FileNotFoundError(f"Input audio file not found: {input_path}")

        client = OpenAI(api_key=self.api_key)
        with input_path.open("rb") as audio:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio)

        text = getattr(transcript, "text", "")
        if not text:
            raise RuntimeError("Whisper transcription returned empty text")
        return text
