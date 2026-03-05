# Brain-Driven Autonomous CLI Agent

Ubuntu-first autonomous agent scaffold focused on reasoning, self-healing dependencies, and long-term Markdown+JSON memory.
The current scaffold also supports macOS package auto-install through Homebrew.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python cli/main.py --prompt "Get me the BTC price as of March 3, 2026"
python cli/main.py --prompt "Get me the BTC price as of March 3, 2026" --model openrouter/auto
python cli/main.py --prompt "Transcribe this audio file" --file /absolute/path/audio.mp3
python cli/main.py --prompt "Download this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

On macOS, ensure Homebrew is installed before using auto-install paths.

## Layout

- `cli/` CLI entrypoint
- `api/` HTTP server wrapper (FastAPI)
- `agent/` planner/executor/memory/dependency logic
- `providers/` provider adapters (crypto, etc.)
- `tools/` generated reusable tools
- `skills/` skill definitions/instructions
- `state/` persistent registries and brain memory
- `logs/` execution traces
- `artifacts/` output files (e.g., transcript `.txt`)

## Security note

Store keys in environment variables only (e.g., `OPENROUTER_API_KEY`, `OPENAI_API_KEY`). Do not put real secrets in Markdown memory files.

## Platform notes

- Ubuntu/Linux: auto-installs use `apt-get`.
- macOS: auto-installs use Homebrew (`brew` must be installed).

## Safety

- Shell actions run through a safety policy that blocks known destructive command patterns.

## Autonomous tool generation

- If a direct workflow fails, the agent can generate a Python tool, validate it (`py_compile` + `--help`), then retry.
- Capability reliability is tracked in `state/capabilities.json` (`success_rate`, `reliability_score`).

## Phase status

- Phase 1 (Core Runtime): complete
- Phase 2 (Brain + Memory): complete
- Phase 3 (Capability Engine): complete
- Phase 4 (Workflow Adapters): complete
- Phase 5 (Hardening): complete

## Validation

```bash
python3 -m unittest tests/test_phase_1_3.py tests/test_phase_2.py tests/test_phase_3.py tests/test_phase_4.py tests/test_phase_5.py
```

Run logs now include `task_id`, structured `install_events`, and `llm_usage` token/cost metadata.

## Run as API (chat/request mode)

Start API server locally:

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8080
```

Health check:

```bash
curl http://localhost:8080/health
```

Run a task:

```bash
curl -X POST http://localhost:8080/task \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Get me BTC price as of 3rd march 2026","max_steps":8}'
```

## Run continuously on Ubuntu (systemd)

1. Copy project to `/opt/brain-agent` and create venv there.
2. Install dependencies:

```bash
cd /opt/brain-agent
/opt/brain-agent/.venv/bin/pip install -r requirements.txt
```

3. Copy service file:

```bash
sudo cp deploy/brain-agent-api.service /etc/systemd/system/brain-agent-api.service
```

4. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable brain-agent-api
sudo systemctl start brain-agent-api
sudo systemctl status brain-agent-api
```
