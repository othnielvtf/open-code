from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.executor import AgentExecutor
from agent.memory_manager import MemoryManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_memory = MemoryManager(PROJECT_ROOT)
_executor = AgentExecutor(PROJECT_ROOT, _memory)

app = FastAPI(title="Brain Agent API", version="1.0.0")


class TaskRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    input_file: str | None = None
    max_steps: int = Field(default=8, ge=1, le=40)
    model: str | None = None


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "brain-agent-api"}


@app.post("/task")
def run_task(req: TaskRequest) -> dict:
    try:
        return _executor.run(
            prompt=req.prompt,
            input_file=req.input_file,
            max_steps=req.max_steps,
            model_override=req.model,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"task execution failed: {exc}") from exc
