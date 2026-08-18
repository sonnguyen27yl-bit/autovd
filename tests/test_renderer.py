import json
import random
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

from autovd.jobs.workspace import JobWorkspace
from autovd.media.ingest import MediaLimits, ingest_staged_media
from autovd.media.renderer import (
    ClipRenderPlan,
    MusicTrack,
    RendererError,
    RenderProfile,
    build_render_command,
    render_video,
)
from autovd.media.timeline import RenderSegment


def _make_av_clip(
    path: Path,
    *,
    color: str,
    tone_hz: int,
    duration_seconds: float,
) -> None:
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
            f"color=c={color}:s=96x64:r=10:d={duration_seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={tone_hz}:duration={duration_seconds}",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _make_music(path: Path, *, tone_hz: int = 880, duration_seconds: float = 0.5) -> None:
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
            f"sine=frequency={tone_hz}:duration={duration_seconds}",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )


def _probe(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return cast(dict[str, Any], json.loads(completed.stdout))


def _sample_rgb(path: Path, timestamp_seconds: float) -> tuple[int, int, int]:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(timestamp_seconds),
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=1:1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
        timeout=15,
    )
    assert len(completed.stdout) == 3
    return tuple(completed.stdout)  # type: ignore[return-value]


def _profile() -> RenderProfile:
    return RenderProfile(width=96, height=64, fps=10)


def test_build_render_command_preserves_clip_order_and_maps_only_music_audio(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    music = tmp_path / "music.m4a"
    _make_av_clip(first, color="red", tone_hz=440, duration_seconds=1.0)
    _make_av_clip(second, color="blue", tone_hz=550, duration_seconds=1.0)
    _make_music(music)

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        clips = ingest_staged_media(
            [first, second],
            workspace=workspace,
            limits=MediaLimits(max_clips=2, max_file_bytes=5_000_000, max_duration_ms=2_000),
        )
        plans = [
            ClipRenderPlan(clip=clips[1], segments=(RenderSegment(0, 1000, 1.0),)),
            ClipRenderPlan(clip=clips[0], segments=(RenderSegment(0, 1000, 1.0),)),
        ]
        output_path = workspace.path / "output.mp4"
        built = build_render_command(
            plans,
            music_tracks=[MusicTrack(track_id="music-1", path=music)],
            output_path=output_path,
            profile=_profile(),
            rng=random.Random(1),
        )

        first_input_index = built.command.index(str(clips[0].path))
        second_input_index = built.command.index(str(clips[1].path))
        assert first_input_index < second_input_index
        assert built.music_track.track_id == "music-1"
        assert "[0:a" not in built.filter_complex
        assert "[1:a" not in built.filter_complex
        assert built.command[built.command.index("-map") + 1] == "[vout]"
        assert f"{built.music_input_index}:a:0" in built.command


def test_render_video_applies_segments_preserves_order_and_adds_music(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    music = tmp_path / "music.m4a"
    _make_av_clip(first, color="red", tone_hz=440, duration_seconds=2.0)
    _make_av_clip(second, color="blue", tone_hz=550, duration_seconds=1.0)
    _make_music(music)

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        clips = ingest_staged_media(
            [first, second],
            workspace=workspace,
            limits=MediaLimits(max_clips=2, max_file_bytes=5_000_000, max_duration_ms=3_000),
        )
        plans = [
            ClipRenderPlan(
                clip=clips[0],
                segments=(
                    RenderSegment(start_ms=0, end_ms=500, speed_factor=1.0),
                    RenderSegment(start_ms=1000, end_ms=2000, speed_factor=2.0),
                ),
            ),
            ClipRenderPlan(
                clip=clips[1],
                segments=(RenderSegment(start_ms=0, end_ms=1000, speed_factor=1.0),),
            ),
        ]
        output_path = workspace.path / "final.mp4"

        result = render_video(
            plans,
            music_tracks=[MusicTrack(track_id="music-1", path=music)],
            output_path=output_path,
            profile=_profile(),
            rng=random.Random(1),
        )

        assert result.output_path == output_path
        assert result.music_track_id == "music-1"
        assert result.expected_duration_ms == 2000
        assert output_path.is_file()

        probe = _probe(output_path)
        streams = cast(list[dict[str, Any]], probe["streams"])
        assert [(stream["codec_type"], stream["codec_name"]) for stream in streams] == [
            ("video", "h264"),
            ("audio", "aac"),
        ]
        duration_ms = round(float(cast(dict[str, Any], probe["format"])["duration"]) * 1000)
        assert 1800 <= duration_ms <= 2200

        first_rgb = _sample_rgb(output_path, 0.25)
        second_rgb = _sample_rgb(output_path, 1.50)
        assert first_rgb[0] > first_rgb[2]
        assert second_rgb[2] > second_rgb[0]


def test_renderer_rejects_when_all_video_content_is_removed(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    music = tmp_path / "music.m4a"
    _make_av_clip(video, color="red", tone_hz=440, duration_seconds=1.0)
    _make_music(music)

    with JobWorkspace(root=tmp_path / "jobs") as workspace:
        clip = ingest_staged_media(
            [video],
            workspace=workspace,
            limits=MediaLimits(max_clips=1, max_file_bytes=5_000_000, max_duration_ms=2_000),
        )[0]

        with pytest.raises(RendererError, match="no retained video"):
            render_video(
                [ClipRenderPlan(clip=clip, segments=())],
                music_tracks=[MusicTrack(track_id="music-1", path=music)],
                output_path=workspace.path / "final.mp4",
                profile=_profile(),
                rng=random.Random(1),
            )
