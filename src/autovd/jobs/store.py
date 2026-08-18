"""Bounded in-process job registry for multi-call MCP workflows."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from uuid import uuid4

from autovd.jobs.workspace import JobWorkspace
from autovd.media.ingest import IngestedClip, MediaLimits, ingest_staged_media


class JobStoreError(ValueError):
    """Raised when a workflow job cannot be created or resolved."""


@dataclass(slots=True)
class PreparedJob:
    """One active job whose workspace must survive across MCP calls."""

    job_id: str
    workspace: JobWorkspace
    clips: list[IngestedClip]
    expires_at: float
    output_path: Path | None = None


class JobStore:
    """Keep a bounded number of ephemeral jobs alive inside one server process."""

    def __init__(
        self,
        *,
        root: Path,
        max_jobs: int,
        ttl_seconds: float = 30 * 60,
        max_output_bytes: int = 512 * 1024 * 1024,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_jobs <= 0:
            raise ValueError("max_jobs must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")
        self.root = root
        self.max_jobs = max_jobs
        self.ttl_seconds = ttl_seconds
        self.max_output_bytes = max_output_bytes
        self.clock = clock
        self._jobs: dict[str, PreparedJob] = {}

    def create_from_staged(
        self,
        staged_paths: list[Path],
        *,
        limits: MediaLimits,
    ) -> PreparedJob:
        self._purge_expired()
        if len(self._jobs) >= self.max_jobs:
            raise JobStoreError("too many active jobs")

        workspace = JobWorkspace(root=self.root)
        try:
            clips = ingest_staged_media(staged_paths, workspace=workspace, limits=limits)
        except Exception:
            workspace.cleanup()
            raise

        job_id = uuid4().hex
        job = PreparedJob(
            job_id=job_id,
            workspace=workspace,
            clips=clips,
            expires_at=self.clock() + self.ttl_seconds,
        )
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> PreparedJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobStoreError("unknown or expired job")
        now = self.clock()
        if now >= job.expires_at:
            self.delete(job_id)
            raise JobStoreError("unknown or expired job")
        job.expires_at = now + self.ttl_seconds
        return job

    def set_output(self, job_id: str, output_path: Path) -> None:
        job = self.get(job_id)
        if output_path.parent != job.workspace.path or not output_path.is_file():
            raise JobStoreError("job output is unavailable")
        if output_path.stat().st_size > self.max_output_bytes:
            raise JobStoreError("job output size exceeds configured limit")
        job.output_path = output_path

    def read_output(self, job_id: str) -> bytes:
        job = self.get(job_id)
        if job.output_path is None or not job.output_path.is_file():
            raise JobStoreError("job output is unavailable")
        if job.output_path.stat().st_size > self.max_output_bytes:
            raise JobStoreError("job output size exceeds configured limit")
        return job.output_path.read_bytes()

    def delete(self, job_id: str) -> None:
        job = self._jobs.pop(job_id, None)
        if job is not None:
            job.workspace.cleanup()

    def close(self) -> None:
        for job_id in list(self._jobs):
            self.delete(job_id)

    def _purge_expired(self) -> None:
        now = self.clock()
        for job_id, job in list(self._jobs.items()):
            if now >= job.expires_at:
                self.delete(job_id)
