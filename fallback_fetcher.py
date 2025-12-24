"""Cookie-less fallback fetchers for LinkedIn public pages.

Provides best-effort HTML retrieval via third-party renderers and caches
without using authentication cookies.
"""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def fetch_via_jina_reader(url: str, timeout: int = 20) -> Optional[str]:
    try:
        proxy_url = f"https://r.jina.ai/http://{url.lstrip('http://').lstrip('https://')}"
        resp = requests.get(proxy_url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code == 200 and resp.text:
            logger.info("Jina Reader fetched content: %d chars", len(resp.text))
            return resp.text
        logger.warning("Jina Reader failed: %s", resp.status_code)
        return None
    except Exception as e:
        logger.warning("Jina Reader error: %s", e)
        return None


def fetch_via_google_cache(url: str, timeout: int = 20) -> Optional[str]:
    try:
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
        resp = requests.get(cache_url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code == 200 and resp.text:
            logger.info("Google cache fetched content: %d chars", len(resp.text))
            return resp.text
        logger.warning("Google cache failed: %s", resp.status_code)
        return None
    except Exception as e:
        logger.warning("Google cache error: %s", e)
        return None


def fetch_via_wayback(url: str, timeout: int = 20) -> Optional[str]:
    try:
        avail = requests.get(
            "https://archive.org/wayback/available",
            params={"url": url},
            headers=DEFAULT_HEADERS,
            timeout=timeout,
        ).json()
        closest = avail.get('archived_snapshots', {}).get('closest', {})
        if closest and closest.get('available') and closest.get('url'):
            snap_url = closest['url']
            resp = requests.get(snap_url, headers=DEFAULT_HEADERS, timeout=timeout)
            if resp.status_code == 200 and resp.text:
                logger.info("Wayback fetched snapshot: %d chars", len(resp.text))
                return resp.text
        logger.warning("Wayback snapshot not available")
        return None
    except Exception as e:
        logger.warning("Wayback error: %s", e)
        return None
