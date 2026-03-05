#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.executor import AgentExecutor
from agent.memory_manager import MemoryManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Brain-driven autonomous CLI agent")
    parser.add_argument("--prompt", required=True, help="Task prompt")
    parser.add_argument("--file", help="Optional input file path (e.g., audio file)")
    parser.add_argument("--max-steps", type=int, default=8, help="Max execution iterations")
    parser.add_argument("--model", help="Optional per-task model override (e.g., openai5.2)")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    project_root = PROJECT_ROOT
    memory = MemoryManager(project_root=project_root)
    executor = AgentExecutor(project_root=project_root, memory_manager=memory)

    result = executor.run(
        prompt=args.prompt,
        input_file=args.file,
        max_steps=args.max_steps,
        model_override=args.model,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
