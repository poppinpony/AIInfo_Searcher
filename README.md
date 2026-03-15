============================================================
  自動資訊蒐集工具 — 安裝與使用說明
============================================================

【必要環境】
  Python 3.9 以上（建議 3.12）
  下載：https://www.python.org/downloads/

------------------------------------------------------------
  STEP 1 — 建立虛擬環境（建議，可跳過）
------------------------------------------------------------

  cd T:\WorkS\AlInfo_Searcher

  # 建立 venv
  python -m venv .venv

  # 啟動 venv（PowerShell）
  .\.venv\Scripts\Activate.ps1

  # 啟動 venv（CMD）
  .\.venv\Scripts\activate.bat

------------------------------------------------------------
  STEP 2 — 安裝必要套件
------------------------------------------------------------

  pip install duckduckgo-search PyYAML requests schedule google-search-results playwright

  # 安裝 Playwright 瀏覽器（約 130MB，截圖功能需要）
  playwright install chromium

------------------------------------------------------------
  STEP 3 — 編輯設定檔 config.yaml
------------------------------------------------------------

  用任意文字編輯器開啟 config.yaml，修改以下項目：

  1. keywords — 要監控的關鍵詞列表（每行一個，前面加 - ）
     範例：
       keywords:
         - "Elon Musk"
         - "Tesla"

  2. people — 要監控的人物列表
     範例：
       people:
         - "黃仁勳"

  3. discord.webhook_url — Discord Webhook URL
     取得方式：Discord 頻道 → 編輯頻道 → 整合 → Webhook → 新 Webhook → 複製 URL
     範例：
       webhook_url: "https://discord.com/api/webhooks/123456789/abcdefg..."

  4. schedule.interval — 執行間隔數字
  5. schedule.unit     — minutes（分鐘）或 hours（小時）
     範例（每 30 分鐘執行一次）：
       schedule:
         interval: 30
         unit: "minutes"

------------------------------------------------------------
  STEP 4 — 執行
------------------------------------------------------------

  # 驗證設定檔是否正確
  python Info_Searcher.py --validate-config

  # 測試執行一次（確認搜尋、截圖、Discord 是否正常）
  python Info_Searcher.py --run-once

  # 正式啟動（依排程持續執行，Ctrl+C 停止）
  python Info_Searcher.py

------------------------------------------------------------
  輸出結果位置
------------------------------------------------------------

  output/
    results_YYYYMMDD_HHMM.json   ← 每次搜尋結果（JSON 格式）
    screenshots/
      YYYYMMDD_HHMM_網站名.png   ← 網頁截圖

  logs/
    collector.log                ← 執行日誌

------------------------------------------------------------
  常見問題
------------------------------------------------------------

  Q: 出現「No module named 'xxx'」
  A: 執行 pip install xxx 安裝缺少的套件

  Q: 截圖功能不工作
  A: 確認已執行 playwright install chromium

  Q: Discord 沒收到訊息
  A: 確認 config.yaml 的 webhook_url 已填入正確 URL
     且 discord.enabled 設為 true

  Q: 不想要截圖功能（速度太慢）
  A: 將 config.yaml 中的 screenshot.enabled 設為 false

  Q: 不想發到 Discord，只想存檔
  A: 將 config.yaml 中的 discord.enabled 設為 false

============================================================
