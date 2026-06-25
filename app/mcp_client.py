# Day 2: MCP client - connects to mcp_server.py over real stdio transport
# instead of importing its tool functions in-process.

import asyncio
import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

_session: ClientSession | None = None
_exit_stack: AsyncExitStack | None = None

# Retries live here, not as ADK's per-node RetryConfig on memory_saver:
# exhausting a workflow-level RetryConfig surfaces as a fatal ctx.error that
# aborts the rest of the graph (see Known Limitations in README), which
# would turn a flaky MCP write into a failed check-in. A bounded retry at
# the transport layer recovers from transient subprocess hiccups while
# preserving agent.py's own try/except as the final graceful-degradation
# fallback if every attempt fails.
_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 0.5


async def _call_tool_with_retry(name: str, arguments: dict) -> CallToolResult:
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return await _session.call_tool(name, arguments=arguments)
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)
    raise last_exc


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
    result = await _call_tool_with_retry("save_session", kwargs)
    return _unwrap(result)


async def get_streak(user_id: str) -> dict:
    result = await _call_tool_with_retry("get_streak", {"user_id": user_id})
    return _unwrap(result)


async def save_baby_book_entry(**kwargs) -> dict:
    result = await _call_tool_with_retry("save_baby_book_entry", kwargs)
    return _unwrap(result)


async def get_yesterday_activities(user_id: str) -> dict:
    result = await _call_tool_with_retry("get_yesterday_activities", {"user_id": user_id})
    return _unwrap(result)
