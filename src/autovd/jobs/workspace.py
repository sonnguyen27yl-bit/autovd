"""Isolated ephemeral workspace for one AutoVD media job."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import Self
from uuid import uuid4


class JobWorkspace:
    """Own one randomized temporary directory and delete it on context exit."""

    def __init__(self, *, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._temporary_directory = TemporaryDirectory(prefix="autovd-job-", dir=root)
        self.path = Path(self._temporary_directory.name)

    def allocate_media_path(self) -> Path:
        """Return a randomized internal path without using a user-provided filename."""
        return self.path / f"{uuid4().hex}.media"

    def cleanup(self) -> None:
        """Delete all temporary data owned by this workspace."""
        self._temporary_directory.cleanup()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.cleanup()
