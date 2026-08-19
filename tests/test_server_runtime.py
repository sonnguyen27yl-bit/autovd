import asyncio
import json

import pytest
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request

from autovd.mcp_server import http_health, main, mcp


def _health_request() -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/health",
            "raw_path": b"/health",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
        }
    )


def test_http_health_is_public_and_non_sensitive() -> None:
    response = asyncio.run(http_health(_health_request()))

    assert response.status_code == 200
    assert json.loads(response.body) == {"status": "ok"}


def test_main_uses_configured_bind_and_public_host_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setenv("AUTOVD_HOST", "0.0.0.0")
    monkeypatch.setenv("AUTOVD_PORT", "9000")
    monkeypatch.setenv(
        "AUTOVD_ALLOWED_HOSTS",
        "autovd.example.com,autovd.example.com:*",
    )
    monkeypatch.setattr(mcp, "run", fake_run)

    main()

    assert captured["transport"] == "streamable-http"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9000
    assert captured["stateless_http"] is True
    assert captured["json_response"] is True
    security = captured["transport_security"]
    assert isinstance(security, TransportSecuritySettings)
    assert "autovd.example.com" in security.allowed_hosts
    assert "autovd.example.com:*" in security.allowed_hosts
    assert "127.0.0.1:*" in security.allowed_hosts


def test_main_rejects_invalid_public_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOVD_PORT", "70000")

    with pytest.raises(ValueError, match="AUTOVD_PORT"):
        main()
