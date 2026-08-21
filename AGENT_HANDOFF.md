# AGENT HANDOFF — AWS Affiliate Threads Post Generator

## 系統概覽

每 5 分鐘透過 GitHub Actions 自動從 `url.txt` 取一個 Amazon affiliate URL，用 Gemini AI 生成 Threads 貼文，發布到 Threads，並記錄已處理的 URL。

---

## 目前狀態（2026-08-21）

**✅ 完全運作中**
- GitHub Actions cron `*/45 * * * *` 每 45 分鐘自動執行（每天約 32 篇）
- Gemini 生成貼文（字元卡控 ≤ 500，超過自動重試最多 3 次）
- Threads API 發布成功
- Amazon affiliate URL 保留 `tag=thenewssam-20`
- 商品縮圖顯示正常（使用 `amazon.com/dp/ID?tag=` 格式）
- url.txt 共 43 個 URL，已處理約 12 個

---

## 檔案結構

```
threads_aws/
├── .github/
│   └── workflows/
│       └── hourly.yml          # GitHub Actions workflow（每 5 分鐘執行）
├── src/
│   ├── main.py                 # 主流程：讀 URL → 生成 → 發布 → 記錄
│   ├── generator.py            # Gemini API，含字元卡控重試邏輯
│   ├── publisher.py            # Threads API（Meta Graph API）
│   └── scraper.py              # HTML 抓取（目前未使用，Gemini 直接用 URL）
├── url.txt                     # 待處理的 Amazon affiliate URL 清單
├── processed_urls.txt          # 已處理的 URL（自動管理，勿手動修改）
├── output/                     # 生成的貼文存檔（YYYY-MM-DD-HH-MM.txt）
├── requirements.txt
└── .env                        # 本地環境變數（不推到 GitHub）
```

---

## GitHub Secrets（必須設定）

| Secret | 說明 |
|--------|------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `THREADS_ACCESS_TOKEN` | Meta Threads long-lived token（60天過期，需定期更新） |
| `THREADS_USER_ID` | `28106974412248485` |

---

## 環境變數（.env 本地）

```
GEMINI_API_KEY=...
THREADS_ACCESS_TOKEN=...
THREADS_USER_ID=28106974412248485
```

---

## 核心邏輯

### main.py 流程
1. 讀 `url.txt`，跳過已在 `processed_urls.txt` 的 URL
2. 取第一個未處理 URL
3. 呼叫 `generate(url)` 生成貼文
4. 存到 `output/YYYY-MM-DD-HH-MM.txt`
5. 把 URL 加到 `processed_urls.txt`
6. 呼叫 `publish_to_threads()` 發布

Exit codes: `0`=成功, `1`=錯誤, `2`=無可用 URL

### generator.py 字元卡控
- Threads 上限 500 字元
- URL 用 `amazon.com/dp/ID?tag=thenewssam-20` 格式（~54 字元）
- Post body 上限 440 字元（`CHAR_LIMIT`）
- 超過限制時最多 retry 3 次（每次把 prompt 限制縮緊 40 字元）
- 最終若仍超過，hard truncate 在單詞邊界

### publisher.py URL 處理
- 傳進來的 post_text 末尾已是 clean URL（generator 負責）
- 從 post_text 末尾抓 URL，用 `_clean_amazon_url()` 確保格式正確
- `_clean_amazon_url()` 用 `urllib.parse` 正確解析 `tag=` 參數

---

## Gemini 模型 fallback chain

```python
MODEL_CHAIN = [
    "models/gemini-3.5-flash",       # 主要
    "models/gemini-3.6-flash",       # 備用 1
    "models/gemini-3.5-flash-lite",  # 備用 2
    "models/gemini-flash-latest",    # 備用 3
]
```

503/unavailable 時自動切換下一個模型。

---

## Threads Access Token 更新方式

Token 每 60 天過期，需要手動更新：

1. 去 https://developers.facebook.com/tools/explorer/
2. 選 App `1536373420985324`（threads-automation）
3. 點 "Generate Threads Access Token"
4. 取得 short-lived token 後換 long-lived：
   ```
   curl -G "https://graph.threads.net/access_token" \
     --data-urlencode "grant_type=th_exchange_token" \
     --data-urlencode "client_id=1536373420985324" \
     --data-urlencode "client_secret=6dc6d1dc891e4b34cbdb75c494be4605" \
     --data-urlencode "access_token=<short_lived_token>"
   ```
5. 把 long-lived token 更新到：
   - GitHub Secrets → `THREADS_ACCESS_TOKEN`
   - 本地 `.env` → `THREADS_ACCESS_TOKEN`

---

## 新增 URL 方式

直接在 `url.txt` 新增一行 Amazon affiliate URL，然後用終端機 push：

```bash
cd /Users/sam/Desktop/程市區/threads_aws
git add url.txt
git commit -m "add: new affiliate URLs"
git push
```

系統會自動在下次執行時處理新的 URL。已處理過的在 `processed_urls.txt`，不會重複發。

---

## 常見問題排查

| 問題 | 原因 | 解法 |
|------|------|------|
| `Failed to decrypt` | Token 無效或格式錯誤 | 重新生成 long-lived token |
| `500 Server Error` | 貼文超過 500 字元 | 字元卡控已自動處理 |
| `503 UNAVAILABLE` | Gemini 模型繁忙 | 自動 fallback 到下一個模型 |
| `All models failed` | 所有 Gemini 模型暫時不可用 | 等下次 cron 自動重試（URL 不會被標記為已處理）|
| `0 workflow runs` | workflow 檔案改動才會觸發 push | 任何 commit push 都會觸發 |

---

## Meta App 資訊

- App ID: `1536373420985324`
- App Name: threads-automation
- App Secret: `6dc6d1dc891e4b34cbdb75c494be4605`
- Threads User ID: `28106974412248485`
- Threads Username: johnthenewss

---

## 測試指令（本地）

```bash
cd /Users/sam/Desktop/程市區/threads_aws
source venv/bin/activate
export $(grep -v "^#" .env | xargs)
python src/main.py
```

---

## 下一步（可選改進）

- [ ] Token 快過期時自動 email 提醒
- [ ] 每次 run 完後 pull latest（避免 git conflict）
- [ ] 改回 hourly cron（`0 * * * *`）正式上線後
- [ ] 加更多 URL 進 `url.txt`（現有 43 個，已處理 11 個）
