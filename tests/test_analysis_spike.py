import subprocess
from pathlib import Path

from mcp.types import ImageContent, TextContent

from autovd.tools.analysis_spike import build_temporal_evidence


def _make_video(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=s=64x64:r=10:d=1.5",
            "-an",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def test_build_temporal_evidence_interleaves_timestamps_and_images(tmp_path: Path) -> None:
    video_path = tmp_path / "fixture.mp4"
    _make_video(video_path)

    result = build_temporal_evidence(video_path, interval_ms=500, max_frames=8)

    assert result.is_error is False
    assert result.structured_content == {
        "clip_id": "spike_fixture",
        "timestamps_ms": [0, 500, 1000],
        "sampling_interval_ms": 500,
    }
    assert isinstance(result.content[0], TextContent)

    evidence = result.content[1:]
    assert len(evidence) == 6
    for index, timestamp_ms in enumerate([0, 500, 1000]):
        timestamp_block = evidence[index * 2]
        image_block = evidence[index * 2 + 1]
        assert isinstance(timestamp_block, TextContent)
        assert timestamp_block.text == f"timestamp_ms={timestamp_ms}"
        assert isinstance(image_block, ImageContent)
        assert image_block.mime_type == "image/png"
        assert image_block.data
