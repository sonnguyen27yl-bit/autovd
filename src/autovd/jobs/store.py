"""Bounded in-process job registry for multi-call MCP workflows."""

from dataclasses import dataclass
from pathlib import Path
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
    output_path: Path | None = None


class JobStore:
    """Keep a bounded number of ephemeral jobs alive inside one server process."""

    def __init__(self, *, root: Path, max_jobs: int) -> None:
        if max_jobs <= 0:
            raise ValueError("max_jobs must be positive")
        self.root = root
        self.max_jobs = max_jobs
        self._jobs: dict[str, PreparedJob] = {}

    def create_from_staged(
        self,
        staged_paths: list[Path],
        *,
        limits: MediaLimits,
    ) -> PreparedJob:
        if len(self._jobs) >= self.max_jobs:
            raise JobStoreError("too many active jobs")

        workspace = JobWorkspace(root=self.root)
        try:
            clips = ingest_staged_media(staged_paths, workspace=workspace, limits=limits)
        except Exception:
            workspace.cleanup()
            raise

        job_id = uuid4().hex
        job = PreparedJob(job_id=job_id, workspace=workspace, clips=clips)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> PreparedJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobStoreError("unknown or expired job")
        return job

    def set_output(self, job_id: str, output_path: Path) -> None:
        job = self.get(job_id)
        if output_path.parent != job.workspace.path or not output_path.is_file():
            raise JobStoreError("job output is unavailable")
        job.output_path = output_path

    def read_output(self, job_id: str) -> bytes:
        job = self.get(job_id)
        if job.output_path is None or not job.output_path.is_file():
            raise JobStoreError("job output is unavailable")
        return job.output_path.read_bytes()

    def delete(self, job_id: str) -> None:
        job = self._jobs.pop(job_id, None)
        if job is not None:
            job.workspace.cleanup()

    def close(self) -> None:
        for job_id in list(self._jobs):
            self.delete(job_id)
