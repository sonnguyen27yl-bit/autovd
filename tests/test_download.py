import socket
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType
from typing import Self

import pytest

from autovd.contracts.openai_files import OpenAIFile
from autovd.media import download
from autovd.media.download import FileDownloadError, download_openai_files


class _FakeResponse:
    def __init__(self, payload: bytes, headers: Mapping[str, str] | None = None) -> None:
        self.payload = payload
        self.headers = headers or {}
        self.offset = 0

    def read(self, amt: int = -1) -> bytes:
        if self.offset >= len(self.payload):
            return b""
        end = len(self.payload) if amt < 0 else min(len(self.payload), self.offset + amt)
        chunk = self.payload[self.offset : end]
        self.offset = end
        return chunk

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


def test_download_rejects_non_https_url(tmp_path: Path) -> None:
    file_value = OpenAIFile(download_url="http://example.com/video.mp4", file_id="file_1")

    with pytest.raises(FileDownloadError, match="HTTPS"):
        download_openai_files(
            [file_value],
            destination_dir=tmp_path,
            max_file_bytes=1024,
            timeout_seconds=1.0,
        )


def test_download_rejects_private_resolved_address(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        ],
    )
    file_value = OpenAIFile(download_url="https://files.example/video.mp4", file_id="file_1")

    with pytest.raises(FileDownloadError, match="not public"):
        download_openai_files(
            [file_value],
            destination_dir=tmp_path,
            max_file_bytes=1024,
            timeout_seconds=1.0,
        )


def test_download_rejects_stream_that_exceeds_size_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(download, "_validate_public_https_url", lambda url: None)
    monkeypatch.setattr(
        download,
        "_open_without_redirects",
        lambda url, timeout_seconds: _FakeResponse(b"12345"),
    )
    file_value = OpenAIFile(download_url="https://files.example/video.mp4", file_id="file_1")

    with pytest.raises(FileDownloadError, match="size limit"):
        download_openai_files(
            [file_value],
            destination_dir=tmp_path,
            max_file_bytes=4,
            timeout_seconds=1.0,
        )
    assert list(tmp_path.iterdir()) == []


def test_download_never_uses_user_filename_for_staged_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(download, "_validate_public_https_url", lambda url: None)
    monkeypatch.setattr(
        download,
        "_open_without_redirects",
        lambda url, timeout_seconds: _FakeResponse(b"ok"),
    )
    file_value = OpenAIFile(
        download_url="https://files.example/video.mp4",
        file_id="file_1",
        file_name="../../sensitive.mp4",
    )

    staged = download_openai_files(
        [file_value],
        destination_dir=tmp_path,
        max_file_bytes=1024,
        timeout_seconds=1.0,
    )

    assert staged[0].name == "upload_0000.media"
    assert staged[0].read_bytes() == b"ok"
