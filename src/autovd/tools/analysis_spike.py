"""Narrow temporal-vision spike for proving ChatGPT + MCP feasibility."""

import os
from pathlib import Path

from mcp.server.mcpserver import Image
from mcp.types import CallToolResult, ContentBlock, TextContent

from autovd.media.frame_sampler import sample_video_frames

SPIKE_VIDEO_ENV = "AUTOVD_SPIKE_VIDEO"


def build_temporal_evidence(
    video_path: Path,
    *,
    interval_ms: int = 500,
    max_frames: int = 8,
) -> CallToolResult:
    """Build ordered timestamp/image blocks for one trusted short fixture clip."""
    frames = sample_video_frames(video_path, interval_ms=interval_ms, max_frames=max_frames)
    if not frames:
        return CallToolResult(
            content=[TextContent(type="text", text="No video frames could be extracted.")],
            is_error=True,
        )

    content: list[ContentBlock] = [
        TextContent(
            type="text",
            text=(
                "AutoVD temporal-analysis spike. Inspect the ordered frames below. "
                "CUT only a clear AI-generation failure; when uncertain, KEEP."
            ),
        )
    ]

    for frame in frames:
        content.append(
            TextContent(
                type="text",
                text=f"timestamp_ms={frame.timestamp_ms}",
            )
        )
        content.append(Image(data=frame.png_bytes, format="png").to_image_content())

    return CallToolResult(
        content=content,
        structured_content={
            "clip_id": "spike_fixture",
            "timestamps_ms": [frame.timestamp_ms for frame in frames],
            "sampling_interval_ms": interval_ms,
        },
        is_error=False,
    )


def get_temporal_analysis_demo(
    interval_ms: int = 500,
    max_frames: int = 8,
) -> CallToolResult:
    """Return timestamped visual evidence from the operator-configured spike clip.

    The model cannot choose a filesystem path. The server operator configures the
    fixture via AUTOVD_SPIKE_VIDEO until the upload ingestion boundary is built.
    """
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

    return build_temporal_evidence(
        Path(configured_path),
        interval_ms=interval_ms,
        max_frames=max_frames,
    )
