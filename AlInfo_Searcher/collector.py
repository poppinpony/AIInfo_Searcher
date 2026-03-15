"""
collector.py — 搜尋邏輯與 JSON 儲存
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# 台灣時區 +08:00
TW_TZ = timezone(timedelta(hours=8))


def _normalize(raw: dict, keyword: str, source: str) -> dict:
    """將各來源原始資料統一為標準結構。"""
    return {
        "title": (raw.get("title") or "").strip(),
        "url": (raw.get("href") or raw.get("url") or raw.get("link") or "").strip(),
        "summary": (raw.get("body") or raw.get("snippet") or "").strip(),
        "source": source,
        "keyword": keyword,
        "fetched_at": datetime.now(TW_TZ).isoformat(),
    }


def search_duckduckgo(keyword: str, config: dict) -> list[dict]:
    """用 duckduckgo-search 搜尋單一關鍵詞，回傳標準化 dict 列表。"""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.error("duckduckgo-search 未安裝，執行 pip install duckduckgo-search")
        return []

    cfg = config["search"]["sources"]["duckduckgo"]
    max_results = cfg.get("max_results", 10)
    region = cfg.get("region", "zh-tw")
    safesearch = cfg.get("safesearch", "moderate")

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(keyword, region=region, safesearch=safesearch, max_results=max_results):
                results.append(_normalize(r, keyword, "duckduckgo"))
        logger.debug("DuckDuckGo [%s]: %d 筆結果", keyword, len(results))
    except Exception as e:
        logger.warning("DuckDuckGo 搜尋失敗 [%s]: %s", keyword, e)
    return results


def search_serpapi(keyword: str, config: dict) -> list[dict]:
    """用 SerpAPI 搜尋單一關鍵詞，回傳標準化 dict 列表。"""
    try:
        from serpapi import GoogleSearch
    except ImportError:
        logger.error("google-search-results 未安裝，執行 pip install google-search-results")
        return []

    cfg = config["search"]["sources"]["serpapi"]
    params = {
        "q": keyword,
        "api_key": cfg.get("api_key", ""),
        "num": cfg.get("max_results", 10),
        "gl": cfg.get("gl", "tw"),
        "hl": cfg.get("hl", "zh-tw"),
    }

    results = []
    try:
        search = GoogleSearch(params)
        organic = search.get_dict().get("organic_results", [])
        for r in organic:
            results.append(_normalize(
                {"title": r.get("title"), "url": r.get("link"), "body": r.get("snippet")},
                keyword, "serpapi"
            ))
        logger.debug("SerpAPI [%s]: %d 筆結果", keyword, len(results))
    except Exception as e:
        logger.warning("SerpAPI 搜尋失敗 [%s]: %s", keyword, e)
    return results


def collect_all(config: dict) -> list[dict]:
    """
    依 config 中的 keywords + people 列表，
    呼叫啟用的搜尋來源，合併結果並依 URL 去重。
    """
    all_keywords = config.get("keywords", []) + config.get("people", [])
    sources_cfg = config["search"]["sources"]

    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for keyword in all_keywords:
        if not keyword:
            continue

        if sources_cfg.get("duckduckgo", {}).get("enabled", False):
            for r in search_duckduckgo(keyword, config):
                if r["url"] and r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)

        if sources_cfg.get("serpapi", {}).get("enabled", False):
            for r in search_serpapi(keyword, config):
                if r["url"] and r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)

    logger.info("共蒐集 %d 筆結果（去重後）", len(all_results))
    return all_results


def save_json(results: list[dict], config: dict) -> str:
    """
    將結果儲存至 output/ 目錄。
    檔名格式：results_YYYYMMDD_HHMM.json
    回傳儲存路徑。
    """
    output_dir = config.get("output", {}).get("dir", "output")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now(TW_TZ).strftime("%Y%m%d_%H%M")
    filename = f"results_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("結果已儲存：%s (%d 筆)", filepath, len(results))
    return filepath


def cleanup_old_files(config: dict) -> None:
    """刪除超過 retention_days 的 JSON 結果檔（retention_days=0 表示永久保留）。"""
    retention_days = config.get("output", {}).get("retention_days", 30)
    if retention_days == 0:
        return

    output_dir = config.get("output", {}).get("dir", "output")
    if not os.path.isdir(output_dir):
        return

    cutoff = datetime.now(TW_TZ) - timedelta(days=retention_days)
    for fname in os.listdir(output_dir):
        if not fname.startswith("results_") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(output_dir, fname)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=TW_TZ)
        if mtime < cutoff:
            os.remove(fpath)
            logger.info("已刪除過期檔案：%s", fpath)
