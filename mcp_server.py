import io
import os
import re
from pathlib import Path
from urllib.parse import unquote

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Transport is chosen at process start (see __main__ block below):
# - stdio (default): read/write JSON-RPC over stdin/stdout, for a client that
#   spawns this script as a local subprocess.
# - streamable-http: run this as a standalone, long-lived network service so
#   remote clients can reach it over HTTP.
#   Host/port only matter for streamable-http; they're ignored for stdio.
mcp = FastMCP(
    "K600VideoPredictMCP",
    log_level="ERROR",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8210")),
)

# Videos live on disk under this directory instead of an in-memory dict.
# Adjust if K600test isn't next to mcp_server.py, or run the process with
# this as the working directory.
VIDEOS_DIR = Path("K600test")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

K600_PREDICT_URL = "http://103.124.75.123:8000/predict/"


def _resolve_video_path(video_id: str) -> Path:
    video_path = VIDEOS_DIR / video_id
    if not video_path.exists():
        raise ValueError(f"Video with id {video_id} not found")
    return video_path


# Write a resource to return all video id's
@mcp.resource(
    "videos://videos",
    mime_type="application/json"
)
def list_videos() -> list[str]:
    video_list = VIDEOS_DIR.iterdir()
    video_list = [video for video in video_list if video.suffix.lower() in VIDEO_EXTENSIONS]
    return [video.name for video in video_list]


# Write a resource to return the file path of a particular video
@mcp.resource(
    "videos://videos/{video_id}",
    mime_type="text/plain"
)
def fetch_video(video_id: str) -> str:
    video_path = _resolve_video_path(video_id)
    return str(video_path)


def _call_k600_predict(file_obj, filename: str):
    """Shared K600 call used by both the local-file and URL-based tools."""
    try:
        response = httpx.post(
            K600_PREDICT_URL,
            files={"file": (filename, file_obj)},
            timeout=300.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise ValueError(f"An error occurred while requesting {e.request.url!r}.") from e
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Error response {e.response.status_code} while requesting {e.request.url!r}: "
            f"{e.response.text}"
        ) from e


@mcp.tool(
    name="video_predict",
    description="Predict the contents of a video that already lives in the local K600test/ folder."
)
def video_predict(
    video_id: str = Field(
        description="Id of the video to predict (see the videos:// resource for available ids)"
    )
):
    video_path = _resolve_video_path(video_id)
    with open(video_path, "rb") as file_obj:
        return _call_k600_predict(file_obj, video_path.name)


def _filename_from_content_disposition(headers: httpx.Headers) -> str | None:
    disposition = headers.get("content-disposition", "")
    match = re.search(r"filename\*=UTF-8''([^;]+)", disposition, re.IGNORECASE)
    if match:
        return unquote(match.group(1))
    match = re.search(r'filename="?([^";]+)"?', disposition, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


@mcp.tool(
    name="video_predict_url",
    description=(
        "Predict the contents of a video given a downloadable URL. "
        "Use this instead of video_predict when the video isn't already "
        "in the local K600test/ folder."
    )
)
def video_predict_url(
    video_url: str = Field(description="A URL the video can be downloaded from")
):
    try:
        download = httpx.get(video_url, timeout=300.0, follow_redirects=True)
        download.raise_for_status()
    except httpx.RequestError as e:
        raise ValueError(f"Could not download video from {video_url!r}: {e}") from e
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Error response {e.response.status_code} while downloading {video_url!r}."
        ) from e

    filename = (
        _filename_from_content_disposition(download.headers)
        or Path(httpx.URL(video_url).path).name
        or "video.mp4"
    )
    return _call_k600_predict(io.BytesIO(download.content), filename)


if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "stdio"))
