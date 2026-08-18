"""Validated ingestion from adapter-staged local files into one job workspace."""

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from autovd.jobs.workspace import JobWorkspace
from autovd.media.probe import MediaProbeError, probe_video


class MediaIngestError(ValueError):
    """Raised when staged media violates the MVP ingestion contract."""


@dataclass(frozen=True, slots=True)
class MediaLimits:
    """Caller-configured resource limits for one ingestion request."""

    max_clips: int
    max_file_bytes: int
    max_duration_ms: int

    def __post_init__(self) -> None:
        if self.max_clips <= 0:
            raise ValueError("max_clips must be positive")
        if self.max_file_bytes <= 0:
            raise ValueError("max_file_bytes must be positive")
        if self.max_duration_ms <= 0:
            raise ValueError("max_duration_ms must be positive")


@dataclass(frozen=True, slots=True)
class IngestedClip:
    """Trusted internal metadata for one validated clip."""

    clip_id: str
    order: int
    path: Path
    duration_ms: int
    width: int
    height: int
    codec_name: str


def ingest_staged_media(
    paths: Sequence[Path],
    *,
    workspace: JobWorkspace,
    limits: MediaLimits,
) -> list[IngestedClip]:
    """Validate adapter-staged media and copy it into isolated internal paths."""
    if not paths or len(paths) > limits.max_clips:
        raise MediaIngestError("clip count exceeds configured limit")

    clips: list[IngestedClip] = []
    for order, source_path in enumerate(paths):
        if source_path.is_symlink() or not source_path.is_file():
            raise MediaIngestError("input must be valid video media")

        try:
            file_size = source_path.stat().st_size
        except OSError as exc:
            raise MediaIngestError("input must be valid video media") from exc
        if file_size > limits.max_file_bytes:
            raise MediaIngestError("file size exceeds configured limit")

        try:
            metadata = probe_video(source_path)
        except MediaProbeError as exc:
            raise MediaIngestError("input must be valid video media") from exc
        if metadata.duration_ms > limits.max_duration_ms:
            raise MediaIngestError("duration exceeds configured limit")

        internal_path = workspace.allocate_media_path()
        try:
            shutil.copyfile(source_path, internal_path)
        except OSError as exc:
            raise MediaIngestError("input media could not be staged") from exc

        clips.append(
            IngestedClip(
                clip_id=f"clip_{order:04d}",
                order=order,
                path=internal_path,
                duration_ms=metadata.duration_ms,
                width=metadata.width,
                height=metadata.height,
                codec_name=metadata.codec_name,
            )
        )

    return clips
