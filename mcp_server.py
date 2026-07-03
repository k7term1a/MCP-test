from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("DocumentMCP", log_level="ERROR")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}

# Write a tool to read a doc
@mcp.tool(
    name="read_doc_contents",
    description="Read the contents of a document and return it as a string."
)
def read_document(
    doc_id: str = Field(description="Id of the document to read")
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")

    return docs[doc_id]
    
# Write a tool to edit a doc
@mcp.tool(
    name="edit_document",
    description="Edit a document by replacing a string in the documents content with a new string."
)
def edit_document(
    doc_id: str = Field(description="Id of the document that will be edited"),
    old_str: str = Field(description="The text to replace. Must match exactly, including whitespace."),
    new_str: str = Field(description="The new text to insert in place of the old text.")
):
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not foune")
    docs[doc_id] = docs[doc_id].replace(old_str, new_str)

# Write a resource to return all doc id's
@mcp.resource(
    "docs://documents",
    mime_type="application/json"
)
def list_docs() -> list[str]:
    return list(docs.keys())

# Write a resource to return the contents of a particular doc
@mcp.resource(
    "docs://documents/{doc_id}",
    mime_type="text/plain"
)
def fetch_doc(doc_id: str) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with id {doc_id} not found")
    return docs[doc_id]

# Write a prompt to rewrite a doc in markdown format
@mcp.prompt(
    name="format",
    description="Rewrites the contents of the document in Markdown format."
)
def format_document(
    doc_id: str = Field(description="Id of the document to format")
) -> list[base.Message]:
    prompt = f"""
Your goal is to reformat a document to be written with markdown syntax.

The id of the document you need to reformat is:
<document_id>
{doc_id}
</document_id>

Add in headers, bullet points, tables, etc as necessary. Feel free to add in structure.
Use the 'edit_document' tool to edit the document. After the document has been reformatted...
"""
    
    return [
        base.UserMessage(prompt)
    ]

# Write a prompt to summarize a doc
@mcp.prompt(
    name="summarize",
    description="Summarize "
)
def summarize_document(
    doc_id: str = Field(description="Id of the document to summarize")
) -> str:
    prompt = f"""
Your goal is to create a concise and well-structured summary of a document.

The id of the document you need to summarize is:
<document_id>
{doc_id}
</document_id>

Produce a summary that captures the main ideas, key findings, important decisions, and action items (if any). Organize the summary using markdown syntax with appropriate headers, bullet points, and tables where helpful. Keep the summary concise while preserving the essential information.

Use the 'edit_document' tool to replace the document with the generated summary. After the document has been summarized...
"""
    
    return base.UserMessage(prompt)

# Videos live on disk under this directory instead of an in-memory dict.
# mcp_server.py runs as a local subprocess of the CLI app, so this path
# just needs to be readable on this machine. Adjust if K600test isn't
# next to mcp_server.py.
VIDEOS_DIR = Path("K600test")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}

K600_PREDICT_URL = "http://103.124.75.123:8000/predict/"


def _resolve_video_path(video_id: str) -> Path:
    # TODO: 組出 VIDEOS_DIR / video_id 的完整路徑
    # TODO: 用 .exists()（也可以順便檢查 .is_file()）確認檔案存在，
    #       不存在就 raise ValueError(f"Video with id {video_id} not found")
    # TODO: 回傳這個 Path
    pass


# Write a resource to return all video id's (mirrors list_docs above)
@mcp.resource(
    "videos://videos",
    mime_type="application/json"
)
def list_videos() -> list[str]:
    # TODO: 用 VIDEOS_DIR.iterdir() 掃出目錄下的檔案
    # TODO: 只留下副檔名在 VIDEO_EXTENSIONS 裡的檔案（用 .suffix.lower()）
    # TODO: 回傳這些檔案的檔名（.name）組成的 list，當作 video_id
    pass

# Write a resource to return the file path of a particular video (mirrors fetch_doc above)
@mcp.resource(
    "videos://videos/{video_id}",
    mime_type="text/plain"
)
def fetch_video(video_id: str) -> str:
    # TODO: 呼叫 _resolve_video_path(video_id)，把結果轉成字串回傳
    pass

@mcp.tool(
    name="video_predict",
    description="Predict the contents of a video based on K600 video datasets."
)
def video_predict(
    video_id: str = Field(
        description="Id of the video to predict (see the videos:// resource for available ids)"
    )
):
    # TODO 1: 呼叫 _resolve_video_path(video_id) 拿到檔案路徑
    #         (video_id 不存在時它會自己 raise ValueError，不用重複檢查)

    # TODO 2: 用 open(path, "rb") 開檔，記得用 with 語法確保檔案用完會關閉

    # TODO 3: 用 httpx.post(K600_PREDICT_URL, files={"video": file_obj}, timeout=...)
    #         呼叫 K600 服務。影片辨識可能要花不少時間，timeout 記得抓寬一點

    # TODO 4: response.raise_for_status() 檢查狀態，並回傳 response.json()
    #         或整理過的精簡結果（提示：不要把 per-frame 完整結果整包塞回去，
    #         會佔用大量 tool result token）

    # TODO 5: 用 try/except 包住 httpx 呼叫，網路錯誤時 raise ValueError 並附上錯誤訊息
    pass


if __name__ == "__main__":
    mcp.run(transport="stdio")
