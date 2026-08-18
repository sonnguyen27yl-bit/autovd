import asyncio
import subprocess
from pathlib import Path

import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent

from autovd.mcp_server import mcp


async def _call_tool(name: str, arguments: dict[str, object]) -> CallToolResult:
    async with Client(mcp, raise_exceptions=True) as client:
        return await client.call_tool(name, arguments)


async def _exercise_server_without_spike_fixture() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        listed = await client.list_tools()
        tools = {tool.name: tool for tool in listed.tools}
        assert set(tools) == {
            "health",
            "prepare_video_analysis",
            "get_analysis_chunk",
            "render_video",
            "get_temporal_analysis_demo",
        }

        prepare = tools["prepare_video_analysis"]
        assert prepare.meta == {"openai/fileParams": ["videos"]}
        videos_schema = prepare.input_schema["properties"]["videos"]
        file_schema = videos_schema["items"]
        if "$ref" in file_schema:
            ref_name = file_schema["$ref"].split("/")[-1]
            file_schema = prepare.input_schema["$defs"][ref_name]
        assert set(file_schema["properties"]) == {
            "download_url",
            "file_id",
            "mime_type",
            "file_name",
        }
        assert set(file_schema["required"]) == {"download_url", "file_id"}

        health_result = await client.call_tool("health", {})
        assert health_result.is_error is False
        assert health_result.structured_content == {
            "service": "autovd",
            "status": "ok",
            "version": "0.1.0-dev",
        }

        unconfigured_result = await client.call_tool("get_temporal_analysis_demo", {})
        assert unconfigured_result.is_error is True
        assert "AUTOVD_SPIKE_VIDEO" in unconfigured_result.content[0].text


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
            "testsrc2=s=64x64:r=10:d=1",
            "-an",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _result_text(result: CallToolResult) -> str:
    return " ".join(block.text for block in result.content if isinstance(block, TextContent))


def test_tools_are_listed_and_callable_without_external_spike_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOVD_SPIKE_VIDEO", raising=False)

    asyncio.run(_exercise_server_without_spike_fixture())


def test_missing_configured_spike_media_does_not_expose_server_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_path = "/private/autovd/customer-123/secret-video.mp4"
    monkeypatch.setenv("AUTOVD_SPIKE_VIDEO", sensitive_path)

    result = asyncio.run(_call_tool("get_temporal_analysis_demo", {}))

    assert result.is_error is True
    text = _result_text(result)
    assert "unavailable or invalid" in text.lower()
    assert sensitive_path not in text


def test_configured_spike_media_is_callable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "fixture.mp4"
    _make_video(video_path)
    monkeypatch.setenv("AUTOVD_SPIKE_VIDEO", str(video_path))

    result = asyncio.run(
        _call_tool(
            "get_temporal_analysis_demo",
            {"interval_ms": 500, "max_frames": 2},
        )
    )

    assert result.is_error is False
    assert result.structured_content == {
        "clip_id": "spike_fixture",
        "timestamps_ms": [0, 500],
        "sampling_interval_ms": 500,
        "start_ms": 0,
        "end_ms": None,
    }
