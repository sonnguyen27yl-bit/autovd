"""Small ffprobe boundary for validating staged video media."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class MediaProbeError(ValueError):
    """Raised when staged media cannot be validated as a usable video."""


@dataclass(frozen=True, slots=True)
class ProbedVideo:
    """Validated video metadata required by the MVP core."""

    duration_ms: int
    width: int
    height: int
    codec_name: str


def probe_video(path: Path) -> ProbedVideo:
    """Return bounded metadata for one trusted staged path without exposing it in errors."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name:format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        payload = cast(dict[str, Any], json.loads(completed.stdout))
        streams = cast(list[dict[str, Any]], payload["streams"])
        stream = streams[0]
        format_data = cast(dict[str, Any], payload["format"])

        duration_ms = round(float(format_data["duration"]) * 1000)
        width = int(stream["width"])
        height = int(stream["height"])
        codec_name = str(stream["codec_name"])
        if duration_ms <= 0 or width <= 0 or height <= 0 or not codec_name:
            raise ValueError("invalid probed media metadata")
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        raise MediaProbeError("input must be valid video media") from exc

    return ProbedVideo(
        duration_ms=duration_ms,
        width=width,
        height=height,
        codec_name=codec_name,
    )
