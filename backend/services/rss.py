from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import feedparser
from curl_cffi.requests import AsyncSession

# ---------------------------------------------------------------------------
# Sources — refreshed links + safer source-specific parsing
#
# Goals:
# - Keep the same output structure for your frontend cards
# - Improve price/image fill rate
# - Replace dead/stale URLs with better working alternatives
# - Avoid enriching search result pages when possible
# ---------------------------------------------------------------------------

REDDIT_RSS_URL = "https://www.reddit.com/r/buildapcsales/.rss"

RSS_SOURCES: Dict[str, List[str]] = {
    # Slickdeals: frontpage + targeted search RSS
    "Slickdeals": [
        "https://slickdeals.net/newsearch.php?mode=frontpage&rss=1",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=graphics+card",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=processor+cpu",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=nvme+ssd",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=ddr5+ram",
    ],
    # DealNews: broader live feeds; filtering happens in code
    "DealNews": [
        "https://www.dealnews.com/rss/headlines.xml",
        "https://www.dealnews.com/rss/editors-choice.xml",
    ],
    "OzBargain": [
        "https://www.ozbargain.com.au/tag/computer-component/feed",
        "https://www.ozbargain.com.au/tag/gpu/feed",
        "https://www.ozbargain.com.au/tag/ssd/feed",
        "https://www.ozbargain.com.au/tag/cpu/feed",
    ],
    # remove broken computer-components feed
    "HotUKDeals": [
        "https://www.hotukdeals.com/rss/tag/pc",
        "https://www.hotukdeals.com/rss/tag/computers",
    ],
    # corrected feed path
    "BensBargains": [
        "https://bensbargains.com/rss.xml",
    ],
    "RedFlagDeals": [
        "https://forums.redflagdeals.com/hot-deals-f9/?rss=1",
    ],
}

HTML_SOURCES: Dict[str, List[str]] = {
    "Newegg": [
        "https://www.newegg.com/p/pl?d=rtx+5070",
        "https://www.newegg.com/p/pl?d=rtx+4070&N=100007709",
        "https://www.newegg.com/p/pl?d=ryzen+9700x",
        "https://www.newegg.com/p/pl?d=ddr5+32gb",
        "https://www.newegg.com/p/pl?d=nvme+2tb",
        "https://www.newegg.com/p/pl?d=850w+psu",
        "https://www.newegg.com/p/pl?d=b650+motherboard",
    ],
    "Micro Center": [
        "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+5070&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+4080&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=ryzen+7800x3d&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=b650+motherboard&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=ddr5+32gb&Ntk=all",
        "https://www.microcenter.com/search/search_results.aspx?Ntt=nvme+ssd+2tb&Ntk=all",
    ],
    "Amazon": [
        "https://www.amazon.com/s?k=rtx+4070+graphics+card&rh=n%3A284822",
        "https://www.amazon.com/s?k=rtx+5070+graphics+card&rh=n%3A284822",
        "https://www.amazon.com/s?k=ryzen+9700x+processor&rh=n%3A229189",
        "https://www.amazon.com/s?k=ddr5+32gb+ram&rh=n%3A172282",
        "https://www.amazon.com/s?k=nvme+ssd+2tb&rh=n%3A1292110011",
        "https://www.amazon.com/s?k=850w+psu+power+supply&rh=n%3A1161760",
        "https://www.amazon.com/s?k=b650+motherboard&rh=n%3A1048424",
    ],
    "Best Buy": [
        "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+4070+graphics+card",
        "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+5070+graphics+card",
        "https://www.bestbuy.com/site/searchpage.jsp?st=ryzen+9700x+processor",
        "https://www.bestbuy.com/site/searchpage.jsp?st=ddr5+ram+32gb",
        "https://www.bestbuy.com/site/searchpage.jsp?st=nvme+ssd+2tb",
        "https://www.bestbuy.com/site/searchpage.jsp?st=850w+power+supply",
        "https://www.bestbuy.com/site/searchpage.jsp?st=b650+motherboard",
    ],
    # refreshed B&H category pages
    "B&H": [
        "https://www.bhphotovideo.com/c/buy/graphic-cards/ci/55619",
        "https://www.bhphotovideo.com/c/buy/cpu-processors/ci/37889",
        "https://www.bhphotovideo.com/c/buy/internal-ssds/ci/30903",
        "https://www.bhphotovideo.com/c/buy/Computer-Memory/ci/13341",
        "https://www.bhphotovideo.com/c/buy/motherboards/ci/19864",
        "https://www.bhphotovideo.com/c/browse/desktop-components/ci/30908",
    ],
    "Antonline": [
        "https://www.antonline.com/NVIDIA",
        "https://www.antonline.com/AMD",
        "https://www.antonline.com/ASUS/Electronics/Video_Cards_Video_Devices/Video_Cards",
        "https://www.antonline.com/Computers/Components",
    ],
}

SOURCE_ORDER = ["r/buildapcsales"] + list(RSS_SOURCES) + list(HTML_SOURCES)

# ---------------------------------------------------------------------------
# Keywords — exact product model names first, generics as fallback
# ---------------------------------------------------------------------------

KEYWORDS: Dict[str, List[str]] = {
    "GPU": [
        "rtx 5090", "rtx 5080", "rtx 5070 ti", "rtx 5070", "rtx 5060 ti", "rtx 5060",
        "rtx 4090", "rtx 4080 super", "rtx 4080", "rtx 4070 ti super",
        "rtx 4070 ti", "rtx 4070 super", "rtx 4070", "rtx 4060 ti", "rtx 4060",
        "rx 9070 xt", "rx 9070", "rx 9060 xt",
        "rx 7900 xtx", "rx 7900 xt", "rx 7900 gre",
        "rx 7800 xt", "rx 7700 xt", "rx 7600 xt", "rx 7600",
        "geforce rtx", "radeon rx", "graphics card", "video card", "gpu",
    ],
    "CPU": [
        "ryzen 9 9950x", "ryzen 9 9900x", "ryzen 7 9800x3d", "ryzen 7 9700x",
        "ryzen 5 9600x", "ryzen 5 9600",
        "ryzen 9 7950x3d", "ryzen 9 7900x3d", "ryzen 9 7900x",
        "ryzen 7 7800x3d", "ryzen 7 7700x", "ryzen 5 7600x", "ryzen 5 7600",
        "core ultra 9 285k", "core ultra 7 265k", "core ultra 7 265kf",
        "core ultra 5 245k", "core ultra 5 245kf",
        "core i9-14900k", "core i9-14900kf", "core i7-14700k", "core i5-14600k",
        "core i9-13900k", "core i7-13700k", "core i5-13600k",
        "ryzen", "core ultra", "core i9", "core i7", "core i5", "processor",
    ],
    "RAM": [
        "g.skill trident z5", "g.skill ripjaws s5", "g.skill flare x5",
        "corsair vengeance ddr5", "corsair dominator platinum ddr5",
        "kingston fury beast ddr5", "kingston fury renegade ddr5",
        "crucial pro ddr5", "teamgroup t-force vulcan ddr5",
        "corsair vengeance lpx", "g.skill ripjaws v", "kingston fury beast ddr4",
        "32gb ddr5-6000", "32gb ddr5-6400", "32gb ddr5-7200",
        "64gb ddr5", "16gb ddr5", "32gb ddr4-3600",
        "ddr4", "ddr5", "ram kit", "desktop memory",
    ],
    "SSD": [
        "samsung 9100 pro", "crucial t705", "kingston fury renegade pcie 5",
        "seagate firecuda 540", "corsair mp700 pro",
        "samsung 990 pro", "samsung 980 pro", "wd black sn850x",
        "seagate firecuda 530", "sabrent rocket 4 plus",
        "crucial p3 plus", "crucial p5 plus", "sk hynix platinum p41",
        "2tb nvme", "1tb nvme", "4tb nvme", "2tb m.2", "4tb m.2",
        "nvme ssd", "m.2 ssd", "pcie 4.0 ssd", "pcie 5.0 ssd", "internal ssd",
    ],
    "Motherboard": [
        "asus rog crosshair x870e", "asus rog strix x870-f", "asus tuf gaming x870-plus",
        "asus prime x870-p", "asus prime b650m",
        "msi meg x870e ace", "msi mpg x870e carbon", "msi mag x870 tomahawk",
        "gigabyte aorus x870e", "asrock x870e taichi",
        "asus rog strix z790-f", "msi meg z790 ace", "gigabyte z790 aorus master",
        "asus prime b760m", "msi pro b760m",
        "b650", "x670", "x870", "z790", "z890", "b760", "motherboard", "mobo",
    ],
    "PSU": [
        "corsair rm850e", "corsair rm1000e", "corsair hx1000i",
        "seasonic focus gx-850", "seasonic prime tx-1000", "seasonic vertex gx-850",
        "be quiet! straight power 12", "be quiet! dark power pro 13",
        "lian li sp850", "msi meg ai1300p", "thermaltake toughpower gf3 850",
        "850w 80+ gold", "1000w 80+ platinum", "750w fully modular", "850w atx 3.0",
        "power supply", "psu", "80+ gold", "80+ platinum", "fully modular",
    ],
    "Cooling": [
        "noctua nh-d15", "noctua nh-d15s", "noctua nh-u12a",
        "deepcool ak620", "deepcool ak500", "deepcool assassin iv",
        "thermalright peerless assassin 120 se", "thermalright phantom spirit 120",
        "be quiet! dark rock pro 4", "arctic freezer 36",
        "nzxt kraken 360", "nzxt kraken 280", "nzxt kraken 240",
        "corsair icue h150i elite", "corsair icue h100i elite",
        "deepcool lt720", "deepcool lt520",
        "arctic liquid freezer iii 360", "arctic liquid freezer iii 240",
        "lian li galahad ii 360",
        "cpu cooler", "aio cooler", "liquid cooler", "air cooler",
        "360mm aio", "240mm aio", "280mm aio",
    ],
    "Monitor": [
        "lg 27gr95qe", "lg 27gp950", "lg 27gp850", "lg 32gr93u", "lg 45gr95qe",
        "lg ultragear oled",
        "samsung odyssey neo g9", "samsung odyssey g9", "samsung odyssey g7",
        "samsung odyssey oled g8", "samsung odyssey oled g6",
        "asus rog swift pg32ucdp", "asus rog swift pg27aqdm", "asus rog swift oled",
        "alienware aw3423dwf", "alienware aw2725df", "alienware aw3225qf",
        "dell s2722dgm", "dell s3222dgm",
        "acer predator x27u", "msi mag 274qrf",
        "1440p 144hz", "1440p 165hz", "4k 144hz", "oled 144hz",
        "gaming monitor", "ultrawide monitor", "monitor",
    ],
}

STRONG_SIGNALS: Dict[str, List[str]] = {
    "GPU":         ["rtx", "rx 9", "rx 7", "geforce", "radeon", "graphics card", "video card", "gpu"],
    "CPU":         ["ryzen", "core ultra", "core i9", "core i7", "core i5", "processor"],
    "RAM":         ["ddr4", "ddr5", "ram kit", "desktop memory"],
    "SSD":         ["nvme", "m.2 ssd", "internal ssd", "pcie 4.0 ssd", "pcie 5.0 ssd"],
    "Motherboard": ["motherboard", "mobo", "b650", "x670", "x870", "z790", "z890", "b760"],
    "PSU":         ["power supply", "psu", "80+ gold", "80+ platinum", "fully modular", "atx 3.0", "atx 3.1"],
    "Cooling":     ["cpu cooler", "aio", "air cooler", "liquid cooler", "heatsink"],
    "Monitor":     ["monitor", "oled monitor", "gaming monitor", "ultrawide", "display"],
}

EXCLUDED_TERMS = [
    "laptop", "notebook", "prebuilt", "gaming pc", "desktop pc",
    "mini pc", "handheld", "steam deck", "rog ally",
    "smartphone", "tablet", "ipad", "iphone", "android",
    "tv", "television", "soundbar", "earbuds", "headphones",
    "camera", "printer", "router", "projector", "smartwatch",
    "micro sd", "sd card", "usb drive", "flash drive",
    "external ssd", "external hard drive", "portable ssd",
    "chair", "desk", "keyboard", "mouse", "webcam", "microphone",
]

GENERIC_NAV_TITLES: Set[str] = {
    "graphics cards", "video cards", "gpu", "gpus",
    "processors", "cpu", "cpus", "memory", "ram", "ddr4", "ddr5",
    "solid state drives", "ssd", "ssds", "nvme", "motherboards",
    "power supplies", "psu", "cpu coolers", "cooling", "coolers",
    "monitors", "displays", "components", "pc parts", "deals", "sale",
    "shop", "buy", "see all", "more", "home",
}

PRODUCT_URL_PATTERNS: Dict[str, List[str]] = {
    "Micro Center": ["/product/"],
    "Newegg":       ["/p/N82E", "itemNumber="],
    "Best Buy":     ["/site/", "/p/"],
    "B&H":          ["/c/product/", "/v/", "/p/"],
    "Amazon":       ["/dp/", "/gp/product/"],
    "Antonline":    ["/Electronics/", "/Computers/"],
}

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

PRICE_RE        = re.compile(r'(?<!\w)(?:\$|USD\s?)\s?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)', re.I)
OG_IMAGE_RE     = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I)
IMG_SRC_RE      = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
LINK_RE         = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)

AMAZON_HIRES_RE = re.compile(r'"hiRes"\s*:\s*"(https://[^"]+)"', re.I)
AMAZON_SIMG_RE  = re.compile(r'class="s-image"[^>]+src="([^"]+)"', re.I)
AMAZON_PRICE_RE = re.compile(r'"priceAmount"\s*:\s*([\d.]+)', re.I)
AMAZON_WHOLE_RE = re.compile(r'<span class="a-price-whole">([^<]+)</span>', re.I)
AMAZON_FRAC_RE  = re.compile(r'<span class="a-price-fraction">([^<]+)</span>', re.I)

BBY_PRICE_RE    = re.compile(r'"currentPrice"\s*:\s*([\d.]+)', re.I)

BH_DATA_PRICE_RE = re.compile(r'"price"\s*:\s*"?([\d,]+(?:\.\d{2})?)"?', re.I)
BH_SCRIPT_PRICE_RE = re.compile(r'\$([0-9,]+)(?:\.(\d{2}))?')
BH_IMAGE_RE = re.compile(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', re.I)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\+\.\- ]+", " ", text)
    return re.sub(r"\s+", " ", text)


def _safe_summary(text: str, limit: int = 300) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _contains_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def _title_is_product(title: str) -> bool:
    t = _norm(title)
    return t not in GENERIC_NAV_TITLES and len(t.split()) >= 4


def _categorize(title: str) -> str:
    t = _norm(title)
    scores = {cat: sum(1 for kw in kws if kw in t) for cat, kws in KEYWORDS.items()}
    scores = {k: v for k, v in scores.items() if v > 0}
    return max(scores, key=scores.get) if scores else "Other"


def _is_relevant(title: str) -> bool:
    t = _norm(title)
    if _contains_any(t, EXCLUDED_TERMS):
        return False
    if not _title_is_product(title):
        return False
    return any(_contains_any(t, sigs) for sigs in STRONG_SIGNALS.values())


def _make_id(source: str, link: str) -> str:
    raw = _norm(f"{source}-{link}")
    slug = re.sub(r"[^a-z0-9]+", "-", raw)[:96].strip("-")
    return slug or f"{source.lower()}-{abs(hash(link))}"


def _extract_price(*parts: Optional[str]) -> Optional[str]:
    for part in parts:
        if not part:
            continue
        m = PRICE_RE.search(unescape(part))
        if m:
            return f"${m.group(1)}"
    return None


def _clean_url(url: Optional[str], base: str = "") -> Optional[str]:
    if not url:
        return None
    url = unescape(url).strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(base, url)
    return url if url.startswith("http") else None


def _image_from_entry(entry: Any) -> Optional[str]:
    for key in ("media_content", "media_thumbnail"):
        for item in (entry.get(key) or []):
            if item.get("url"):
                return item["url"]
    for item in (entry.get("enclosures") or []):
        if item.get("href") and (item.get("type") or "").startswith("image/"):
            return item["href"]
    m = IMG_SRC_RE.search(entry.get("summary", "") or "")
    return _clean_url(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Source-specific price / image extraction
# ---------------------------------------------------------------------------

def _amazon_price(chunk: str) -> Optional[str]:
    m = AMAZON_PRICE_RE.search(chunk)
    if m:
        return f"${float(m.group(1)):.2f}"
    whole = AMAZON_WHOLE_RE.search(chunk)
    if whole:
        frac = AMAZON_FRAC_RE.search(chunk)
        return f"${whole.group(1).strip().rstrip('.')}.{frac.group(1).strip() if frac else '00'}"
    return _extract_price(chunk[:3000])


def _amazon_image(chunk: str) -> Optional[str]:
    m = AMAZON_HIRES_RE.search(chunk)
    if m:
        return m.group(1)
    m = AMAZON_SIMG_RE.search(chunk)
    return _clean_url(m.group(1)) if m else None


def _bestbuy_price(chunk: str) -> Optional[str]:
    m = BBY_PRICE_RE.search(chunk)
    return f"${float(m.group(1)):.2f}" if m else _extract_price(chunk[:3000])


def _bh_price(chunk: str) -> Optional[str]:
    m = BH_DATA_PRICE_RE.search(chunk)
    if m:
        return f"${m.group(1)}"
    m = BH_SCRIPT_PRICE_RE.search(chunk)
    if m:
        frac = m.group(2) or "00"
        return f"${m.group(1)}.{frac}" if "." not in m.group(1) else f"${m.group(1)}"
    return _extract_price(chunk[:3000])


def _bh_image(chunk: str, base: str = "") -> Optional[str]:
    m = BH_IMAGE_RE.search(chunk)
    if m:
        return _clean_url(m.group(1), base)
    return _og_image(chunk, base)


def _og_image(html: str, base: str = "") -> Optional[str]:
    m = OG_IMAGE_RE.search(html)
    if m:
        return _clean_url(m.group(1), base)
    m = IMG_SRC_RE.search(html)
    return _clean_url(m.group(1), base) if m else None


def _make_deal(
    source: str, title: str, link: str,
    published: str = "", summary: str = "",
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
        "id":           _make_id(source, link),
        "title":        title.strip(),
        "link":         link.strip(),
        "source":       source,
        "category":     cat,
        "published":    published,
        "summary":      _safe_summary(summary),
        "price":        price,
        "image":        image,
        "product_link": product_link or link,
    }


# ---------------------------------------------------------------------------
# HTTP fetch — with source-specific headers
# ---------------------------------------------------------------------------

_SEMAPHORE   = 8
_IMPERSONATE = "chrome136"
_TIMEOUT     = 20
_RETRIES     = 2
_RETRY_CODES = {429, 500, 502, 503, 504}

_EXTRA_HEADERS: Dict[str, Dict[str, str]] = {
    "r/buildapcsales": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    },
    "Amazon": {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    },
    "Best Buy": {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    },
    "B&H": {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
}


async def _fetch(
    session: AsyncSession, sem: asyncio.Semaphore,
    url: str, source: str, timeout: int = _TIMEOUT,
) -> Optional[str]:
    headers = _EXTRA_HEADERS.get(source, {})
    async with sem:
        for attempt in range(_RETRIES + 1):
            try:
                r = await session.get(url, timeout=timeout, headers=headers)
                if r.status_code == 200:
                    return r.text
                if r.status_code in _RETRY_CODES and attempt < _RETRIES:
                    await asyncio.sleep(1.5 ** (attempt + 1))
                    continue
                print(f"[{source}] HTTP {r.status_code} {url}")
                return None
            except asyncio.TimeoutError:
                if attempt < _RETRIES:
                    await asyncio.sleep(1.5 ** (attempt + 1))
                    continue
                print(f"[{source}] Timeout {url}")
                return None
            except Exception as exc:
                print(f"[{source}] {exc}")
                return None
    return None


# ---------------------------------------------------------------------------
# Reddit — optional best effort
# ---------------------------------------------------------------------------

async def fetch_reddit(session: AsyncSession, sem: asyncio.Semaphore) -> List[Dict[str, Any]]:
    text = await _fetch(session, sem, REDDIT_RSS_URL, "r/buildapcsales", timeout=15)
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    for entry in feedparser.parse(text).entries:
        title   = entry.get("title", "")
        link    = entry.get("link", "")
        summary = entry.get("summary", "") or ""

        if not _is_relevant(title):
            continue
        cat = _categorize(title)
        if cat == "Other":
            continue

        product_link = link
        for m in LINK_RE.finditer(summary):
            href, anchor = m.groups()
            if "reddit.com" not in href and anchor.strip().lower() not in ("comments", "[link]", "[comments]"):
                product_link = href
                break

        results.append({
            "id":           _make_id("r/buildapcsales", link),
            "title":        title,
            "link":         link,
            "source":       "r/buildapcsales",
            "category":     cat,
            "published":    entry.get("published", ""),
            "summary":      _safe_summary(summary),
            "price":        _extract_price(title, summary),
            "image":        _image_from_entry(entry),
            "product_link": product_link,
        })

    print(f"[r/buildapcsales] {len(results)} relevant posts")
    return results


# ---------------------------------------------------------------------------
# RSS sources
# ---------------------------------------------------------------------------

async def fetch_rss(session: AsyncSession, sem: asyncio.Semaphore, source: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for url in RSS_SOURCES[source]:
        text = await _fetch(session, sem, url, source)
        if not text:
            continue
        for entry in feedparser.parse(text).entries:
            title   = entry.get("title", "")
            link    = entry.get("link", "")
            summary = entry.get("summary", "")
            deal = _make_deal(
                source, title, link, entry.get("published", ""), summary,
                price=_extract_price(title, summary),
                image=_image_from_entry(entry),
            )
            if deal and deal["id"] not in seen:
                seen.add(deal["id"])
                results.append(deal)

    print(f"[{source}] {len(results)} deals")
    return results


# ---------------------------------------------------------------------------
# HTML sources
# ---------------------------------------------------------------------------

async def fetch_html(session: AsyncSession, sem: asyncio.Semaphore, source: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    patterns = PRODUCT_URL_PATTERNS.get(source, [])

    for url in HTML_SOURCES[source]:
        text = await _fetch(session, sem, url, source)
        if not text:
            continue

        base_m = re.match(r"(https?://[^/]+)", url)
        base_url = base_m.group(1) if base_m else ""

        # ── Amazon: price + image from search result chunks ──────────────────
        if source == "Amazon":
            for m in LINK_RE.finditer(text):
                href, raw = m.groups()
                if not any(p in href for p in ["/dp/", "/gp/product/"]):
                    continue
                if href.startswith("/"):
                    href = base_url + href

                title = re.sub(r"<[^>]+>", " ", raw)
                title = re.sub(r"\s+", " ", title).strip()
                if not _is_relevant(title):
                    continue

                pos = m.start()
                chunk = text[max(0, pos - 600):pos + 2000]
                deal = _make_deal(
                    source, title, href,
                    published=datetime.now(timezone.utc).isoformat(),
                    price=_amazon_price(chunk),
                    image=_amazon_image(chunk),
                    product_link=href,
                )
                if deal and deal["id"] not in seen:
                    seen.add(deal["id"])
                    results.append(deal)
            print(f"[{source}] {min(len(results), 30)} deals")
            return results[:30]

        # ── Best Buy: only keep actual product pages ─────────────────────────
        if source == "Best Buy":
            for m in LINK_RE.finditer(text):
                href, raw = m.groups()

                if href.startswith("/"):
                    href = base_url + href
                if not href.startswith("http"):
                    continue

                if "/site/" not in href or "searchpage.jsp" in href:
                    continue

                title = re.sub(r"<[^>]+>", " ", raw)
                title = re.sub(r"\s+", " ", title).strip()
                if not _is_relevant(title):
                    continue

                pos = m.start()
                chunk = text[max(0, pos - 500):pos + 1800]
                img_m = IMG_SRC_RE.search(chunk)

                deal = _make_deal(
                    source, title, href,
                    published=datetime.now(timezone.utc).isoformat(),
                    price=_bestbuy_price(chunk),
                    image=_clean_url(img_m.group(1), base_url) if img_m else None,
                    product_link=href,
                )
                if deal and deal["id"] not in seen:
                    seen.add(deal["id"])
                    results.append(deal)

            print(f"[{source}] {min(len(results), 30)} deals")
            return results[:30]

        # ── B&H: parse category pages directly ───────────────────────────────
        if source == "B&H":
            for m in LINK_RE.finditer(text):
                href, raw = m.groups()

                title = re.sub(r"<[^>]+>", " ", raw)
                title = re.sub(r"\s+", " ", title).strip()
                if not _is_relevant(title):
                    continue

                if href.startswith("/"):
                    href = base_url + href
                if not href.startswith("http"):
                    continue

                pos = m.start()
                chunk = text[max(0, pos - 1200):pos + 2600]

                deal = _make_deal(
                    source, title, href,
                    published=datetime.now(timezone.utc).isoformat(),
                    price=_bh_price(chunk),
                    image=_bh_image(chunk, base_url),
                    product_link=href,
                )
                if deal and deal["id"] not in seen:
                    seen.add(deal["id"])
                    results.append(deal)

            print(f"[{source}] {min(len(results), 30)} deals")
            return results[:30]

        # ── Generic HTML ─────────────────────────────────────────────────────
        for m in LINK_RE.finditer(text):
            href, raw = m.groups()
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = base_url + href
            if not href.startswith("http"):
                continue
            if patterns and not any(p in href for p in patterns):
                continue

            title = re.sub(r"<[^>]+>", " ", raw)
            title = re.sub(r"\s+", " ", title).strip()

            pos = m.start()
            chunk = text[max(0, pos - 500):pos + 1600]

            deal = _make_deal(
                source, title, href,
                published=datetime.now(timezone.utc).isoformat(),
                price=_extract_price(title, chunk),
                image=_og_image(chunk, base_url),
                product_link=href,
            )
            if deal and deal["id"] not in seen:
                seen.add(deal["id"])
                results.append(deal)

    print(f"[{source}] {min(len(results), 30)} deals")
    return results[:30]


# ---------------------------------------------------------------------------
# Enrichment — fetch product page to fill missing price / image
# ---------------------------------------------------------------------------

async def _enrich(session: AsyncSession, sem: asyncio.Semaphore, deal: Dict[str, Any]) -> Dict[str, Any]:
    if deal.get("price") and deal.get("image"):
        return deal

    target = deal.get("product_link") or deal.get("link")
    if not target:
        return deal

    # never enrich search result pages
    if "searchpage.jsp" in target or "/p/pl?d=" in target:
        return deal

    html = await _fetch(session, sem, target, f"{deal['source']}[enrich]", timeout=12)
    if not html:
        return deal

    source = deal.get("source", "")

    if not deal.get("price"):
        if source == "Amazon":
            deal["price"] = _amazon_price(html)
        elif source == "Best Buy":
            deal["price"] = _bestbuy_price(html)
        elif source == "B&H":
            deal["price"] = _bh_price(html)
        else:
            m = re.search(r'"price"\s*:\s*"?([\d,]+(?:\.\d{2})?)"?', html, re.I)
            deal["price"] = f"${m.group(1)}" if m else _extract_price(html[:3000])

    if not deal.get("image"):
        if source == "Amazon":
            deal["image"] = _amazon_image(html)
        elif source == "B&H":
            deal["image"] = _bh_image(html, target)
        else:
            deal["image"] = _og_image(html, target)

    return deal


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_deals_cache: List[Dict[str, Any]] = []
_last_updated: Optional[datetime] = None
_source_status_cache: Dict[str, Dict[str, Any]] = {}


async def refresh_deals_cache() -> None:
    global _deals_cache, _last_updated, _source_status_cache

    print("[Scraper] Refreshing all sources...")
    t0 = time.perf_counter()

    async with AsyncSession(impersonate=_IMPERSONATE) as session:
        sem = asyncio.Semaphore(_SEMAPHORE)
        tasks = (
            [fetch_reddit(session, sem)]
            + [fetch_rss(session, sem, src) for src in RSS_SOURCES]
            + [fetch_html(session, sem, src) for src in HTML_SOURCES]
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

    async with AsyncSession(impersonate=_IMPERSONATE) as session:
        enrich_sem = asyncio.Semaphore(6)
        fresh = list(await asyncio.gather(
            *[_enrich(session, enrich_sem, d) for d in fresh]
        ))

    # Keep only real deals that have a visible price.
    fresh = [d for d in fresh if d.get("price")]

    fresh.sort(key=lambda d: d.get("published") or "", reverse=True)
    _deals_cache = fresh
    _last_updated = datetime.now(timezone.utc)

    # Build per-source dashboard status from actual cached deals.
    source_counts = {name: 0 for name in SOURCE_ORDER}
    for deal in fresh:
        source = deal.get("source")
        if source in source_counts:
            source_counts[source] += 1

    _source_status_cache = {
        name: {
            "name": name,
            "deal_count": source_counts[name],
            "status": "LIVE" if source_counts[name] > 0 else "INACTIVE",
            "uptime": "ACTIVE" if source_counts[name] > 0 else "INACTIVE",
        }
        for name in SOURCE_ORDER
    }

    print(f"[Scraper] Done — {len(fresh)} deals in {time.perf_counter() - t0:.1f}s")

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
        "deals": deals,
        "total": len(deals),
        "last_updated": _last_updated.isoformat() if _last_updated else None,
        "categories": list(KEYWORDS.keys()),
        "sources": SOURCE_ORDER,
        "source_statuses": [_source_status_cache.get(name, {
            "name": name,
            "deal_count": 0,
            "status": "INACTIVE",
            "uptime": "INACTIVE",
        }) for name in SOURCE_ORDER],
    }


if __name__ == "__main__":
    async def _main() -> None:
        await refresh_deals_cache()
        data = get_cached_deals()
        print(f"\n{'─' * 75}")
        print(f"Total: {data['total']}")
        print(f"{'─' * 75}")
        for deal in data["deals"][:25]:
            price = deal.get("price") or "N/A"
            img   = "img✓" if deal.get("image") else "img✗"
            print(
                f"[{deal['category']:12s}] [{deal['source']:20s}] "
                f"{deal['title'][:50]:<50} | {price:<10} | {img}"
            )

    asyncio.run(_main())