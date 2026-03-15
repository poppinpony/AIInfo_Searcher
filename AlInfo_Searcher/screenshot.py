"""
screenshot.py — Playwright 截圖
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

TW_TZ = timezone(timedelta(hours=8))


def _url_to_filename(url: str, timestamp: str) -> str:
    """將 URL 轉換為安全的檔名。"""
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/").replace("/", "_")
    safe = re.sub(r"[^\w\-]", "_", f"{host}_{path}")[:60]
    return f"{timestamp}_{safe}.png"


async def _take_single(page, url: str, output_path: str, timeout_ms: int) -> bool:
    """對單一 URL 截圖。失敗回傳 False，不中斷整體流程。"""
    try:
        await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        await page.screenshot(path=output_path, full_page=False)
        logger.debug("截圖成功：%s", output_path)
        return True
    except Exception as e:
        logger.warning("截圖失敗 [%s]: %s", url, e)
        return False


async def _take_screenshots_async(results: list[dict], config: dict) -> dict[str, str]:
    """非同步截圖主邏輯。"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("playwright 未安裝，執行: pip install playwright && playwright install chromium")
        return {}

    shot_cfg = config.get("screenshot", {})
    max_per_run = shot_cfg.get("max_per_run", 5)
    timeout_ms = shot_cfg.get("timeout_ms", 15000)
    width = shot_cfg.get("viewport_width", 1280)
    height = shot_cfg.get("viewport_height", 800)

    output_dir = os.path.join(
        config.get("output", {}).get("dir", "output"),
        config.get("output", {}).get("screenshots_subdir", "screenshots"),
    )
    os.makedirs(output_dir, exist_ok=True)

    # 限制截圖數量，只取有 URL 的結果
    targets = [r for r in results if r.get("url")][:max_per_run]
    timestamp = datetime.now(TW_TZ).strftime("%Y%m%d_%H%M")
    url_to_path: dict[str, str] = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": width, "height": height})

        for result in targets:
            url = result["url"]
            filename = _url_to_filename(url, timestamp)
            output_path = os.path.join(output_dir, filename)
            success = await _take_single(page, url, output_path, timeout_ms)
            if success:
                url_to_path[url] = output_path

        await browser.close()

    logger.info("截圖完成：%d / %d 張成功", len(url_to_path), len(targets))
    return url_to_path


def take_screenshots(results: list[dict], config: dict) -> dict[str, str]:
    """同步包裝函式，供 main 呼叫。截圖未啟用時直接回傳空字典。"""
    if not config.get("screenshot", {}).get("enabled", True):
        return {}
    return asyncio.run(_take_screenshots_async(results, config))
