# Requirement Document (Planning v1.1 - Brain-Driven Autonomous CLI)

## 1) Product Vision
Build an autonomous Ubuntu-server agent focused on **problem solving** (reasoning-first), not template responses.

For each prompt, the agent should iteratively reason, act, verify, and adapt until it reaches a valid conclusion or a clear blocked state.

## 2) Locked MVP Decisions
- Platform: Ubuntu Server (22.04/24.04)
- Runtime privilege: `root`
- Interface: CLI only
- Language: Python
- Missing dependencies: auto-install
- Capability persistence: JSON + Markdown
- New tool behavior: auto-save + auto-reuse
- Crypto providers: multi-provider
- Transcription output: `.txt`
- LLM routing: OpenRouter, default reasoning model `openai5.2` (configurable)

## 3) Core Execution Model
The agent runs an iterative loop per task:
1. Understand prompt intent.
2. Read `brain.md` and referenced memory files.
3. Produce next best action.
4. Execute action (tool/command/API/file op).
5. Evaluate result against goal.
6. Update memory/capability state.
7. Continue loop until completion or hard block.

This loop must keep consuming the LLM as needed, not stop at first draft output.

## 4) Brain Architecture

### 4.1 Master Brain File
`state/brain.md` is always injected into agent context for every task.

`brain.md` contains a reference index to other memory files:
- `Soul.md` (values, guardrails, decision style, response principles)
- `Persona.md` (user profile and evolving preferences)
- `Directives.md` (core problem-solving operating instructions; immutable in normal runs)
- `Skills.md` (capability catalog and routing hints)
- optional memory docs created over time (`Playbooks.md`, `Failures.md`, etc.)

### 4.2 Memory File Roles
- `Soul.md`: mandatory, stable, highest-priority governance.
- `Persona.md`: append-only snapshots when user behavior/preferences change.
- `Directives.md`: fixed operating doctrine for planning/execution loops.
- `Skills.md`: skill inventory and integration notes.

### 4.3 Long-Term Memory Rules
- Agent must read memory references before plan execution.
- Agent may update mutable files (`Persona.md`, `Skills.md`, episodic logs).
- Agent must not directly edit immutable doctrine (`Directives.md`) unless an explicit admin command is given.

## 5) Functional Requirements

### 5.1 Reasoning and Planning
- Generate a dynamic step graph with fallback branches.
- Store decision trace: chosen path, rejected options, rationale.
- Continue planning mid-run when new evidence appears.

### 5.2 Autonomous Environment Repair
- Detect missing commands/libraries/SDKs.
- Auto-install with apt and verify install success.
- Track install action with reason and task ID.

### 5.3 Tool/Skill Discovery and Generation
- Discover existing tools/skills before generating new ones.
- If needed, generate a new tool, validate it, register it, and reuse later.
- Skills/tools must be linked into `Skills.md` and `state/capabilities.json`.

### 5.4 LLM Provider Orchestration
- Primary LLM endpoint: OpenRouter.
- Default model profile: OpenAI reasoning model (`openai5.2` alias/config key).
- Model selection strategy:
  - use default reasoning model unless task/user explicitly overrides,
  - permit per-task model switch,
  - log selected model + token/cost metadata.

### 5.5 Secrets and Credentials
- API keys must be loaded from environment or secure secret files, not embedded in memory docs.
- Memory docs may reference key names only (example: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`).
- Strict redaction for logs and responses.

### 5.6 Folder Structure Awareness
Maintain canonical structure:
- `cli/`
- `agent/`
- `providers/`
- `tools/`
- `skills/`
- `state/`
- `logs/`
- `artifacts/`

Memory files under `state/memory/`:
- `brain.md`
- `Soul.md`
- `Persona.md`
- `Directives.md`
- `Skills.md`

### 5.7 Scenario Adapter: Historical BTC Price
Prompt example: "Get me BTC price as of March 3, 2026."
- Normalize date to `2026-03-03`.
- Ensure HTTP capability (`curl` or Python HTTP library).
- Query provider chain (CoinGecko + fallbacks).
- Reconcile response quality and return value + source attribution.

### 5.8 Scenario Adapter: Audio Transcription
Prompt example: "Transcribe this audio file."
- Inspect file and decode path.
- Ensure decode dependencies (e.g., `ffmpeg`).
- Verify OpenAI credentials.
- Execute transcription and return/save `.txt` artifact.
- Register and reuse successful workflow.

### 5.9 Self-Extension Behavior
If asked for new interface (REST API, Telegram bot), the agent should treat it as a task:
- plan scaffold,
- generate integration,
- install dependencies,
- test basic health,
- register this as a reusable capability.

## 6) Robustness Additions (Suggested and Included)
- `Failures.md`: known failure signatures and proven fixes.
- `ProviderReliability.md`: rolling health score for each external provider.
- `ToolBenchmarks.md`: latency/success stats per generated tool.
- `TaskEpisodes/`: per-task compact postmortems for learning.

## 7) Security and Guardrails
- Root-enabled runtime, but with policy restrictions for destructive commands.
- Full audit trail of commands and outcomes.
- Secret redaction at source and sink.
- Optional denylist for high-risk operations.

## 8) Acceptance Criteria (Updated)
1. Agent demonstrates iterative reasoning loop and does not terminate prematurely with generic text-only responses.
2. `brain.md` is loaded each run and referenced memory files are honored.
3. Missing dependencies are auto-installed and verified.
4. At least one generated tool is persisted and reused on a later task.
5. BTC and transcription scenarios complete with auditable traces.
6. No API key appears in logs or user-facing output.

## 9) Phase Plan
### Phase 1: Core Runtime
- CLI runner + task loop + command executor
- OpenRouter client integration with model config
- dependency manager + install verification

### Phase 2: Brain and Memory
- `brain.md` loader + reference resolver
- mutable/immutable memory policy
- memory update pipeline

### Phase 3: Capability Engine
- skill/tool discovery
- tool generation + registration
- JSON + Markdown capability persistence

### Phase 4: Scenario Workflows
- crypto multi-provider adapter chain
- audio transcription workflow
- provider reliability tracking

### Phase 5: Hardening
- retries/backoff policies
- regression suite for reasoning, repair, and reuse
- security and redaction tests
