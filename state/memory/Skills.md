# Skills.md

This document catalogs available skills/tools and capability hints.

## LLM
- Provider: OpenRouter
- Default model alias: `openrouter/auto`
- Override policy: user can request model/provider changes explicitly.
- Secret references: `OPENROUTER_API_KEY`

## Audio
- Intended capabilities: transcribe, convert, speechify
- Primary API: OpenAI (Whisper / speech)
- System dependency: `ffmpeg`
- Secret references: `OPENAI_API_KEY`

## Data / Crypto
- Provider priority:
1. CoinGecko
2. Coinpaprika
3. Binance
- Return format: value + currency + date + provider attribution

## Video
- Capability: download YouTube videos for user-provided URLs
- Primary tool: `yt-dlp`
- Fallback: generated local tool under `tools/download_youtube.py`
- System dependencies: `yt-dlp`

## Generated Tools
- route: `youtube_download` | tool: `/Users/othnielnaga/Desktop/open-code/tools/download_youtube_dynamic.py` | status: `existing_tool_reused`
- route: `self_extension` | tool: `/Users/othnielnaga/Desktop/open-code/tools/telegram_interface.py` | status: `template_tool_generated`
