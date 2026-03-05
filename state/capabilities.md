# Capabilities Memory

This file is a human-readable companion to `state/capabilities.json`.

## Registered Capabilities

### crypto_price_workflow
- route: `crypto_price`
- purpose: Reusable workflow for route 'crypto_price'
- last_status: `completed`
- times_used: 13
- success_count: 9
- failure_count: 1
- success_rate: 0.90
- reliability_score: 0.90
- dependencies: curl, requests

### general_reasoning_workflow
- route: `general_reasoning`
- purpose: Reusable workflow for route 'general_reasoning'
- last_status: `completed`
- times_used: 3
- success_count: 2
- failure_count: 0
- success_rate: 1.00
- reliability_score: 0.20
- dependencies: none

### audio_transcription_workflow
- route: `audio_transcription`
- purpose: Reusable workflow for route 'audio_transcription'
- last_status: `blocked`
- times_used: 2
- success_count: 0
- failure_count: 1
- success_rate: 0.00
- reliability_score: 0.00
- dependencies: ffmpeg, openai

### youtube_download_workflow
- route: `youtube_download`
- purpose: Reusable workflow for route 'youtube_download'
- last_status: `blocked`
- times_used: 6
- success_count: 0
- failure_count: 4
- success_rate: 0.00
- reliability_score: 0.00
- dependencies: yt-dlp
- last_tool: `/Users/othnielnaga/Desktop/open-code/tools/download_youtube_dynamic.py`
- last_tool_status: `existing_tool_reused`

### self_extension_workflow
- route: `self_extension`
- purpose: Reusable workflow for route 'self_extension'
- last_status: `completed`
- times_used: 2
- success_count: 2
- failure_count: 0
- success_rate: 1.00
- reliability_score: 0.20
- dependencies: python-telegram-bot
- last_tool: `/Users/othnielnaga/Desktop/open-code/tools/telegram_interface.py`
- last_tool_status: `template_tool_generated`

