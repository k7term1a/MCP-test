# K600 Video Predict MCP Server

An MCP (Model Context Protocol) server that predicts the action happening in a
video using a Kinetics-600 (K600) recognition service. Built with the
official Python `mcp` SDK (`FastMCP`).

## What it provides

Two tools:

| Tool | Parameters | Description |
|---|---|---|
| `video_predict` | `video_id: str` | Predicts a video that already lives in the local `K600test/` folder. `video_id` is just the filename. |
| `video_predict_url` | `video_url: str` | Downloads a video from a URL and predicts it. Use this when the video isn't already in `K600test/`. |

Two resources for discovering what's available locally:

| Resource | Description |
|---|---|
| `videos://videos` | Lists the video ids (filenames) available in `K600test/` |
| `videos://videos/{video_id}` | Returns the local file path for a given video id |

Both tools return the raw JSON from the K600 recognition service, e.g.:

```json
{
  "filename": "1600.mp4",
  "model_mode": "Kinetics-600 (K600)",
  "predictions": [
    {"rank": 1, "action_name": "unloading truck (卸貨)", "confidence": 97.67, "confidence_str": "97.67%"}
  ],
  "inference_time_sec": 1.89,
  "status": "success"
}
```

## Prerequisites

- Python 3.10+
- Network access to the K600 recognition service (hardcoded as
  `K600_PREDICT_URL` in `mcp_server.py`, currently
  `http://103.124.75.123:8000/predict/`)
- A `K600test/` folder next to `mcp_server.py`, populated with video files
  (`.mp4`/`.mov`/`.avi`/`.mkv`), if you plan to use `video_predict` (not
  needed for `video_predict_url`)

## Setup

```bash
pip install uv        # if you don't have it already
uv sync
```

## Running the server

The transport is chosen via environment variables at process start:

```bash
# stdio (default) — for a client that spawns this script as a subprocess.
# No env vars needed.
uv run mcp_server.py

# streamable-http — run as a standalone, long-lived network service that
# remote clients connect to over HTTP.
MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=8210 uv run mcp_server.py
```

In `streamable-http` mode the server listens at `http://<host>:<port>/mcp`
(the `/mcp` path is fixed). It needs to stay running as a long-lived
process — use `systemd`, `tmux`, `nohup ... &`, or similar, rather than a
one-off foreground run.

## Connecting to it

### Connection notes

- **No authentication.** Anything that can reach the port can call every
  tool. Don't expose this to an untrusted network without adding your own
  auth (e.g. a header check in front of it) or firewalling by source IP.
- **Predictions can be slow.** The K600 call uses a 300-second timeout on
  the server side; if your client has its own timeout, set it generously
  (e.g. ≥ 300s / 5 minutes) rather than the default a few seconds most HTTP
  clients ship with.
- **`video_predict_url` fetches arbitrary URLs.** There's no domain
  allowlist. If you expose this tool to untrusted callers, consider adding
  one — otherwise it can be used as an SSRF pivot against your internal
  network.
- Any MCP client that supports the `streamable-http` transport can connect
  directly to `http://<host>:8210/mcp` — no special setup is otherwise
  required.

### Example: minimal Python client

See [`demo_client.py`](demo_client.py) for a runnable example using the
official `mcp` SDK. By default it spawns `mcp_server.py` itself over stdio
(zero setup beyond `uv sync`):

```bash
uv run demo_client.py
```

Or point it at an already-running `streamable-http` instance:

```bash
MCP_SERVER_URL=http://localhost:8210/mcp uv run demo_client.py
```

Predict a video from a URL instead of the local `K600test/` folder:

```bash
uv run demo_client.py https://example.com/some-video.mp4
```

## Development

`mcp_server.py` is a single file — no external `core/` package dependency.
The K600 endpoint (`K600_PREDICT_URL`) is a module-level constant if it ever
needs to change.
