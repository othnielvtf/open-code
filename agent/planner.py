from __future__ import annotations

from agent.types import TaskContext


class Planner:
    """Produces next action based on route and current context."""

    def next_action(self, route: str, ctx: TaskContext) -> str:
        if route == "identity":
            return "handle_identity"

        if route == "self_extension":
            if "extension_scaffolded" not in ctx.data:
                return "scaffold_extension_interface"
            if "extension_health_checked" not in ctx.data:
                return "test_extension_health"
            return "finalize"

        if route == "youtube_download":
            if "video_stack_ready" not in ctx.data:
                return "ensure_video_stack"
            if "download_result" not in ctx.data and "generated_tool_attempted" not in ctx.data:
                return "run_youtube_download"
            if "download_result" not in ctx.data and "generated_tool_attempted" in ctx.data:
                return "run_generated_youtube_tool"
            return "finalize"

        if route == "crypto_price":
            if "http_ready" not in ctx.data:
                return "ensure_http"
            if "provider_result" not in ctx.data:
                return "query_crypto_providers"
            return "finalize"

        if route == "network_ops":
            if "network_command_result" not in ctx.data:
                return "execute_network_command"
            return "finalize"

        if route == "audio_transcription":
            if "audio_ready" not in ctx.data:
                return "ensure_audio_stack"
            if "transcript" not in ctx.data:
                return "run_transcription"
            return "finalize"

        if "analysis" not in ctx.data:
            return "analyze_prompt"
        return "finalize"
