import subprocess
from pathlib import Path

import pytest

from autovd.jobs.store import JobStore, JobStoreError
from autovd.media.ingest import MediaLimits


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


def _limits() -> MediaLimits:
    return MediaLimits(max_clips=2, max_file_bytes=5_000_000, max_duration_ms=2_000)


def test_expired_job_is_deleted_and_becomes_unavailable(tmp_path: Path) -> None:
    now = [100.0]
    source = tmp_path / "clip.mp4"
    _make_video(source)
    store = JobStore(
        root=tmp_path / "jobs",
        max_jobs=2,
        ttl_seconds=10.0,
        max_output_bytes=1024,
        clock=lambda: now[0],
    )
    job = store.create_from_staged([source], limits=_limits())
    workspace_path = job.workspace.path

    now[0] = 111.0

    with pytest.raises(JobStoreError, match="unknown or expired"):
        store.get(job.job_id)
    assert not workspace_path.exists()


def test_get_refreshes_active_job_ttl(tmp_path: Path) -> None:
    now = [100.0]
    source = tmp_path / "clip.mp4"
    _make_video(source)
    store = JobStore(
        root=tmp_path / "jobs",
        max_jobs=2,
        ttl_seconds=10.0,
        max_output_bytes=1024,
        clock=lambda: now[0],
    )
    job = store.create_from_staged([source], limits=_limits())

    now[0] = 109.0
    assert store.get(job.job_id).job_id == job.job_id
    now[0] = 118.0
    assert store.get(job.job_id).job_id == job.job_id


def test_output_size_is_bounded_before_resource_read(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    _make_video(source)
    store = JobStore(
        root=tmp_path / "jobs",
        max_jobs=2,
        ttl_seconds=60.0,
        max_output_bytes=4,
    )
    job = store.create_from_staged([source], limits=_limits())
    output = job.workspace.path / "output.mp4"
    output.write_bytes(b"12345")

    with pytest.raises(JobStoreError, match="output size"):
        store.set_output(job.job_id, output)


def test_output_growth_is_rechecked_before_resource_read(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    _make_video(source)
    store = JobStore(
        root=tmp_path / "jobs",
        max_jobs=2,
        ttl_seconds=60.0,
        max_output_bytes=4,
    )
    job = store.create_from_staged([source], limits=_limits())
    output = job.workspace.path / "output.mp4"
    output.write_bytes(b"1234")
    store.set_output(job.job_id, output)

    output.write_bytes(b"12345")

    with pytest.raises(JobStoreError, match="output size"):
        store.read_output(job.job_id)


def test_store_config_rejects_non_positive_bounds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="ttl_seconds"):
        JobStore(root=tmp_path, max_jobs=1, ttl_seconds=0, max_output_bytes=1)
    with pytest.raises(ValueError, match="max_output_bytes"):
        JobStore(root=tmp_path, max_jobs=1, ttl_seconds=1, max_output_bytes=0)
