from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import feedparser
from curl_cffi.requests import AsyncSession

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

RSS_SOURCES: Dict[str, List[str]] = {
    "Slickdeals": [
        "https://slickdeals.net/newsearch.php?mode=frontpage&rss=1",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=graphics+card",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=processor+cpu",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=nvme+ssd",
        "https://slickdeals.net/newsearch.php?mode=search&rss=1&q=ddr5+ram",
    ],
    "DealNews": [
        "https://www.dealnews.com/?rss=1&sort=time",
        "https://www.dealnews.com/f1682/Staff-Pick/?rss=1",
    ],
    "HardForum": [
        "https://hardforum.com/forums/h-ot-deals.28/index.rss",
        "https://hardforum.com/forums/h-ot-deals-discussions.118/index.rss",
    ],
    "OzBargain": [
        "https://www.ozbargain.com.au/tag/computer-component/feed",
        "https://www.ozbargain.com.au/tag/gpu/feed",
        "https://www.ozbargain.com.au/tag/ssd/feed",
        "https://www.ozbargain.com.au/tag/cpu/feed",
    ],
    "HotUKDeals": [
        "https://www.hotukdeals.com/rss/tag/pc",
        "https://www.hotukdeals.com/rss/tag/computers",
    ],
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
    "TomsHardware": [
        "https://www.tomshardware.com/deals",
        "https://www.tomshardware.com/deals/page/2",
    ],
}

DEALNEWS_HTML_URLS = [
    "https://www.dealnews.com/c39/Computers/",
    "https://www.dealnews.com/f1682/Staff-Pick/",
]

SOURCE_ORDER = list(RSS_SOURCES) + list(HTML_SOURCES)

# ---------------------------------------------------------------------------
# Keywords
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
    "GPU": ["rtx", "rx 9", "rx 7", "geforce", "radeon", "graphics card", "video card", "gpu"],
    "CPU": ["ryzen", "core ultra", "core i9", "core i7", "core i5", "processor"],
    "RAM": ["ddr4", "ddr5", "ram kit", "desktop memory"],
    "SSD": ["nvme", "m.2 ssd", "internal ssd", "pcie 4.0 ssd", "pcie 5.0 ssd"],
    "Motherboard": ["motherboard", "mobo", "b650", "x670", "x870", "z790", "z890", "b760"],
    "PSU": ["power supply", "psu", "80+ gold", "80+ platinum", "fully modular", "atx 3.0", "atx 3.1"],
    "Cooling": ["cpu cooler", "aio", "air cooler", "liquid cooler", "heatsink"],
    "Monitor": ["monitor", "oled monitor", "gaming monitor", "ultrawide", "display"],
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

NON_PC_TERMS = [
    "magnesium", "vitamin", "supplement", "capsules", "softgels", "probiotic",
    "protein powder", "creatine", "collagen", "omega 3", "fish oil",
    "shampoo", "conditioner", "lotion", "soap", "deodorant",
    "diapers", "wipes", "baby formula",
    "dog food", "cat food", "pet", "litter",
    "snack", "coffee", "tea", "cereal", "chocolate",
    "detergent", "cleaner", "paper towels", "toilet paper",
    "mattress", "shoes", "jacket", "shirt", "pants",
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
    "Newegg": ["/p/N82E", "itemNumber="],
    "Best Buy": ["/site/", "/p/"],
    "B&H": ["/c/product/", "/v/", "/p/"],
    "Amazon": ["/dp/", "/gp/product/"],
    "Antonline": ["/Electronics/", "/Computers/"],
}

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

PRICE_RE = re.compile(r'(?<!\w)(?:\$|USD\s?)\s?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)', re.I)
OG_IMAGE_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I)
IMG_SRC_RE = re.compile(r'<img[^>]+(?:src|data-src|data-image)=["\']([^"\']+)["\']', re.I)
LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_JSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)

AMAZON_PRODUCT_BLOCK_RE = re.compile(
    r'<div[^>]+(?:data-component-type=["\']s-search-result["\']|data-asin=["\'][A-Z0-9]{10}["\'])[^>]*>.*?</div>',
    re.I | re.S,
)
AMAZON_ASIN_RE = re.compile(r'data-asin=["\']([A-Z0-9]{10})["\']', re.I)
AMAZON_TITLE_RE = re.compile(
    r'<a[^>]+class=["\'][^"\']*a-link-normal[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.I | re.S,
)
AMAZON_HIRES_RE = re.compile(r'"hiRes"\s*:\s*"(https://[^"]+)"', re.I)
AMAZON_SIMG_RE = re.compile(r'class=["\'][^"\']*s-image[^"\']*["\'][^>]+src=["\']([^"\']+)["\']', re.I)
AMAZON_PRICE_RE = re.compile(r'"priceAmount"\s*:\s*([\d.]+)', re.I)
AMAZON_WHOLE_RE = re.compile(r'<span[^>]+class=["\'][^"\']*a-price-whole[^"\']*["\'][^>]*>([^<]+)</span>', re.I)
AMAZON_FRAC_RE = re.compile(r'<span[^>]+class=["\'][^"\']*a-price-fraction[^"\']*["\'][^>]*>([^<]+)</span>', re.I)

BESTBUY_TILE_RE = re.compile(
    r'<li[^>]+class=["\'][^"\']*(?:sku-item|list-item)[^"\']*["\'][^>]*>.*?</li>',
    re.I | re.S,
)
BBY_TITLE_RE = re.compile(
    r'<a[^>]+class=["\'][^"\']*sku-title[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.I | re.S,
)
BBY_PRICE_RE = re.compile(r'"currentPrice"\s*:\s*([\d.]+)', re.I)

NEWEGG_ITEM_RE = re.compile(
    r'<div[^>]+class=["\'][^"\']*item-cell[^"\']*["\'][^>]*>.*?</div>',
    re.I | re.S,
)
NEWEGG_TITLE_RE = re.compile(
    r'<a[^>]+class=["\'][^"\']*item-title[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.I | re.S,
)
NEWEGG_PRICE_RE = re.compile(
    r'<li[^>]+class=["\'][^"\']*price-current[^"\']*["\'][^>]*>.*?<strong>([^<]+)</strong>\s*<sup>([^<]+)</sup>',
    re.I | re.S,
)

MICROCENTER_ITEM_RE = re.compile(
    r'<li[^>]+class=["\'][^"\']*product_wrapper[^"\']*["\'][^>]*>.*?</li>',
    re.I | re.S,
)
MICROCENTER_TITLE_RE = re.compile(
    r'<a[^>]+data-name=["\']([^"\']+)["\'][^>]+href=["\']([^"\']+)["\']',
    re.I,
)
MICROCENTER_PRICE_RE = re.compile(r'(?:data-price|price)["\':=\s]+([\d.]+)', re.I)

BH_TILE_RE = re.compile(
    r'<div[^>]+data-selenium=["\']miniProductPage["\'][^>]*>.*?</div>',
    re.I | re.S,
)
BH_LINK_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
BH_DATA_PRICE_RE = re.compile(r'"price"\s*:\s*"?([\d,]+(?:\.\d{2})?)"?', re.I)
BH_SCRIPT_PRICE_RE = re.compile(r'\$([0-9,]+)(?:\.(\d{2}))?')
BH_IMAGE_RE = re.compile(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', re.I)

ANTONLINE_TILE_RE = re.compile(
    r'<div[^>]+class=["\'][^"\']*product-item-info[^"\']*["\'][^>]*>.*?</div>',
    re.I | re.S,
)

DEALNEWS_ITEM_RE = re.compile(
    r'<article[^>]*>.*?</article>|<div[^>]+class=["\'][^"\']*(?:deal|listing|item)[^"\']*["\'][^>]*>.*?</div>',
    re.I | re.S,
)

TOMS_ARTICLE_RE = re.compile(
    r'<article[^>]*>.*?</article>',
    re.I | re.S,
)

TOMS_LINK_RE = re.compile(
    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.I | re.S,
)

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
    if t in GENERIC_NAV_TITLES:
        return False
    if len(t.split()) < 4:
        return False
    bad_phrases = [
        "shop all", "view all", "see all", "top deals", "related searches",
        "featured products", "best sellers", "customer also viewed",
    ]
    return not any(p in t for p in bad_phrases)


def _categorize(title: str) -> str:
    t = _norm(title)
    scores = {cat: sum(1 for kw in kws if kw in t) for cat, kws in KEYWORDS.items()}
    scores = {k: v for k, v in scores.items() if v > 0}
    return max(scores, key=scores.get) if scores else "Other"


def _is_relevant(title: str) -> bool:
    t = _norm(title)

    if _contains_any(t, EXCLUDED_TERMS) or _contains_any(t, NON_PC_TERMS):
        return False
    if not _title_is_product(title):
        return False

    cat = _categorize(title)
    if cat == "Other":
        return False

    kw_hits = sum(1 for kw in KEYWORDS[cat] if kw in t)
    sig_hits = sum(1 for sig in STRONG_SIGNALS[cat] if sig in t)
    return kw_hits >= 1 or sig_hits >= 2


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


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", unescape(text or ""))).strip()


def _normalize_price_num(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.replace(",", "").strip().rstrip(".")
    if not raw:
        return None
    return f"${raw if '.' in raw else raw + '.00'}"


def _extract_first_valid_link_and_title(block: str, base_url: str) -> Tuple[Optional[str], Optional[str]]:
    for href, inner in LINK_RE.findall(block):
        link = _clean_url(href, base_url)
        title = _strip_tags(inner)
        if link and title and _is_relevant(title):
            return title, link
    return None, None


def _extract_json_ld_price_and_image(html: str, base_url: str = "") -> Tuple[Optional[str], Optional[str]]:
    price = None
    image = None

    for raw in SCRIPT_JSON_RE.findall(html):
        txt = unescape(raw)

        if not price:
            m = re.search(r'"price"\s*:\s*"?(?P<price>\d+(?:\.\d{2})?)"?', txt, re.I)
            if m:
                price = _normalize_price_num(m.group("price"))

        if not image:
            m = re.search(r'"image"\s*:\s*(?:"([^"]+)"|\[(.*?)\])', txt, re.I | re.S)
            if m:
                if m.group(1):
                    image = _clean_url(m.group(1), base_url)
                else:
                    mm = re.search(r'"(https?://[^"]+)"', m.group(2) or "", re.I)
                    if mm:
                        image = _clean_url(mm.group(1), base_url)

        if price and image:
            break

    return price, image


def _iter_product_blocks(source: str, html: str) -> List[str]:
    patterns = {
        "Amazon": AMAZON_PRODUCT_BLOCK_RE,
        "Best Buy": BESTBUY_TILE_RE,
        "Newegg": NEWEGG_ITEM_RE,
        "Micro Center": MICROCENTER_ITEM_RE,
        "B&H": BH_TILE_RE,
        "Antonline": ANTONLINE_TILE_RE,
        "TomsHardware": TOMS_ARTICLE_RE,
    }
    pattern = patterns.get(source)
    return [m.group(0) for m in pattern.finditer(html)] if pattern else []


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _amazon_price(chunk: str) -> Optional[str]:
    m = AMAZON_PRICE_RE.search(chunk)
    if m:
        return f"${float(m.group(1)):.2f}"
    whole = AMAZON_WHOLE_RE.search(chunk)
    if whole:
        frac = AMAZON_FRAC_RE.search(chunk)
        return f"${whole.group(1).replace(',', '').strip().rstrip('.')}.{frac.group(1).strip() if frac else '00'}"
    return _extract_price(chunk[:3000])


def _amazon_image(chunk: str) -> Optional[str]:
    m = AMAZON_HIRES_RE.search(chunk)
    if m:
        return m.group(1)
    m = AMAZON_SIMG_RE.search(chunk)
    return _clean_url(m.group(1)) if m else _og_image(chunk)


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
    return _clean_url(m.group(1), base) if m else _og_image(chunk, base)


def _og_image(html: str, base: str = "") -> Optional[str]:
    m = OG_IMAGE_RE.search(html)
    if m:
        return _clean_url(m.group(1), base)
    m = IMG_SRC_RE.search(html)
    return _clean_url(m.group(1), base) if m else None


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
    blob = _norm(f"{title} {summary}")
    if _contains_any(blob, NON_PC_TERMS):
        return None
    if not title or not _is_relevant(title):
        return None

    cat = _categorize(title)
    if cat == "Other":
        return None

    return {
        "id": _make_id(source, link),
        "title": title.strip(),
        "link": link.strip(),
        "source": source,
        "category": cat,
        "published": published,
        "summary": _safe_summary(summary),
        "price": price,
        "image": image,
        "product_link": product_link or link,
    }


# ---------------------------------------------------------------------------
# Store/article parsers
# ---------------------------------------------------------------------------

def _parse_amazon_block(block: str, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    m = AMAZON_TITLE_RE.search(block)
    title = _strip_tags(m.group(2)) if m else None
    link = _clean_url(m.group(1), base_url) if m else None

    if not title or not link:
        title, link = _extract_first_valid_link_and_title(block, base_url)

    if not title or not link or not _is_relevant(title):
        return None

    asin_m = AMAZON_ASIN_RE.search(block)
    if asin_m and "/dp/" not in link:
        link = f"{base_url}/dp/{asin_m.group(1)}"

    return {
        "title": title,
        "link": link,
        "price": _amazon_price(block),
        "image": _amazon_image(block),
    }


def _parse_bestbuy_block(block: str, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    m = BBY_TITLE_RE.search(block)
    title = _strip_tags(m.group(2)) if m else None
    link = _clean_url(m.group(1), base_url) if m else None

    if not title or not link:
        title, link = _extract_first_valid_link_and_title(block, base_url)

    if not title or not link or "/site/" not in link or "searchpage.jsp" in link or not _is_relevant(title):
        return None

    img_m = IMG_SRC_RE.search(block)
    return {
        "title": title,
        "link": link,
        "price": _bestbuy_price(block),
        "image": _clean_url(img_m.group(1), base_url) if img_m else None,
    }


def _parse_newegg_block(block: str, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    m = NEWEGG_TITLE_RE.search(block)
    if not m:
        return None

    link = _clean_url(m.group(1), base_url)
    title = _strip_tags(m.group(2))
    if not link or not title or not _is_relevant(title):
        return None

    pm = NEWEGG_PRICE_RE.search(block)
    price = f"${pm.group(1).replace(',', '')}.{pm.group(2).replace('.', '').strip()}" if pm else _extract_price(block[:2500])

    img_m = IMG_SRC_RE.search(block)
    return {
        "title": title,
        "link": link,
        "price": price,
        "image": _clean_url(img_m.group(1), base_url) if img_m else None,
    }


def _parse_microcenter_block(block: str, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    m = MICROCENTER_TITLE_RE.search(block)
    title = _strip_tags(m.group(1)) if m else None
    link = _clean_url(m.group(2), base_url) if m else None

    if not title or not link:
        title, link = _extract_first_valid_link_and_title(block, base_url)

    if not title or not link or "/product/" not in link or not _is_relevant(title):
        return None

    pm = MICROCENTER_PRICE_RE.search(block)
    img_m = IMG_SRC_RE.search(block)
    return {
        "title": title,
        "link": link,
        "price": _normalize_price_num(pm.group(1)) if pm else _extract_price(block[:2500]),
        "image": _clean_url(img_m.group(1), base_url) if img_m else None,
    }


def _parse_bh_block(block: str, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    title = None
    link = None

    for href, inner in BH_LINK_RE.findall(block):
        full = _clean_url(href, base_url)
        cleaned = _strip_tags(inner)
        if full and cleaned and _is_relevant(cleaned):
            title = cleaned
            link = full
            break

    if not title or not link:
        return None

    return {
        "title": title,
        "link": link,
        "price": _bh_price(block),
        "image": _bh_image(block, base_url),
    }


def _parse_antonline_block(block: str, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    title, link = _extract_first_valid_link_and_title(block, base_url)
    if not title or not link or not _is_relevant(title):
        return None

    img_m = IMG_SRC_RE.search(block)
    return {
        "title": title,
        "link": link,
        "price": _extract_price(block[:2500]),
        "image": _clean_url(img_m.group(1), base_url) if img_m else None,
    }


def _parse_tomshardware_block(block: str, base_url: str) -> Optional[Dict[str, Optional[str]]]:
    title = None
    link = None

    for href, inner in TOMS_LINK_RE.findall(block):
        full = _clean_url(href, base_url)
        cleaned = _strip_tags(inner)

        if not full or not cleaned:
            continue
        if "/deals/" not in full and "/best-picks/" not in full:
            continue
        if _is_relevant(cleaned):
            title = cleaned
            link = full
            break

    if not title or not link:
        return None

    img_m = IMG_SRC_RE.search(block)
    return {
        "title": title,
        "link": link,
        "price": _extract_price(block[:4000]),
        "image": _clean_url(img_m.group(1), base_url) if img_m else None,
    }


# ---------------------------------------------------------------------------
# HTTP fetch
# ---------------------------------------------------------------------------

_SEMAPHORE = 8
_IMPERSONATE = "chrome136"
_TIMEOUT = 20
_RETRIES = 2
_RETRY_CODES = {429, 500, 502, 503, 504}

_EXTRA_HEADERS: Dict[str, Dict[str, str]] = {
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
    "DealNews": {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, text/html;q=0.8, */*;q=0.7",
        "Cache-Control": "no-cache",
    },
}


async def _fetch(
    session: AsyncSession,
    sem: asyncio.Semaphore,
    url: str,
    source: str,
    timeout: int = _TIMEOUT,
) -> Optional[str]:
    headers = _EXTRA_HEADERS.get(source, {})
    async with sem:
        for attempt in range(_RETRIES + 1):
            try:
                r = await session.get(url, timeout=timeout, headers=headers, allow_redirects=True)
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
# RSS sources
# ---------------------------------------------------------------------------

async def fetch_rss(session: AsyncSession, sem: asyncio.Semaphore, source: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for url in RSS_SOURCES[source]:
        text = await _fetch(session, sem, url, source)
        if not text:
            continue

        parsed = feedparser.parse(text)
        for entry in parsed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            blob = _norm(f"{title} {summary}")

            if _contains_any(blob, NON_PC_TERMS):
                continue

            deal = _make_deal(
                source,
                title,
                link,
                entry.get("published", ""),
                summary,
                price=_extract_price(title, summary),
                image=_image_from_entry(entry),
            )
            if deal and deal["id"] not in seen:
                seen.add(deal["id"])
                results.append(deal)

    print(f"[{source}] {len(results)} RSS deals")
    return results


# ---------------------------------------------------------------------------
# DealNews HTML fallback
# ---------------------------------------------------------------------------

async def fetch_dealnews_html(session: AsyncSession, sem: asyncio.Semaphore) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for url in DEALNEWS_HTML_URLS:
        text = await _fetch(session, sem, url, "DealNews")
        if not text:
            continue

        base_url = "https://www.dealnews.com"

        for block in DEALNEWS_ITEM_RE.findall(text):
            title, link = _extract_first_valid_link_and_title(block, base_url)
            if not title or not link:
                continue
            if "/deal/" not in link and "/c" not in link and "/f" not in link:
                continue

            deal = _make_deal(
                source="DealNews",
                title=title,
                link=link,
                published=datetime.now(timezone.utc).isoformat(),
                summary=title,
                price=_extract_price(block[:4000]),
                image=_og_image(block, base_url),
                product_link=link,
            )
            if deal and deal["id"] not in seen:
                seen.add(deal["id"])
                results.append(deal)

    print(f"[DealNews HTML fallback] {len(results)} deals")
    return results


# ---------------------------------------------------------------------------
# HTML sources
# ---------------------------------------------------------------------------

async def fetch_html(session: AsyncSession, sem: asyncio.Semaphore, source: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    parsers = {
        "Amazon": _parse_amazon_block,
        "Best Buy": _parse_bestbuy_block,
        "Newegg": _parse_newegg_block,
        "Micro Center": _parse_microcenter_block,
        "B&H": _parse_bh_block,
        "Antonline": _parse_antonline_block,
        "TomsHardware": _parse_tomshardware_block,
    }

    for url in HTML_SOURCES[source]:
        text = await _fetch(session, sem, url, source)
        if not text:
            continue

        base_m = re.match(r"(https?://[^/]+)", url)
        base_url = base_m.group(1) if base_m else ""

        parser = parsers.get(source)
        blocks = _iter_product_blocks(source, text)

        if parser and blocks:
            for block in blocks:
                parsed = parser(block, base_url)
                if not parsed:
                    continue

                deal = _make_deal(
                    source=source,
                    title=parsed["title"] or "",
                    link=parsed["link"] or "",
                    published=datetime.now(timezone.utc).isoformat(),
                    summary=parsed["title"] or "",
                    price=parsed.get("price"),
                    image=parsed.get("image"),
                    product_link=parsed["link"],
                )
                if deal and deal["id"] not in seen:
                    seen.add(deal["id"])
                    results.append(deal)
            continue

        patterns = PRODUCT_URL_PATTERNS.get(source, [])
        for m in LINK_RE.finditer(text):
            href, raw = m.groups()
            link = _clean_url(href, base_url)
            if not link:
                continue
            if patterns and not any(p in link for p in patterns):
                continue

            title = _strip_tags(raw)
            if not _is_relevant(title):
                continue

            pos = m.start()
            chunk = text[max(0, pos - 400):pos + 2200]

            deal = _make_deal(
                source=source,
                title=title,
                link=link,
                published=datetime.now(timezone.utc).isoformat(),
                summary=title,
                price=_extract_price(chunk),
                image=_og_image(chunk, base_url),
                product_link=link,
            )
            if deal and deal["id"] not in seen:
                seen.add(deal["id"])
                results.append(deal)

    print(f"[{source}] {min(len(results), 30)} deals")
    return results[:30]


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

async def _enrich(session: AsyncSession, sem: asyncio.Semaphore, deal: Dict[str, Any]) -> Dict[str, Any]:
    if deal.get("price") and deal.get("image"):
        return deal

    target = deal.get("product_link") or deal.get("link")
    if not target:
        return deal

    bad_targets = [
        "searchpage.jsp",
        "/p/pl?d=",
        "/search/search_results.aspx",
        "/s?",
        "/site/searchpage.jsp",
        "/c/buy/",
        "/c/browse/",
        "/deals/page/",
    ]
    if any(x in target for x in bad_targets):
        return deal

    html = await _fetch(session, sem, target, deal["source"], timeout=12)
    if not html:
        return deal

    source = deal.get("source", "")
    json_price, json_image = _extract_json_ld_price_and_image(html, target)

    if not deal.get("price"):
        if json_price:
            deal["price"] = json_price
        elif source == "Amazon":
            deal["price"] = _amazon_price(html)
        elif source == "Best Buy":
            deal["price"] = _bestbuy_price(html)
        elif source == "B&H":
            deal["price"] = _bh_price(html)
        else:
            deal["price"] = _extract_price(html[:4000])

    if not deal.get("image"):
        if json_image:
            deal["image"] = json_image
        elif source == "Amazon":
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
            [fetch_rss(session, sem, src) for src in RSS_SOURCES if src != "DealNews"]
            + [
                asyncio.gather(
                    fetch_rss(session, sem, "DealNews"),
                    fetch_dealnews_html(session, sem),
                )
            ]
            + [fetch_html(session, sem, src) for src in HTML_SOURCES]
        )
        batches = await asyncio.gather(*tasks, return_exceptions=True)

    seen: Set[str] = set()
    fresh: List[Dict[str, Any]] = []

    for batch in batches:
        if isinstance(batch, Exception):
            print(f"[Scraper] Task error: {batch}")
            continue

        if isinstance(batch, (tuple, list)) and batch and all(isinstance(x, list) for x in batch):
            iterable_batches = batch
        else:
            iterable_batches = [batch]

        for inner_batch in iterable_batches:
            for deal in inner_batch:
                if deal["id"] not in seen:
                    seen.add(deal["id"])
                    fresh.append(deal)

    async with AsyncSession(impersonate=_IMPERSONATE) as session:
        enrich_sem = asyncio.Semaphore(6)
        fresh = list(await asyncio.gather(*[_enrich(session, enrich_sem, d) for d in fresh]))

    fresh = [d for d in fresh if d.get("price")]
    fresh.sort(key=lambda d: d.get("published") or "", reverse=True)

    _deals_cache = fresh
    _last_updated = datetime.now(timezone.utc)

    source_counts = {name: 0 for name in SOURCE_ORDER}
    for deal in fresh:
        source = deal.get("source")
        if source in source_counts:
            source_counts[source] += 1

    _source_status_cache = {
        name: {
            "name": name,
            "deal_count": source_counts[name],
            "status": "LIVE",
            "uptime": "ACTIVE",
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
        "source_statuses": [
            _source_status_cache.get(name, {
                "name": name,
                "deal_count": 0,
                "status": "LIVE",
                "uptime": "ACTIVE",
            })
            for name in SOURCE_ORDER
        ],
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
            img = "img✓" if deal.get("image") else "img✗"
            print(
                f"[{deal['category']:12s}] [{deal['source']:20s}] "
                f"{deal['title'][:50]:<50} | {price:<10} | {img}"
            )

    asyncio.run(_main())