"""AutoVD MCP entrypoint."""

import os
from pathlib import Path
from tempfile import gettempdir

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from autovd import __version__
from autovd.contracts.edit_plan import EditPlanLimits
from autovd.contracts.openai_files import OpenAIFile
from autovd.diagnostic import diagnostic_status
from autovd.jobs.store import JobStore
from autovd.media.ingest import MediaLimits
from autovd.media.motion import MotionConfig
from autovd.media.renderer import RenderProfile
from autovd.tools.analysis_spike import get_temporal_analysis_demo
from autovd.tools.workflow import ClipEditRequest, WorkflowConfig, WorkflowService

_LOCAL_ALLOWED_HOSTS = ("127.0.0.1:*", "localhost:*", "[::1]:*")
_LOCAL_ALLOWED_ORIGINS = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
)

mcp = MCPServer(
    "AutoVD",
    version=__version__,
    instructions=(
        "AutoVD cleans AI-generated video conservatively. Prepare uploaded clips first, inspect "
        "timestamped analysis chunks, then render only clear CUT decisions. When uncertain, KEEP."
    ),
)


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _float_env(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def _csv_env(name: str) -> list[str]:
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


def _server_transport_options() -> tuple[str, int, TransportSecuritySettings]:
    host = os.environ.get("AUTOVD_HOST", "127.0.0.1").strip()
    if not host:
        raise ValueError("AUTOVD_HOST must not be empty")

    port = _int_env("AUTOVD_PORT", 8000)
    if not 1 <= port <= 65_535:
        raise ValueError("AUTOVD_PORT must be between 1 and 65535")

    allowed_hosts = list(dict.fromkeys([*_LOCAL_ALLOWED_HOSTS, *_csv_env("AUTOVD_ALLOWED_HOSTS")]))
    allowed_origins = list(
        dict.fromkeys([*_LOCAL_ALLOWED_ORIGINS, *_csv_env("AUTOVD_ALLOWED_ORIGINS")])
    )
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )
    return host, port, security


def _build_workflow_service() -> WorkflowService:
    job_root = Path(os.environ.get("AUTOVD_JOB_ROOT", str(Path(gettempdir()) / "autovd-jobs")))
    music_dir = Path(os.environ.get("AUTOVD_MUSIC_DIR", "music/library"))
    return WorkflowService(
        store=JobStore(
            root=job_root,
            max_jobs=_int_env("AUTOVD_MAX_ACTIVE_JOBS", 8),
            ttl_seconds=_float_env("AUTOVD_JOB_TTL_SECONDS", 30 * 60),
            max_output_bytes=_int_env("AUTOVD_MAX_OUTPUT_BYTES", 512 * 1024 * 1024),
        ),
        config=WorkflowConfig(
            media_limits=MediaLimits(
                max_clips=_int_env("AUTOVD_MAX_CLIPS", 8),
                max_file_bytes=_int_env("AUTOVD_MAX_FILE_BYTES", 256 * 1024 * 1024),
                max_duration_ms=_int_env("AUTOVD_MAX_CLIP_DURATION_MS", 120_000),
            ),
            motion=MotionConfig(
                frame_interval_ms=_int_env("AUTOVD_MOTION_INTERVAL_MS", 500),
                threshold=_float_env("AUTOVD_MOTION_THRESHOLD", 0.01),
                min_low_motion_ms=_int_env("AUTOVD_MIN_LOW_MOTION_MS", 2_000),
                speed_factor=_float_env("AUTOVD_SPEED_FACTOR", 2.0),
                max_frames=_int_env("AUTOVD_MOTION_MAX_FRAMES", 256),
            ),
            edit_limits=EditPlanLimits(max_cut_intervals=_int_env("AUTOVD_MAX_CUT_INTERVALS", 64)),
            render_profile=RenderProfile(
                width=_int_env("AUTOVD_OUTPUT_WIDTH", 1280),
                height=_int_env("AUTOVD_OUTPUT_HEIGHT", 720),
                fps=_int_env("AUTOVD_OUTPUT_FPS", 30),
                timeout_seconds=_int_env("AUTOVD_RENDER_TIMEOUT_SECONDS", 180),
            ),
            download_timeout_seconds=_float_env("AUTOVD_DOWNLOAD_TIMEOUT_SECONDS", 30.0),
        ),
        music_dir=music_dir,
    )


workflow_service = _build_workflow_service()


@mcp.custom_route("/health", methods=["GET"])
async def http_health(_request: Request) -> JSONResponse:
    """Return a public, non-sensitive liveness response for deployment probes."""
    return JSONResponse({"status": "ok"})


@mcp.tool(
    title="Check AutoVD health",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
def health() -> dict[str, str]:
    """Return a stable, non-sensitive diagnostic payload."""
    return diagnostic_status()


@mcp.tool(
    title="Prepare uploaded videos",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False, destructive_hint=False),
    meta={"openai/fileParams": ["videos"]},
)
def prepare_video_analysis(videos: list[OpenAIFile]) -> dict[str, object]:
    """Prepare 1..N ChatGPT-uploaded videos for AutoVD analysis in upload order."""
    return workflow_service.prepare_video_analysis(videos)


@mcp.tool(
    title="Get video analysis chunk",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False, destructive_hint=False),
)
def get_analysis_chunk(
    job_id: str,
    clip_id: str,
    start_ms: int = 0,
    end_ms: int | None = None,
    interval_ms: int = 500,
    max_frames: int = 8,
) -> CallToolResult:
    """Return bounded ordered timestamp/image evidence for one prepared clip interval."""
    return workflow_service.get_analysis_chunk(
        job_id=job_id,
        clip_id=clip_id,
        start_ms=start_ms,
        end_ms=end_ms,
        interval_ms=interval_ms,
        max_frames=max_frames,
    )


@mcp.tool(
    name="render_video",
    title="Render cleaned video",
    annotations=ToolAnnotations(
        read_only_hint=False,
        open_world_hint=False,
        destructive_hint=False,
    ),
)
def render_video_tool(job_id: str, edits: list[ClipEditRequest]) -> CallToolResult:
    """Render prepared clips using validated clear CUT decisions plus deterministic pacing."""
    return workflow_service.render_video(job_id=job_id, edits=edits)


@mcp.resource("autovd://jobs/{job_id}/output", mime_type="video/mp4")
def rendered_output(job_id: str) -> bytes:
    """Return the completed MP4 for one active AutoVD job."""
    return workflow_service.read_rendered_output(job_id)


mcp.tool()(get_temporal_analysis_demo)


def main() -> None:
    """Run the remote MCP endpoint using Streamable HTTP."""
    host, port, transport_security = _server_transport_options()
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
        transport_security=transport_security,
    )


if __name__ == "__main__":
    main()
