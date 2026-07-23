"""
Minimal example of connecting to the K600 video-prediction MCP server.

By default this spawns mcp_server.py itself over stdio, so it works with
zero setup beyond `uv sync`. To instead connect to an already-running
streamable-http instance, set MCP_SERVER_URL, e.g.:

    MCP_SERVER_URL=http://localhost:8210/mcp uv run demo_client.py

Usage:
    uv run demo_client.py                 # predicts the first video found
                                           # in K600test/ via video_predict
    uv run demo_client.py <video-url>      # predicts a video at that URL
                                           # via video_predict_url
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


async def connect(stack: AsyncExitStack) -> ClientSession:
    server_url = os.getenv("MCP_SERVER_URL")

    if server_url:
        print(f"Connecting to {server_url} ...")
        read, write, _ = await stack.enter_async_context(
            streamablehttp_client(server_url)
        )
    else:
        print("No MCP_SERVER_URL set, spawning mcp_server.py over stdio ...")
        # A spawned MCP server only inherits a curated safe subset of the
        # parent's environment (see mcp.client.stdio.get_default_environment),
        # not custom vars like K600_PREDICT_URL — pass it through explicitly.
        k600_url = os.environ.get("K600_PREDICT_URL")
        if not k600_url:
            raise SystemExit(
                "K600_PREDICT_URL is not set. Export it before running this "
                "script, e.g. export K600_PREDICT_URL=http://<your-host>:8000/predict/"
            )
        params = StdioServerParameters(
            command="uv",
            args=["run", "mcp_server.py"],
            env={"K600_PREDICT_URL": k600_url},
        )
        read, write = await stack.enter_async_context(stdio_client(params))

    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    return session


async def main() -> None:
    video_url = sys.argv[1] if len(sys.argv) > 1 else None

    async with AsyncExitStack() as stack:
        session = await connect(stack)

        tools = await session.list_tools()
        print("Available tools:", [t.name for t in tools.tools])

        if video_url:
            print(f"\nCalling video_predict_url({video_url!r}) ...")
            result = await session.call_tool(
                "video_predict_url", {"video_url": video_url}
            )
        else:
            videos = await session.read_resource("videos://videos")
            video_ids = json.loads(videos.contents[0].text)
            if not video_ids:
                print("No videos found in K600test/ and no URL was given.")
                return
            video_id = video_ids[0]
            print(f"\nCalling video_predict({video_id!r}) ...")
            result = await session.call_tool("video_predict", {"video_id": video_id})

        for block in result.content:
            if block.type == "text":
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
