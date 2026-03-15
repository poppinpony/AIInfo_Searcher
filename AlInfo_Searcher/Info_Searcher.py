"""
Info_Searcher.py — 主進入點：排程控制與模組協調

用法：
  python Info_Searcher.py                  # 排程模式（依 config.yaml 設定）
  python Info_Searcher.py --run-once       # 執行一次後結束（適合測試）
  python Info_Searcher.py --validate-config  # 只檢查設定檔是否正確
"""

import argparse
import logging
import os
import sys
import time

_MISSING = []
for _pkg, _import in [("schedule", "schedule"), ("PyYAML", "yaml"), ("requests", "requests")]:
    try:
        __import__(_import)
    except ImportError:
        _MISSING.append(_pkg)
if _MISSING:
    print(f"[錯誤] 缺少套件，請先執行：pip install {' '.join(_MISSING)}")
    sys.exit(1)

import schedule
import yaml

import collector
import notifier
import screenshot


# ---------------------------------------------------------------------------
# 設定讀取與驗證
# ---------------------------------------------------------------------------

def load_config(path: str = "config.yaml") -> dict:
    if not os.path.isfile(path):
        sys.exit(f"[錯誤] 找不到設定檔：{path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            sys.exit(f"[錯誤] config.yaml 語法錯誤：{e}")

    _validate_config(config)
    return config


def _validate_config(config: dict) -> None:
    errors = []

    # 排程設定
    unit = config.get("schedule", {}).get("unit", "")
    if unit not in ("minutes", "hours"):
        errors.append(f"schedule.unit 必須是 'minutes' 或 'hours'，目前為：'{unit}'")

    interval = config.get("schedule", {}).get("interval", 0)
    if not isinstance(interval, int) or interval <= 0:
        errors.append(f"schedule.interval 必須是正整數，目前為：{interval}")

    # Discord Webhook
    webhook = config.get("discord", {}).get("webhook_url", "")
    discord_enabled = config.get("discord", {}).get("enabled", True)
    if discord_enabled and webhook and not webhook.startswith("https://discord.com/api/webhooks/"):
        errors.append("discord.webhook_url 格式不正確，應以 https://discord.com/api/webhooks/ 開頭")

    # 輸出目錄可寫入
    output_dir = config.get("output", {}).get("dir", "output")
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        errors.append(f"無法建立輸出目錄 '{output_dir}'：{e}")

    if errors:
        for err in errors:
            print(f"[設定錯誤] {err}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 日誌初始化
# ---------------------------------------------------------------------------

def setup_logging(config: dict) -> None:
    log_cfg = config.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    log_file = log_cfg.get("file", "logs/collector.log")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------------------
# 核心流程
# ---------------------------------------------------------------------------

def run_once(config: dict) -> None:
    """執行一次完整的蒐集流程：搜尋 → 存 JSON → 截圖 → Discord。"""
    logger.info("===== 開始蒐集 =====")
    start = time.time()

    # 1. 搜尋
    results = collector.collect_all(config)
    if not results:
        logger.info("無結果，結束本次執行")
        return

    # 2. 儲存 JSON
    collector.save_json(results, config)

    # 3. 截圖
    screenshots = screenshot.take_screenshots(results, config)

    # 4. 發送至 Discord
    notifier.send_discord(results, screenshots, config)

    # 5. 清理舊檔
    collector.cleanup_old_files(config)

    elapsed = time.time() - start
    logger.info("===== 蒐集完成，耗時 %.1f 秒 =====", elapsed)


# ---------------------------------------------------------------------------
# 進入點
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="自動資訊蒐集工具")
    parser.add_argument("--config", default="config.yaml", help="設定檔路徑（預設 config.yaml）")
    parser.add_argument("--run-once", action="store_true", help="執行一次後結束")
    parser.add_argument("--validate-config", action="store_true", help="只驗證設定檔後結束")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config)

    if args.validate_config:
        print("[OK] 設定檔驗證通過")
        return

    if args.run_once:
        run_once(config)
        return

    # 排程模式
    interval = config["schedule"]["interval"]
    unit = config["schedule"]["unit"]

    if unit == "minutes":
        schedule.every(interval).minutes.do(run_once, config=config)
        logger.info("排程啟動：每 %d 分鐘執行一次", interval)
    else:
        schedule.every(interval).hours.do(run_once, config=config)
        logger.info("排程啟動：每 %d 小時執行一次", interval)

    # 啟動時先執行一次
    run_once(config)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
