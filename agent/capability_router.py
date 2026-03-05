from __future__ import annotations

from pathlib import Path


class CapabilityRouter:
    """Very small intent router for scaffold phase."""
    MEDIA_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def route(self, prompt: str, input_file: str | None = None) -> str:
        p = prompt.lower()
        if any(k in p for k in ["what is your name", "who are you", "what are you", "call you", "your name is", "i name you"]):
            return "identity"
        if "telegram bot" in p or ("telegram" in p and "bot" in p):
            return "self_extension"
        if "rest api" in p or "http api" in p or ("api" in p and "scaffold" in p):
            return "self_extension"
        if "youtube.com/" in p or "youtu.be/" in p or ("youtube" in p and "download" in p):
            return "youtube_download"
        if any(k in p for k in ["btc", "bitcoin", "price", "coingecko"]):
            return "crypto_price"
        if input_file and any(input_file.lower().endswith(ext) for ext in self.MEDIA_EXTENSIONS):
            return "audio_transcription"
        if "transcribe" in p or "audio" in p:
            return "audio_transcription"
        return "general_reasoning"
