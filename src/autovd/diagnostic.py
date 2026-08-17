"""Small deterministic diagnostic behavior used to prove the MCP contract."""

from autovd import __version__


def diagnostic_status() -> dict[str, str]:
    """Return a stable, non-sensitive service status payload."""
    return {
        "service": "autovd",
        "status": "ok",
        "version": __version__,
    }
