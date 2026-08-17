import asyncio

from mcp import Client

from autovd.mcp_server import mcp


async def _exercise_server() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        listed = await client.list_tools()
        assert [tool.name for tool in listed.tools] == ["health"]

        result = await client.call_tool("health", {})
        assert result.is_error is False
        assert result.structured_content == {
            "service": "autovd",
            "status": "ok",
            "version": "0.1.0-dev",
        }


def test_health_tool_is_listed_and_callable() -> None:
    asyncio.run(_exercise_server())
