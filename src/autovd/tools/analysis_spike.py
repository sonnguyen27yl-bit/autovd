"""Temporal evidence helpers for ChatGPT visual-analysis workflows."""

import os
import subprocess
from pathlib import Path

from mcp.server.mcpserver import Image
from mcp.types import CallToolResult, ContentBlock, TextContent

from autovd.media.frame_sampler import FramePayloadLimitError, sample_video_frames

SPIKE_VIDEO_ENV = "AUTOVD_SPIKE_VIDEO"
SAFE_MEDIA_ERROR = "Configured spike media is unavailable or invalid."


def _safe_media_error_result() -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=SAFE_MEDIA_ERROR)],
        is_error=True,
    )


def build_temporal_evidence(
    video_path: Path,
    *,
    clip_id: str = "spike_fixture",
    interval_ms: int = 500,
    max_frames: int = 8,
    start_ms: int = 0,
    end_ms: int | None = None,
) -> CallToolResult:
    """Build ordered timestamp/image blocks for one trusted video interval."""
    frames = sample_video_frames(
        video_path,
        interval_ms=interval_ms,
        max_frames=max_frames,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    if not frames:
        return CallToolResult(
            content=[TextContent(type="text", text="No video frames could be extracted.")],
            is_error=True,
        )

    content: list[ContentBlock] = [
        TextContent(
            type="text",
            text=(
                "Inspect the ordered frames below for clear AI-generation visual failures. "
                "CUT only clear failures; when uncertain, KEEP."
            ),
        )
    ]

    for frame in frames:
        content.append(TextContent(type="text", text=f"timestamp_ms={frame.timestamp_ms}"))
        content.append(Image(data=frame.png_bytes, format="png").to_image_content())

    return CallToolResult(
        content=content,
        structured_content={
            "clip_id": clip_id,
            "timestamps_ms": [frame.timestamp_ms for frame in frames],
            "sampling_interval_ms": interval_ms,
            "start_ms": start_ms,
            "end_ms": end_ms,
        },
        is_error=False,
    )


def get_temporal_analysis_demo(
    interval_ms: int = 500,
    max_frames: int = 8,
) -> CallToolResult:
    """Return timestamped visual evidence from the operator-configured spike clip."""
    configured_path = os.environ.get(SPIKE_VIDEO_ENV)
    if not configured_path:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Spike fixture is not configured. Set {SPIKE_VIDEO_ENV} on the server.",
                )
            ],
            is_error=True,
        )

    try:
        return build_temporal_evidence(
            Path(configured_path),
            interval_ms=interval_ms,
            max_frames=max_frames,
        )
    except (
        FileNotFoundError,
        FramePayloadLimitError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return _safe_media_error_result()
