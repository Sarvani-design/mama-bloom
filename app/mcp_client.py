# Day 2: MCP client - connects to mcp_server.py over real stdio transport
# instead of importing its tool functions in-process.

import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

_session: ClientSession | None = None
_exit_stack: AsyncExitStack | None = None


async def start_mcp_client(project_root: str) -> None:
    global _session, _exit_stack
    _exit_stack = AsyncExitStack()
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        cwd=project_root,
    )
    read, write = await _exit_stack.enter_async_context(stdio_client(params))
    _session = await _exit_stack.enter_async_context(ClientSession(read, write))
    await _session.initialize()


async def stop_mcp_client() -> None:
    global _session, _exit_stack
    if _exit_stack is not None:
        await _exit_stack.aclose()
    _session = None
    _exit_stack = None


def _unwrap(result: CallToolResult) -> dict:
    # FastMCP only populates structuredContent when the tool's return type
    # annotation is specific enough to derive a JSON schema from (our tools
    # are annotated plain `dict`, so it isn't) - fall back to parsing the
    # JSON text content, which is always populated.
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


async def save_session(**kwargs) -> dict:
    result = await _session.call_tool("save_session", arguments=kwargs)
    return _unwrap(result)


async def get_streak() -> dict:
    result = await _session.call_tool("get_streak", arguments={})
    return _unwrap(result)


async def save_baby_book_entry(**kwargs) -> dict:
    result = await _session.call_tool("save_baby_book_entry", arguments=kwargs)
    return _unwrap(result)


async def get_yesterday_activities() -> dict:
    result = await _session.call_tool("get_yesterday_activities", arguments={})
    return _unwrap(result)
