import asyncio

from mcp import Client

from autovd.mcp_server import mcp


async def _exercise_server() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == {
            "health",
            "get_temporal_analysis_demo",
        }

        health_result = await client.call_tool("health", {})
        assert health_result.is_error is False
        assert health_result.structured_content == {
            "service": "autovd",
            "status": "ok",
            "version": "0.1.0-dev",
        }

        unconfigured_result = await client.call_tool("get_temporal_analysis_demo", {})
        assert unconfigured_result.is_error is True
        assert "AUTOVD_SPIKE_VIDEO" in unconfigured_result.content[0].text


def test_tools_are_listed_and_callable() -> None:
    asyncio.run(_exercise_server())
