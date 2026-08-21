# Agent Handoff — AWS Affiliate Threads Post Generator

## 系統說明

GitHub Actions 自動化系統。每小時執行一次，自動：
1. 讀 `url.txt` 的 AWS 文章網址
2. 檢查 `processed_urls.txt` 確認哪些已處理過
3. 挑一個從沒處理過的網址
4. 抓取文章內容
5. 用 Gemini AI 生成 150–200 字 Threads 貼文
6. 存到 `output/` 目錄（UTC 時間戳命名）
7. 更新 `processed_urls.txt`
8. 自動 commit & push 回 GitHub

---

## 專案結構

```
threads_aws/
├── url.txt                    ← 用戶放 AWS 文章網址（一行一個）
├── processed_urls.txt         ← 自動管理，勿手動編輯
├── src/
│   ├── main.py               ← 主程式（讀 URL → 生成 → 存檔 → 更新）
│   ├── scraper.py            ← 抓取文章內容（trafilatura + BS4）
│   ├── generator.py          ← Gemini 貼文生成（臺灣資深工程師風格）
│   └── publisher.py          ← Threads 發布 stub（待實做）
├── output/                   ← 生成的貼文存這裡
├── .github/workflows/
│   └── hourly.yml            ← GitHub Actions 每小時執行
├── requirements.txt          ← Python 依賴
└── .env                      ← API 金鑰（勿 commit）
```

---

## .env 設定

| 變數 | 說明 |
|------|------|
| GEMINI_API_KEY | Google Gemini API Key |

**本地運行**：複製 `.env.example` 為 `.env`，填入金鑰。

**GitHub Actions**：在 repo 的 **Settings → Secrets and variables → Actions** 新增名為 `GEMINI_API_KEY` 的 secret。

---

## 用法

### 本地測試

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行一次
python src/main.py
```

### 自動化（推薦）

1. 把 AWS 文章網址加進 `url.txt`（一行一個）
2. Push 到 GitHub
3. 在 repo **Settings → Secrets and variables → Actions** 新增 `GEMINI_API_KEY` secret
4. GitHub Actions 會每小時自動執行

**手動觸發**：repo → **Actions** → **Generate Threads Post** → **Run workflow**

---

## Exit codes

| 代碼 | 含義 |
|------|------|
| 0 | 成功生成並存檔 |
| 1 | 錯誤（抓取失敗、生成失敗等） |
| 2 | 無可用 URL（所有 URL 都已處理過） |

---

## 貼文風格

- **150–200 字** 英文
- **臺灣資深雲工程師** 語氣：超級諷刺、尖銳、累但專業
- **第一句攻擊痛點**（無暖場）
- **短段落**（2–4 句）適合 Threads
- **自然引入產品** 當解決方案
- **結尾加沙雕 CTA**
- 最後一行是文章原始網址
- **最多 1–2 個 emoji**
- 零 AI 制式用語（"game-changer", "leverage" 等免談）

---

## GitHub 部署

**Repo:** https://github.com/fsdhygefdhyter/thread

**已設定的 Secrets:**
- `GEMINI_API_KEY` ✅
- `THREADS_ACCESS_TOKEN` ✅
- `THREADS_USER_ID` ✅

---

## Threads API 整合（待啟用）

**狀態：⏳ 準備好，暫未啟用**

### 目前狀態

- ✅ 系統已完全架構好，可隨時啟用
- ✅ Threads credentials 已在 GitHub Secrets 配置
- ⏳ 發布功能暫停用（stub 模式）——貼文只會存到 `output/` 不會發布

### 貼文流程

每次執行時：
1. 讀一個未處理的 AWS 文章 URL
2. 抓取內容 + 用 Gemini 生成 Threads 貼文
3. 存檔到 `output/YYYY-MM-DD-HH-MM.txt`
4. 更新 `processed_urls.txt`
5. Commit & push 到 GitHub
6. **（目前停用）** 發布到 Threads

### 何時啟用 Threads 發布

當準備好正式發布時：

1. 在 `src/publisher.py` 實做 API 呼叫（git history commit `2e60899` 有完整實做）
2. 確認 `src/main.py` Threads 發布區塊已啟用
3. Push 到 GitHub
4. 下個執行週期起，貼文會自動發布到你的 Threads 帳號

### Token 說明

- **User ID**: `28106974412248485`
- **Access Token**: 已在 GitHub Secrets 設定
- **App ID**: `1536373420985324`

### Access Token 更新

Threads API token 有效期約 60 天。快過期時：
1. 去 https://developers.facebook.com/tools/explorer
2. 重新產生新 token
3. 更新 GitHub Secrets 中的 `THREADS_ACCESS_TOKEN`

系統會自動使用新 token。

---

## 重點筆記

- `url.txt`：用戶專用，加多少網址就處理多少
- `processed_urls.txt`：永遠不要手動編輯，系統自動維護去重
- `output/` 內的檔案會被 commit 回 GitHub（方便保留記錄）
- 每次執行只處理 **一個** URL（防止 API 額度爆炸）
- 抓取或生成失敗時，不會標記該 URL 為已處理（下次會重試）
- 所有相對路徑都基於 repo root（`src/main.py` 會自動解析）
