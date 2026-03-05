from __future__ import annotations

import json
import subprocess
from pathlib import Path


class AudioProcessor:
    """Inspects and normalizes audio input for Whisper transcription."""

    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".webm"}

    def inspect(self, input_path: Path) -> dict:
        if not input_path.exists():
            raise FileNotFoundError(f"Input audio file not found: {input_path}")

        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-print_format",
            "json",
            str(input_path),
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr.strip() or result.stdout.strip()}")

        data = json.loads(result.stdout or "{}")
        streams = data.get("streams", [])
        format_info = data.get("format", {})
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        if not audio_streams:
            raise RuntimeError("No audio stream found in input file")

        return {
            "path": str(input_path),
            "extension": input_path.suffix.lower(),
            "duration": format_info.get("duration"),
            "codec": audio_streams[0].get("codec_name"),
            "channels": audio_streams[0].get("channels"),
            "sample_rate": audio_streams[0].get("sample_rate"),
        }

    def prepare_for_whisper(self, input_path: Path, artifacts_dir: Path) -> Path:
        ext = input_path.suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return input_path

        artifacts_dir.mkdir(parents=True, exist_ok=True)
        out_path = artifacts_dir / f"normalized_{input_path.stem}.wav"
        convert_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(out_path),
        ]
        result = subprocess.run(convert_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.strip() or result.stdout.strip()}")
        return out_path
