"""
PC Deals Scraper – v3
=====================
Requirements:
    pip install curl-cffi praw feedparser

Reddit setup (one-time):
    1. Go to https://www.reddit.com/prefs/apps -> create a "script" app
    2. Set env vars:  REDDIT_CLIENT_ID  REDDIT_CLIENT_SECRET  REDDIT_USERNAME

Key architectural changes from v2:
  - curl_cffi.AsyncSession  - native async HTTP with real Chrome TLS fingerprint
    (bypasses Cloudflare / bot-detection without a thread-pool executor)
  - PRAW  - Reddit's official API; no more 403s
  - asyncio.Semaphore  - caps concurrent connections to avoid overwhelming sources
  - Circuit breaker  - sources that fail repeatedly are skipped for the rest of the run
  - Dead sources removed (CamelCamelCamel, Geizhals, Pangoly, PCPrice.watch)
  - Correct Slickdeals / Newegg / B&H / Best Buy URLs
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import feedparser
import praw
from curl_cffi.requests import AsyncSession

# ---------------------------------------------------------------------------
# Keyword / signal tables
# ---------------------------------------------------------------------------

KEYWORDS: Dict[str, List[str]] = {
    "GPU": [
        "rtx 4060", "rtx 4070", "rtx 4080", "rtx 4090",
        "rx 7600", "rx 7700", "rx 7800", "rx 7900",
        "geforce rtx", "radeon rx", "graphics card", "video card", "gpu",
        "rtx", "geforce", "radeon", "4060", "4070", "4080", "4090",
    ],
    "CPU": [
        "ryzen 5", "ryzen 7", "ryzen 9",
        "core i5", "core i7", "core i9",
        "intel cpu", "amd cpu", "processor",
        "7800x3d", "7700x", "7600x", "9700x",
        "13600k", "14600k", "14700k",
        "ryzen", "cpu", "x3d",
    ],
    "RAM": [
        "ddr4 ram", "ddr5 ram", "desktop memory", "gaming memory",
        "udimm", "dimm", "ram kit", "memory kit",
        "16gb ddr5", "32gb ddr5", "64gb ddr5",
        "16gb ddr4", "32gb ddr4", "64gb ddr4",
        "ddr4", "ddr5",
    ],
    "SSD": [
        "nvme ssd", "m.2 ssd", "pcie 4.0 ssd", "pcie 5.0 ssd",
        "internal ssd", "2.5 ssd", "solid state drive",
        "1tb ssd", "2tb ssd", "4tb ssd",
        "nvme", "internal ssd",
    ],
    "Motherboard": [
        "motherboard", "mobo",
        "b650", "x670", "b550", "x570",
        "z690", "z790", "b760",
        "am5 motherboard", "am4 motherboard", "lga1700 motherboard",
        "am5", "am4", "lga1700",
    ],
    "PSU": [
        "power supply", "psu",
        "atx 3.0", "atx 3.1", "80+ gold", "80+ platinum", "80+ bronze",
        "fully modular psu", "semi-modular psu",
        "650w psu", "750w psu", "850w psu", "1000w psu",
        "fully modular", "750w", "850w", "1000w",
    ],
    "Cooling": [
        "cpu cooler", "air cooler", "aio cooler", "liquid cooler",
        "360mm aio", "280mm aio", "240mm aio",
        "heatsink", "thermal paste", "noctua", "deepcool", "thermalright",
        "aio", "240mm", "360mm",
    ],
    "Monitor": [
        "monitor", "gaming monitor", "oled monitor", "ips monitor",
        "1440p monitor", "4k monitor", "1080p monitor",
        "144hz monitor", "165hz monitor", "240hz monitor",
        "ultrawide monitor", "display", "ultrawide", "oled", "ips",
        "qhd", "uhd", "ultragear", "odyssey", "rog swift", "alienware aw",
    ],
}

STRONG_SIGNALS: Dict[str, List[str]] = {
    "GPU":         ["graphics card", "video card", "geforce", "radeon", "rtx", "rx 7", "rx 6", "gpu"],
    "CPU":         ["ryzen", "core i", "processor", "intel cpu", "amd cpu", "x3d"],
    "RAM":         ["ddr4", "ddr5", "ram kit", "desktop memory", "udimm", "dimm"],
    "SSD":         ["nvme", "m.2 ssd", "internal ssd", "solid state drive", "pcie 4.0 ssd", "pcie 5.0 ssd"],
    "Motherboard": ["motherboard", "mobo", "am5", "am4", "lga1700", "b650", "z790", "x670", "b760"],
    "PSU":         ["power supply", "psu", "80+ gold", "fully modular", "atx 3.0", "atx 3.1"],
    "Cooling":     ["cpu cooler", "aio", "air cooler", "liquid cooler", "heatsink", "thermal paste"],
    "Monitor":     ["monitor", "gaming monitor", "oled monitor", "1440p monitor", "4k monitor", "display", "ultrawide"],
}

EXCLUDED_TERMS = [
    "laptop", "notebook", "prebuilt", "gaming pc", "desktop pc",
    "mini pc", "handheld", "steam deck", "rog ally",
    "iphone", "android phone", "smartphone", "tablet", "ipad",
    "tv", "television", "soundbar", "earbuds", "headphones",
    "camera", "printer", "router", "projector", "smartwatch",
    "micro sd", "microsd", "sd card", "usb drive", "flash drive",
    "external ssd", "external hard drive", "portable ssd",
    "chair", "desk", "keyboard", "mouse", "webcam", "microphone",
]

GENERIC_NAV_TITLES: Set[str] = {
    "graphics cards", "video cards", "gpu", "gpus",
    "processors", "cpu", "cpus",
    "memory", "ram", "ddr4", "ddr5",
    "solid state drives", "ssd", "ssds", "nvme",
    "motherboards", "motherboard",
    "power supplies", "psu", "psus",
    "cpu coolers", "cooling", "coolers",
    "monitors", "monitor", "displays",
    "components", "pc parts", "computer parts",
    "deals", "sale", "offers", "specials", "view all",
    "shop", "buy", "see all", "more", "home", "search",
}

PRODUCT_URL_PATTERNS: Dict[str, List[str]] = {
    "Micro Center": ["/product/"],
    "Newegg":       ["/p/N82E", "/p/1HU", "itemNumber="],
    "B&H":          ["/c/product/", "/v/"],
    "PCPartPicker": ["/product/"],
}

RSS_SOURCES: Dict[str, List[str]] = {
    "Slickdeals": [
        "https://slickdeals.net/newsearch.php?mode=frontpage&rss=1",
        "https://slickdeals.net/forums/rss.php?f=9",
    ],
    "DealNews": [
        "https://www.dealnews.com/c142/Electronics/Computers/?rss=1",
        "https://www.dealnews.com/c40/Computers/PC-Components/?rss=1",
    ],
    "OzBargain": [
        "https://www.ozbargain.com.au/tag/computer-component/feed",
        "https://www.ozbargain.com.au/tag/gpu/feed",
        "https://www.ozbargain.com.au/tag/ssd/feed",
    ],
    "HotUKDeals": [
        "https://www.hotukdeals.com/rss/tag/pc",
        "https://www.hotukdeals.com/rss/tag/gpu",
    ],
    "Best Buy": [
        "https://www.bestbuy.com/rss/computers-pc-hardware-graphics-cards/pcmcat1563303358461.rss",
        "https://www.bestbuy.com/rss/computers-pc-hardware-computer-processors/abcat0507000.rss",
        "https://www.bestbuy.com/rss/computers-pc-hardware-solid-state-drives/abcat0507019.rss",
        "https://www.bestbuy.com/rss/computers-pc-hardware-computer-memory/abcat0506009.rss",
    ],
}

HTML_SOURCES: Dict[str, List[str]] = {
    "Micro Center": [
        "https://www.microcenter.com/search/search_results.aspx?Ntt=7800x3d&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+4070&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+4080&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=b650+motherboard&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=ddr5+32gb&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=850w+psu&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=2tb+nvme+ssd&Ntk=all",
    ],
    "Newegg": [
        "https://www.newegg.com/p/pl?d=rtx+4070&N=100007709",
        "https://www.newegg.com/p/pl?d=ryzen+7+7800x3d",
        "https://www.newegg.com/p/pl?d=ddr5+32gb",
        "https://www.newegg.com/p/pl?d=nvme+2tb",
        "https://www.newegg.com/p/pl?d=850w+psu",
        "https://www.newegg.com/p/pl?d=b650+motherboard",
    ],
    "B&H": [
        "https://www.bhphotovideo.com/c/search?Ntt=rtx+4070&N=4288586807",
        "https://www.bhphotovideo.com/c/search?Ntt=nvme+ssd&N=4288586807",
        "https://www.bhphotovideo.com/c/search?Ntt=ddr5+ram&N=4288586807",
    ],
    "PCPartPicker": [
        "https://pcpartpicker.com/products/video-card/#sort=price",
        "https://pcpartpicker.com/products/cpu/#sort=price",
        "https://pcpartpicker.com/products/memory/#sort=price",
        "https://pcpartpicker.com/products/internal-hard-drive/#sort=price",
        "https://pcpartpicker.com/products/power-supply/#sort=price",
    ],
}

SOURCE_ORDER = ["r/buildapcsales"] + list(RSS_SOURCES) + list(HTML_SOURCES)

_SEMAPHORE_LIMIT = 8
_IMPERSONATE = "chrome136"
_TIMEOUT = 20
_MAX_RETRIES = 2
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_RETRY_BACKOFF = 1.5

_source_failures: Dict[str, int] = {}
_MAX_SOURCE_FAILURES = 3

PRICE_RE = re.compile(
    r'(?<!\w)(?:\$|USD\s?)\s?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',
    re.I,
)

OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)

TWITTER_IMAGE_RE = re.compile(
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)

JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)

IMG_SRC_RE = re.compile(
    r'<img[^>]+src=["\']([^"\']+)["\']',
    re.I,
)

_LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)


def _record_failure(source: str) -> None:
    _source_failures[source] = _source_failures.get(source, 0) + 1


def _record_success(source: str) -> None:
    _source_failures[source] = 0


def _is_open(source: str) -> bool:
    return _source_failures.get(source, 0) >= _MAX_SOURCE_FAILURES


def _norm(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\+\.\- ]+", " ", text)
    return re.sub(r"\s+", " ", text)


from html import unescape

def _safe_summary(text: str, limit: int = 300) -> str:
    text = unescape(text or "")
    text = re.sub(r"<img[^>]*>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]

def _contains_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def _title_is_product(title: str) -> bool:
    t = _norm(title)
    if t in GENERIC_NAV_TITLES:
        return False
    if len(t.split()) < 4:
        return False
    if not re.search(r"\d", t):
        return False
    return True


def _is_monitor(t: str) -> bool:
    direct = ["monitor", "display", "ultrawide", "ultragear", "odyssey", "rog swift", "alienware aw"]
    if _contains_any(t, direct):
        return True
    res = ["1080p", "1440p", "4k", "qhd", "uhd"]
    hz = ["120hz", "144hz", "165hz", "180hz", "240hz", "360hz"]
    panel = ["oled", "ips", "va", "mini led"]
    if _contains_any(t, res) and _contains_any(t, hz):
        return True
    if _contains_any(t, panel) and _contains_any(t, hz):
        return True
    return False


def _categorize(title: str) -> str:
    t = _norm(title)
    if _is_monitor(t):
        return "Monitor"
    scores = {cat: sum(1 for kw in kws if kw in t) for cat, kws in KEYWORDS.items()}
    scores = {k: v for k, v in scores.items() if v > 0}
    return max(scores, key=scores.get) if scores else "Other"


def _is_relevant(title: str) -> bool:
    t = _norm(title)
    if _contains_any(t, EXCLUDED_TERMS):
        return False
    if not _title_is_product(title):
        return False
    if _is_monitor(t):
        return True
    matched = [cat for cat, sigs in STRONG_SIGNALS.items() if _contains_any(t, sigs)]
    if not matched:
        return False
    checks = [
        lambda: "psu" in t or "power supply" in t,
        lambda: "motherboard" in t or "mobo" in t,
        lambda: "ssd" in t or "nvme" in t or "solid state" in t or "m.2" in t,
        lambda: "ddr4" in t or "ddr5" in t or "ram kit" in t or "desktop memory" in t,
        lambda: "ryzen" in t or "core i" in t or "processor" in t or "x3d" in t,
        lambda: "graphics card" in t or "video card" in t or "geforce" in t or "radeon" in t,
    ]
    for fn in checks:
        if fn():
            return True
    gpu_models = ["4060", "4070", "4080", "4090", "7600", "7700", "7800", "7900"]
    if _contains_any(t, gpu_models):
        if _contains_any(t, ["rtx", "rx ", "geforce", "radeon", "graphics card", "gpu"]):
            return True
    return False


def _make_id(source: str, title: str, link: str) -> str:
    raw = _norm(f"{source}-{title}-{link}")
    slug = re.sub(r"[^a-z0-9]+", "-", raw)[:96].strip("-")
    return slug or f"{source.lower()}-{abs(hash(link))}"


def _extract_price_text(*parts: Optional[str]) -> Optional[str]:
    for part in parts:
        if not part:
            continue
        text = unescape(part)
        m = PRICE_RE.search(text)
        if m:
            return f"${m.group(1)}"
    return None


def _clean_image_url(url: Optional[str], base_url: str = "") -> Optional[str]:
    if not url:
        return None
    url = unescape(url).strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(base_url, url)
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return None


def _extract_image_from_html(html: str, base_url: str = "") -> Optional[str]:
    if not html:
        return None

    m = OG_IMAGE_RE.search(html)
    if m:
        return _clean_image_url(m.group(1), base_url)

    m = TWITTER_IMAGE_RE.search(html)
    if m:
        return _clean_image_url(m.group(1), base_url)

    for block in JSON_LD_RE.findall(html):
        try:
            data = json.loads(block.strip())
            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                image = item.get("image")
                if isinstance(image, str):
                    return _clean_image_url(image, base_url)
                if isinstance(image, list) and image:
                    first = image[0]
                    if isinstance(first, str):
                        return _clean_image_url(first, base_url)
                offers = item.get("offers")
                if isinstance(offers, dict):
                    img = offers.get("image")
                    if isinstance(img, str):
                        return _clean_image_url(img, base_url)
        except Exception:
            continue

    m = IMG_SRC_RE.search(html)
    if m:
        return _clean_image_url(m.group(1), base_url)

    return None


def _extract_price_from_html(html: str) -> Optional[str]:
    if not html:
        return None

    m = re.search(r'"price"\s*:\s*"?(\\?[\d,]+(?:\.\d{2})?)"?', html, re.I)
    if m:
        return f"${m.group(1).replace(chr(92), '')}"

    m = re.search(r'itemprop=["\']price["\'][^>]*content=["\']([\d,]+(?:\.\d{2})?)["\']', html, re.I)
    if m:
        return f"${m.group(1)}"

    return _extract_price_text(html[:5000])


def _extract_feed_image(entry: Any) -> Optional[str]:
    media_content = entry.get("media_content") or []
    for item in media_content:
        url = item.get("url")
        if url:
            return url

    media_thumbnail = entry.get("media_thumbnail") or []
    for item in media_thumbnail:
        url = item.get("url")
        if url:
            return url

    enclosures = entry.get("enclosures") or []
    for item in enclosures:
        href = item.get("href")
        typ = (item.get("type") or "").lower()
        if href and typ.startswith("image/"):
            return href

    summary = entry.get("summary", "") or ""
    m = IMG_SRC_RE.search(summary)
    if m:
        return _clean_image_url(m.group(1))

    return None


def _make_deal(
    source: str,
    title: str,
    link: str,
    published: str = "",
    summary: str = "",
    price: Optional[str] = None,
    image: Optional[str] = None,
    product_link: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not title or not _is_relevant(title):
        return None
    cat = _categorize(title)
    if cat == "Other":
        return None
    return {
        "id":           _make_id(source, title, link),
        "title":        title.strip(),
        "link":         link.strip(),
        "source":       source,
        "category":     cat,
        "published":    published,
        "summary":      _safe_summary(summary),
        "price":        price,
        "image":        image,
        "product_link": product_link,
    }


def _url_is_product(source: str, href: str) -> bool:
    patterns = PRODUCT_URL_PATTERNS.get(source)
    if patterns:
        return any(p in href for p in patterns)
    return len(href) >= 50


async def _fetch(session: AsyncSession, sem: asyncio.Semaphore,
                 url: str, source: str, timeout: int = _TIMEOUT) -> Optional[str]:
    delay = _RETRY_BACKOFF
    async with sem:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                r = await session.get(url, timeout=timeout)
                if r.status_code == 200:
                    _record_success(source)
                    return r.text
                if r.status_code in _RETRY_STATUSES and attempt < _MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                print(f"[{source}] HTTP {r.status_code} -> {url}")
                _record_failure(source)
                return None
            except asyncio.TimeoutError:
                print(f"[{source}] Timeout -> {url}")
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                _record_failure(source)
                return None
            except Exception as exc:
                print(f"[{source}] Error -> {url} : {exc}")
                _record_failure(source)
                return None
    return None


def _praw_fetch() -> List[Dict[str, Any]]:
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    username = os.getenv("REDDIT_USERNAME", "pcdealsbot")

    if not client_id or not client_secret:
        print("[Reddit] Missing REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET - skipping")
        return []

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=f"pcdealsbot:v3.0 (by /u/{username})",
        )
        results: List[Dict[str, Any]] = []
        for post in reddit.subreddit("buildapcsales").new(limit=75):
            if not _is_relevant(post.title):
                continue
            cat = _categorize(post.title)
            if cat == "Other":
                continue

            published = datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat()
            discussion_link = f"https://www.reddit.com{post.permalink}"
            product_link = getattr(post, "url", None) or discussion_link
            summary = _safe_summary(getattr(post, "selftext", ""))

            results.append({
                "id":           _make_id("r/buildapcsales", post.title, discussion_link),
                "title":        post.title,
                "link":         discussion_link,
                "source":       "r/buildapcsales",
                "category":     cat,
                "published":    published,
                "summary":      summary,
                "price":        _extract_price_text(post.title, summary),
                "image":        None,
                "product_link": product_link,
            })
        print(f"[Reddit/PRAW] {len(results)} relevant posts")
        return results
    except Exception as exc:
        print(f"[Reddit/PRAW] Error: {exc}")
        return []


async def fetch_reddit(loop: asyncio.AbstractEventLoop) -> List[Dict[str, Any]]:
    return await loop.run_in_executor(None, _praw_fetch)


async def fetch_rss_source(session: AsyncSession, sem: asyncio.Semaphore,
                           source: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for url in RSS_SOURCES[source]:
        if _is_open(source):
            print(f"[{source}] Circuit breaker tripped - skipping remaining URLs")
            break

        timeout = 30 if source == "Best Buy" else _TIMEOUT
        text = await _fetch(session, sem, url, source, timeout=timeout)
        if not text:
            continue

        feed = feedparser.parse(text)
        entries = getattr(feed, "entries", [])
        if not entries:
            print(f"[{source}] 0 entries from {url}")
            continue

        for entry in entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            price = _extract_price_text(title, summary)
            image = _extract_feed_image(entry)

            deal = _make_deal(
                source,
                title,
                link,
                entry.get("published", ""),
                summary,
                price=price,
                image=image,
                product_link=link,
            )
            if deal and deal["id"] not in seen:
                seen.add(deal["id"])
                results.append(deal)

    print(f"[{source}] {len(results)} relevant deals")
    return results


async def fetch_html_source(session: AsyncSession, sem: asyncio.Semaphore,
                            source: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for url in HTML_SOURCES[source]:
        if _is_open(source):
            print(f"[{source}] Circuit breaker tripped - skipping remaining URLs")
            break

        text = await _fetch(session, sem, url, source)
        if not text:
            continue

        base_match = re.match(r"(https?://[^/]+)", url)
        base_url = base_match.group(1) if base_match else ""

        for m in _LINK_RE.finditer(text):
            href, raw_title = m.groups()

            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = base_url + href
            if not href.startswith("http"):
                continue
            if not _url_is_product(source, href):
                continue

            title = re.sub(r"<[^>]+>", " ", raw_title)
            title = re.sub(r"\s+", " ", title).strip()

            published = datetime.now(timezone.utc).isoformat()
            deal = _make_deal(
                source,
                title,
                href,
                published=published,
                price=_extract_price_text(title),
                image=None,
                product_link=href,
            )
            if deal and deal["id"] not in seen:
                seen.add(deal["id"])
                results.append(deal)

    count = min(len(results), 30)
    print(f"[{source}] {count} HTML-parsed relevant deals")
    return results[:30]


async def _enrich_deal(session: AsyncSession, sem: asyncio.Semaphore, deal: Dict[str, Any]) -> Dict[str, Any]:
    if deal.get("price") and deal.get("image"):
        return deal

    target = deal.get("product_link") or deal.get("link")
    if not target:
        return deal

    html = await _fetch(session, sem, target, f"{deal['source']}[enrich]", timeout=12)
    if not html:
        return deal

    if not deal.get("price"):
        deal["price"] = _extract_price_from_html(html) or _extract_price_text(
            deal.get("title", ""),
            deal.get("summary", ""),
        )

    if not deal.get("image"):
        deal["image"] = _extract_image_from_html(html, target)

    return deal


_deals_cache: List[Dict[str, Any]] = []
_last_updated: Optional[datetime] = None


async def refresh_deals_cache() -> None:
    global _deals_cache, _last_updated

    _source_failures.clear()
    print("[Scraper] Refreshing all sources...")
    t0 = time.perf_counter()

    loop = asyncio.get_running_loop()

    async with AsyncSession(impersonate=_IMPERSONATE) as session:
        sem = asyncio.Semaphore(_SEMAPHORE_LIMIT)
        tasks = (
            [fetch_reddit(loop)]
            + [fetch_rss_source(session, sem, src) for src in RSS_SOURCES]
            + [fetch_html_source(session, sem, src) for src in HTML_SOURCES]
        )
        batches = await asyncio.gather(*tasks, return_exceptions=True)

    seen: Set[str] = set()
    fresh: List[Dict[str, Any]] = []
    for batch in batches:
        if isinstance(batch, Exception):
            print(f"[Scraper] Task error: {batch}")
            continue
        for deal in batch:
            if deal["id"] not in seen:
                seen.add(deal["id"])
                fresh.append(deal)

    async with AsyncSession(impersonate=_IMPERSONATE) as enrich_session:
        enrich_sem = asyncio.Semaphore(6)
        fresh = await asyncio.gather(
            *[_enrich_deal(enrich_session, enrich_sem, deal) for deal in fresh],
            return_exceptions=False,
        )

    fresh.sort(key=lambda d: d.get("published") or "", reverse=True)
    _deals_cache = fresh
    _last_updated = datetime.now(timezone.utc)
    print(f"[Scraper] Done - {len(fresh)} deals cached in {time.perf_counter() - t0:.1f}s")


def get_cached_deals(
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    deals = list(_deals_cache)
    if category and category.lower() != "all":
        deals = [d for d in deals if d["category"].lower() == category.lower()]
    if search:
        s = search.lower()
        deals = [d for d in deals if s in d["title"].lower() or s in d.get("summary", "").lower()]
    return {
        "deals":        deals,
        "total":        len(deals),
        "last_updated": _last_updated.isoformat() if _last_updated else None,
        "categories":   list(KEYWORDS.keys()),
        "sources":      SOURCE_ORDER,
    }


if __name__ == "__main__":
    async def _main() -> None:
        await refresh_deals_cache()
        data = get_cached_deals()
        print(f"\n{'-' * 70}")
        print(f"Total cached: {data['total']}")
        print(f"{'-' * 70}")
        for deal in data["deals"][:25]:
            print(f"[{deal['category']:12s}] [{deal['source']:20s}] {deal['title']} | {deal.get('price') or 'N/A'}")

    asyncio.run(_main())