"""AutoVD MCP entrypoint."""

from mcp.server import MCPServer

from autovd import __version__
from autovd.diagnostic import diagnostic_status

mcp = MCPServer(
    "AutoVD",
    version=__version__,
    instructions=(
        "AutoVD prepares timestamped visual evidence for conservative AI-video cleanup. "
        "The MVP keeps uncertain footage and never executes model-generated shell commands."
    ),
)


@mcp.tool()
def health() -> dict[str, str]:
    """Return a stable, non-sensitive diagnostic payload."""
    return diagnostic_status()


def main() -> None:
    """Run the remote MCP endpoint using Streamable HTTP."""
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()
