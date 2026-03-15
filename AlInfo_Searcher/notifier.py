"""
notifier.py — Discord Webhook 發送
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

_MAX_TITLE = 256
_MAX_DESC = 4096
_MAX_FOOTER = 2048


def _build_embed(result: dict, color: int) -> dict:
    """將單筆結果轉換為 Discord Embed JSON 結構。"""
    title = result.get("title", "（無標題）")[:_MAX_TITLE]
    url = result.get("url", "")
    summary = result.get("summary", "（無摘要）")[:_MAX_DESC]
    source = result.get("source", "")
    keyword = result.get("keyword", "")
    fetched_at = result.get("fetched_at", "")

    footer_text = f"來源：{source} | 關鍵詞：{keyword} | {fetched_at}"[:_MAX_FOOTER]

    embed = {
        "title": title,
        "description": summary,
        "color": color,
        "footer": {"text": footer_text},
    }
    if url:
        embed["url"] = url

    return embed


def _send_webhook(webhook_url: str, payload: dict) -> bool:
    """
    POST 單則訊息至 Discord Webhook。
    處理 429 Rate Limit，最多重試 3 次。
    """
    for attempt in range(3):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                return True
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 2)
                logger.warning("Discord rate limit，等待 %.1f 秒後重試...", retry_after)
                time.sleep(retry_after)
                continue
            logger.warning("Discord 回應異常：%d %s", resp.status_code, resp.text[:200])
            return False
        except requests.RequestException as e:
            logger.warning("Discord 發送失敗（第 %d 次）：%s", attempt + 1, e)
            if attempt < 2:
                time.sleep(2)
    return False


def send_discord(results: list[dict], screenshots: dict[str, str], config: dict) -> None:
    """
    發送搜尋結果至 Discord。
    每則訊息間隔 1 秒防洗版，依 max_messages_per_run 限制數量。
    截圖目前附於 embed footer（Discord Webhook 不支援直接附圖至 Embed，
    若需附圖可改用 multipart/form-data 上傳）。
    """
    discord_cfg = config.get("discord", {})
    if not discord_cfg.get("enabled", True):
        return

    webhook_url = discord_cfg.get("webhook_url", "")
    if not webhook_url or "YOUR_ID" in webhook_url:
        logger.warning("Discord Webhook URL 尚未設定，跳過發送")
        return

    max_msgs = discord_cfg.get("max_messages_per_run", 10)
    color = discord_cfg.get("embed_color", 3447003)

    sent = 0
    for result in results:
        if sent >= max_msgs:
            logger.info("已達本次發送上限 (%d 則)", max_msgs)
            break

        embed = _build_embed(result, color)
        payload = {"embeds": [embed]}

        # 若有截圖路徑，附加於 embed 欄位顯示
        url = result.get("url", "")
        if url in screenshots:
            embed.setdefault("fields", []).append({
                "name": "截圖",
                "value": f"`{screenshots[url]}`",
                "inline": False,
            })

        if _send_webhook(webhook_url, payload):
            sent += 1
            logger.debug("已發送第 %d 則：%s", sent, result.get("title", ""))
        else:
            logger.warning("發送失敗，跳過：%s", result.get("url", ""))

        time.sleep(1)

    logger.info("Discord 發送完成：%d / %d 則", sent, min(len(results), max_msgs))
