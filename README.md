# K600 影片動作辨識 MCP Server

一個 MCP（Model Context Protocol）伺服器，用來呼叫 K600（Kinetics-600）動作辨識服務，判斷影片裡發生了什麼動作。用官方 Python `mcp` SDK 的 `FastMCP` 寫的。

## 提供什麼

兩個 tool：

| Tool | 參數 | 說明 |
|---|---|---|
| `video_predict` | `video_id: str` | 辨識已經放在本機 `K600test/` 資料夾裡的影片，`video_id` 就是檔名 |
| `video_predict_url` | `video_url: str` | 從 URL 下載影片後辨識，影片不在本機 `K600test/` 時用這個 |

兩個 resource，用來查本機有哪些影片可用：

| Resource | 說明 |
|---|---|
| `videos://videos` | 列出 `K600test/` 裡所有可用的 video id（檔名） |
| `videos://videos/{video_id}` | 回傳某個 video id 對應的本機檔案路徑 |

兩個 tool 回傳的都是 K600 辨識服務的原始 JSON，例如：

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

## 前置需求

- Python 3.10+
- 一個 **K600 辨識服務**，並且知道它的 `/predict/` 端點網址（見下方「設定 K600 服務網址」）
- 如果要用 `video_predict`（吃本機檔案那個），`mcp_server.py` 旁邊要有一個 `K600test/` 資料夾，裡面放影片檔（`.mp4`/`.mov`/`.avi`/`.mkv`）；只用 `video_predict_url` 的話不需要這個資料夾

## 安裝

```bash
pip install uv        # 還沒裝過的話
uv sync
```

## 設定 K600 服務網址

這個 MCP server 不會綁死某一台 K600 服務，網址是透過環境變數 `K600_PREDICT_URL` 設定的——**如果你自己有架 K600 辨識服務，換成你自己的網址就能直接沿用這個 MCP server**：

```bash
export K600_PREDICT_URL=http://<你的-K600-主機>:8000/predict/
```

這個環境變數是必填的，沒設的話 `mcp_server.py` 一啟動就會直接報錯並清楚說明要設什麼。

## 啟動伺服器

Transport 是在啟動當下用環境變數決定：

```bash
# stdio（預設）——給會把這支程式當子行程 spawn 起來的 client 用，不用額外設 transport 相關變數
K600_PREDICT_URL=http://<你的-K600-主機>:8000/predict/ uv run mcp_server.py

# streamable-http——當成一個獨立、長駐的網路服務，讓遠端 client 用 HTTP 連進來
K600_PREDICT_URL=http://<你的-K600-主機>:8000/predict/ \
MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=8210 \
uv run mcp_server.py
```

`streamable-http` 模式下，伺服器會監聽 `http://<host>:<port>/mcp`（`/mcp` 這個路徑是固定的）。這個模式需要長駐執行，建議用 `systemd`、`tmux`、`nohup ... &` 之類的方式，不要用一次性的前景指令跑。

## 怎麼連上來

### 連線注意事項

- **目前沒有任何身分驗證**。只要連得到這個 port 就能呼叫所有 tool。如果不是在完全信任的網路環境，記得自己加一層驗證（例如檢查一個自訂 header）或用防火牆限制來源 IP。
- **辨識可能要花不少時間**。伺服器端對 K600 的呼叫設了 300 秒 timeout；如果你的 client 自己也有 timeout 設定，記得調寬一點（至少 300 秒/5 分鐘），不要用大多數 HTTP client 預設的那種幾秒鐘 timeout。
- **`video_predict_url` 會對任意 URL 發出請求**，沒有網域白名單機制。如果這個 tool 會暴露給不受信任的呼叫者，建議自己加上目的地網域檢查，避免被當成 SSRF 的跳板。
- 任何支援 `streamable-http` transport 的 MCP client，都可以直接連到 `http://<host>:8210/mcp`，不需要其他額外設定。

### 範例：最簡單的 Python client

參考 [`demo_client.py`](demo_client.py)，用官方 `mcp` SDK 寫的一個可以直接執行的範例。預設會自己把 `mcp_server.py` 當子行程用 stdio 接起來（除了 `uv sync` 之外不用額外設定）：

```bash
K600_PREDICT_URL=http://<你的-K600-主機>:8000/predict/ uv run demo_client.py
```

或是指向一個已經在跑的 `streamable-http` 伺服器（這個情境下 `K600_PREDICT_URL` 是設在伺服器那一端，demo_client 這邊不用設）：

```bash
MCP_SERVER_URL=http://localhost:8210/mcp uv run demo_client.py
```

辨識一個 URL 上的影片，而不是本機 `K600test/` 資料夾裡的：

```bash
K600_PREDICT_URL=http://<你的-K600-主機>:8000/predict/ uv run demo_client.py https://example.com/some-video.mp4
```

## 開發相關

`mcp_server.py` 是單一檔案，不依賴外部的 `core/` package。K600 端點網址（`K600_PREDICT_URL`）是必填的環境變數，不會寫死在程式碼裡。
