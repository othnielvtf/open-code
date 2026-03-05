#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download YouTube video via yt-dlp")
    parser.add_argument("url")
    parser.add_argument("--out-dir", default="artifacts")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo+bestaudio/best",
        "-o",
        str(out_dir / "%(title)s.%(ext)s"),
        args.url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr or "yt-dlp failed")

    print("download_complete")


if __name__ == "__main__":
    main()
