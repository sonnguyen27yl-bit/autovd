"""Bounded downloader for temporary ChatGPT file URLs."""

import ipaddress
import socket
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from autovd.contracts.openai_files import OpenAIFile

_REDIRECT_CODES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 3
_CHUNK_BYTES = 1024 * 1024


class FileDownloadError(ValueError):
    """Raised when a ChatGPT-provided temporary file cannot be fetched safely."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


def _validate_public_https_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise FileDownloadError("file download URL must use HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise FileDownloadError("file download URL must not contain credentials")
    if parsed.port not in (None, 443):
        raise FileDownloadError("file download URL must use the standard HTTPS port")

    try:
        resolved = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FileDownloadError("file download host could not be resolved") from exc
    if not resolved:
        raise FileDownloadError("file download host could not be resolved")

    for item in resolved:
        address = ipaddress.ip_address(item[4][0])
        if not address.is_global:
            raise FileDownloadError("file download host is not public")


def _open_without_redirects(url: str, timeout_seconds: float) -> object:
    opener = urllib.request.build_opener(_NoRedirectHandler())
    request = urllib.request.Request(url, headers={"User-Agent": "AutoVD/0.1"})
    return opener.open(request, timeout=timeout_seconds)


def download_openai_files(
    files: list[OpenAIFile],
    *,
    destination_dir: Path,
    max_file_bytes: int,
    timeout_seconds: float,
) -> list[Path]:
    """Download ChatGPT file values into randomized adapter-staged paths."""
    if max_file_bytes <= 0:
        raise ValueError("max_file_bytes must be positive")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    destination_dir.mkdir(parents=True, exist_ok=True)

    staged: list[Path] = []
    for index, file_value in enumerate(files):
        current_url = file_value.download_url
        response: object | None = None
        for redirect_count in range(_MAX_REDIRECTS + 1):
            _validate_public_https_url(current_url)
            try:
                response = _open_without_redirects(current_url, timeout_seconds)
                break
            except urllib.error.HTTPError as exc:
                if exc.code not in _REDIRECT_CODES or redirect_count == _MAX_REDIRECTS:
                    raise FileDownloadError("file download failed") from exc
                location = exc.headers.get("Location")
                if not location:
                    raise FileDownloadError("file download redirect is invalid") from exc
                current_url = urljoin(current_url, location)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                raise FileDownloadError("file download failed") from exc
        if response is None:
            raise FileDownloadError("file download failed")

        output_path = destination_dir / f"upload_{index:04d}.media"
        total_bytes = 0
        try:
            with response, output_path.open("wb") as output:
                content_length = getattr(response, "headers").get("Content-Length")
                if content_length is not None and int(content_length) > max_file_bytes:
                    raise FileDownloadError("file exceeds configured size limit")
                while True:
                    chunk = response.read(_CHUNK_BYTES)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_file_bytes:
                        raise FileDownloadError("file exceeds configured size limit")
                    output.write(chunk)
        except (OSError, ValueError) as exc:
            output_path.unlink(missing_ok=True)
            if isinstance(exc, FileDownloadError):
                raise
            raise FileDownloadError("file download failed") from exc
        staged.append(output_path)

    return staged
