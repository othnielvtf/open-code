# Phase Status

## Completed
- Phase 1: Core Runtime
  - CLI runner
  - task loop with step execution
  - command runner + safety policy
  - cross-platform dependency auto-install (apt + brew)

- Phase 2: Brain and Memory
  - `brain.md` loaded every run
  - reference resolver for memory docs
  - mutable/immutable memory policy (`Directives.md` and `Soul.md` immutable)
  - memory update pipeline (`TaskEpisodes`, provider health, tool benchmarks, failure log)

- Phase 3: Capability Engine
  - skill discovery from memory/local skill docs
  - capability registry (JSON + Markdown)
  - reliability scoring (`success_rate`, `reliability_score`)
  - best capability selection per route
  - LLM-driven + validated tool generation with fallback templates
  - generated/reused tools auto-linked into `state/memory/Skills.md`

## Newly Completed
- Phase 4: Workflow Depth and Adapters
  - crypto multi-provider adapter chain now includes CoinGecko, Coinpaprika, and Binance
  - weighted provider consensus using rolling provider reliability score
  - audio inspect/decode pipeline (`ffprobe` + optional `ffmpeg` normalization) before Whisper
  - provider reliability tracking now keeps success/failure counters and score
- Phase 5: Hardening
  - bounded retry/backoff policy for transient provider/transcription failures
  - secret redaction for logs and user-facing notes
  - expanded regression suite for retry and redaction behavior
