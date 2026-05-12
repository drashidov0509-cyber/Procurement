"""
Скраперы маркетплейсов для разных стран.
Полноценная поддержка: UZ, AZ, KZ, KG, RU, TR
Для остальных — фолбэк через DuckDuckGo.
"""
import asyncio
import httpx
from urllib.parse import quote_plus, urlparse
from typing import List, Optional
from dataclasses import dataclass
from selectolax.parser import HTMLParser


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

TIMEOUT = 15


@dataclass
class Listing:
    title: str
    price: float
    currency: str
    seller_name: str = ""
    address: str = ""
    url: str = ""
    source: str = ""


def clean_price(s: str) -> Optional[float]:
    if not s:
        return None
    cleaned = "".join(c for c in s if c.isdigit() or c in ".,")
    cleaned = cleaned.replace(",", ".").replace(" ", "")
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def clean_text(t: Optional[str]) -> str:
    return " ".join(t.split()) if t else ""


def detect_currency(price_text: str, default: str) -> str:
    if not price_text:
        return default
    pt = price_text.upper()
    if "$" in price_text or "USD" in pt:
        return "USD"
    if "€" in price_text or "EUR" in pt:
        return "EUR"
    if "₽" in price_text or "РУБ" in pt or "RUB" in pt:
        return "RUB"
    if "₸" in price_text or "ТГ" in pt or "KZT" in pt:
        return "KZT"
    if "₼" in price_text or "AZN" in pt or "МАН" in pt:
        return "AZN"
    if "СОМ" in pt or "KGS" in pt:
        return "KGS"
    if "TL" in pt or "₺" in price_text or "TRY" in pt:
        return "TRY"
    return default


async def fetch_html(url: str, params: dict = None) -> Optional[str]:
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, follow_redirects=True, headers=HEADERS
        ) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                return r.text
            print(f"⚠ HTTP {r.status_code}: {url}")
    except Exception as e:
        print(f"⚠ Fetch error {url}: {e}")
    return None


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "") or "unknown"
    except Exception:
        return "unknown"


# ════════════════════════════════════════════════════════════════════════
# УЗБЕКИСТАН
# ════════════════════════════════════════════════════════════════════════
async def scrape_olx_uz(query: str) -> List[Listing]:
    """OLX.uz — крупнейшая площадка объявлений Узбекистана"""
    url = f"https://www.olx.uz/list/q-{quote_plus(query)}/"
    html = await fetch_html(url)
    if not html:
        return []

    tree = HTMLParser(html)
    listings = []
    for card in tree.css('div[data-cy="l-card"]')[:25]:
        try:
            t_node = card.css_first('h4, h6')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('p[data-testid="ad-price"]')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 100:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://www.olx.uz{href}"
            loc_node = card.css_first('p[data-testid="location-date"]')
            location = clean_text(loc_node.text()) if loc_node else ""
            listings.append(Listing(
                title=title, price=price,
                currency=detect_currency(price_text, "UZS"),
                address=location, url=full_url, source="olx.uz"
            ))
        except Exception:
            continue
    return listings


async def scrape_glotr_uz(query: str) -> List[Listing]:
    """Glotr.uz — B2B-каталог Узбекистана"""
    html = await fetch_html("https://glotr.uz/search/", params={"q": query})
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('.b-product-list__item, .product-card, [class*="product"]')[:25]:
        try:
            t_node = card.css_first('a.title, .product-title, h3 a, .name a')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('.price, .b-product-price, [class*="price"]')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 100:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://glotr.uz{href}"
            seller_node = card.css_first('.company, .seller, .b-company-info')
            seller = clean_text(seller_node.text()) if seller_node else ""
            listings.append(Listing(
                title=title, price=price, currency="UZS",
                seller_name=seller, url=full_url, source="glotr.uz"
            ))
        except Exception:
            continue
    return listings


# ════════════════════════════════════════════════════════════════════════
# АЗЕРБАЙДЖАН
# ════════════════════════════════════════════════════════════════════════
async def scrape_tap_az(query: str) -> List[Listing]:
    """Tap.az — крупнейшая площадка Азербайджана"""
    url = f"https://tap.az/elanlar/?keywords={quote_plus(query)}"
    html = await fetch_html(url)
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('.products-i, .products-list-item, [class*="product"]')[:25]:
        try:
            t_node = card.css_first('.products-name, h3 a, .product-title')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('.product-price, .price-val')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 1:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://tap.az{href}"
            loc_node = card.css_first('.products-created, .location')
            loc = clean_text(loc_node.text()) if loc_node else ""
            listings.append(Listing(
                title=title, price=price,
                currency=detect_currency(price_text, "AZN"),
                address=loc, url=full_url, source="tap.az"
            ))
        except Exception:
            continue
    return listings


async def scrape_lalafo_az(query: str) -> List[Listing]:
    """Lalafo.az — Азербайджан"""
    url = f"https://lalafo.az/azerbaijan?q={quote_plus(query)}"
    html = await fetch_html(url)
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('article.AdItem, .ad-item, [class*="AdTile"], [class*="adItem"]')[:25]:
        try:
            t_node = card.css_first('h3, .ad-title, [class*="title"] a')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('[class*="price"], .ad-price')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 1:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://lalafo.az{href}"
            listings.append(Listing(
                title=title, price=price,
                currency=detect_currency(price_text, "AZN"),
                url=full_url, source="lalafo.az"
            ))
        except Exception:
            continue
    return listings


# ════════════════════════════════════════════════════════════════════════
# КАЗАХСТАН
# ════════════════════════════════════════════════════════════════════════
async def scrape_olx_kz(query: str) -> List[Listing]:
    """OLX.kz — Казахстан"""
    url = f"https://www.olx.kz/list/q-{quote_plus(query)}/"
    html = await fetch_html(url)
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('div[data-cy="l-card"]')[:25]:
        try:
            t_node = card.css_first('h4, h6')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('p[data-testid="ad-price"]')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 1:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://www.olx.kz{href}"
            loc_node = card.css_first('p[data-testid="location-date"]')
            location = clean_text(loc_node.text()) if loc_node else ""
            listings.append(Listing(
                title=title, price=price,
                currency=detect_currency(price_text, "KZT"),
                address=location, url=full_url, source="olx.kz"
            ))
        except Exception:
            continue
    return listings


async def scrape_satu_kz(query: str) -> List[Listing]:
    """Satu.kz — B2B-маркетплейс Казахстана"""
    url = f"https://satu.kz/search.html?search_term={quote_plus(query)}"
    html = await fetch_html(url)
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('[data-qaid="product_block"], .b-product-gallery__item, [class*="product"]')[:25]:
        try:
            t_node = card.css_first('[data-qaid="product_name"], a[class*="title"], .b-product-gallery__title')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('[data-qaid="price"], [class*="price"]')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 1:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://satu.kz{href}"
            seller_node = card.css_first('[data-qaid="company_name"], .company-name')
            seller = clean_text(seller_node.text()) if seller_node else ""
            listings.append(Listing(
                title=title, price=price, currency="KZT",
                seller_name=seller, url=full_url, source="satu.kz"
            ))
        except Exception:
            continue
    return listings


# ════════════════════════════════════════════════════════════════════════
# КЫРГЫЗСТАН
# ════════════════════════════════════════════════════════════════════════
async def scrape_lalafo_kg(query: str) -> List[Listing]:
    """Lalafo.kg — Кыргызстан"""
    url = f"https://lalafo.kg/kyrgyzstan?q={quote_plus(query)}"
    html = await fetch_html(url)
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('article.AdItem, .ad-item, [class*="AdTile"], [class*="adItem"]')[:25]:
        try:
            t_node = card.css_first('h3, .ad-title, [class*="title"] a')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('[class*="price"], .ad-price')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 1:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://lalafo.kg{href}"
            listings.append(Listing(
                title=title, price=price,
                currency=detect_currency(price_text, "KGS"),
                url=full_url, source="lalafo.kg"
            ))
        except Exception:
            continue
    return listings


# ════════════════════════════════════════════════════════════════════════
# РОССИЯ
# ════════════════════════════════════════════════════════════════════════
async def scrape_avito_ru(query: str) -> List[Listing]:
    """Avito.ru — Россия"""
    url = f"https://www.avito.ru/all?q={quote_plus(query)}"
    html = await fetch_html(url)
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('[data-marker="item"], [class*="iva-item"]')[:25]:
        try:
            t_node = card.css_first('[itemprop="name"], h3 a, [data-marker="item-title"]')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('[itemprop="price"], [data-marker="item-price"]')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 1:
                continue
            link = card.css_first('a[itemprop="url"], a[data-marker="item-title"], h3 a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://www.avito.ru{href}"
            loc_node = card.css_first('[class*="geo"], .item-address')
            location = clean_text(loc_node.text()) if loc_node else ""
            listings.append(Listing(
                title=title, price=price, currency="RUB",
                address=location, url=full_url, source="avito.ru"
            ))
        except Exception:
            continue
    return listings


# ════════════════════════════════════════════════════════════════════════
# ТУРЦИЯ
# ════════════════════════════════════════════════════════════════════════
async def scrape_sahibinden_tr(query: str) -> List[Listing]:
    """Sahibinden.com — крупнейшая площадка Турции"""
    url = f"https://www.sahibinden.com/en/search?query_text_mf={quote_plus(query)}"
    html = await fetch_html(url)
    if not html:
        return []
    tree = HTMLParser(html)
    listings = []
    for card in tree.css('tr.searchResultsItem, [class*="classified"]')[:25]:
        try:
            t_node = card.css_first('.classifiedTitle, a[class*="title"]')
            title = clean_text(t_node.text()) if t_node else ""
            if not title:
                continue
            p_node = card.css_first('.searchResultsPriceValue, [class*="price"]')
            price_text = p_node.text() if p_node else ""
            price = clean_price(price_text)
            if not price or price < 1:
                continue
            link = card.css_first('a')
            href = link.attributes.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"https://www.sahibinden.com{href}"
            listings.append(Listing(
                title=title, price=price,
                currency=detect_currency(price_text, "TRY"),
                url=full_url, source="sahibinden.com"
            ))
        except Exception:
            continue
    return listings


# ════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ ПО СТРАНАМ
# ════════════════════════════════════════════════════════════════════════
COUNTRY_DEFAULT_CURRENCY = {
    "UZ": "UZS", "AZ": "AZN", "KZ": "KZT", "KG": "KGS",
    "TJ": "TJS", "TM": "TMT", "RU": "RUB", "TR": "TRY",
    "CN": "CNY", "DE": "EUR", "US": "USD", "AE": "AED",
    "GB": "GBP", "PL": "PLN", "GE": "GEL", "AM": "AMD",
}

SCRAPERS = {
    "UZ": [scrape_olx_uz, scrape_glotr_uz],
    "AZ": [scrape_tap_az, scrape_lalafo_az],
    "KZ": [scrape_olx_kz, scrape_satu_kz],
    "KG": [scrape_lalafo_kg],
    "RU": [scrape_avito_ru],
    "TR": [scrape_sahibinden_tr],
}


# ════════════════════════════════════════════════════════════════════════
# DUCKDUCKGO — фолбэк для всех остальных стран
# ════════════════════════════════════════════════════════════════════════
async def scrape_ddg(query: str, country: str) -> List[Listing]:
    """Универсальный фолбэк через DuckDuckGo"""
    country_hints = {
        "UZ": "Узбекистан Ташкент купить",
        "AZ": "Azerbaycan Baku купить",
        "KZ": "Казахстан Алматы купить",
        "KG": "Кыргызстан Бишкек купить",
        "TJ": "Таджикистан Душанбе купить",
        "TM": "Туркменистан Ашхабад купить",
        "RU": "Россия купить цена",
        "TR": "Türkiye satın al",
        "CN": "China supplier price",
        "DE": "Deutschland kaufen Preis",
        "US": "USA buy price supplier",
        "AE": "UAE Dubai supplier price",
        "GB": "UK supplier price",
        "PL": "Polska kupić cena",
        "GE": "Georgia Tbilisi supplier",
        "AM": "Armenia Yerevan supplier",
    }
    full_query = f"{query} {country_hints.get(country, '')}"
    html = await fetch_html("https://html.duckduckgo.com/html", params={"q": full_query})
    if not html:
        return []

    tree = HTMLParser(html)
    listings = []
    default_currency = COUNTRY_DEFAULT_CURRENCY.get(country, "USD")

    for r in tree.css('.result__body')[:20]:
        try:
            t_node = r.css_first('.result__title a')
            title = clean_text(t_node.text()) if t_node else ""
            href = t_node.attributes.get("href", "") if t_node else ""

            sn_node = r.css_first('.result__snippet')
            snippet = clean_text(sn_node.text()) if sn_node else ""

            if not title or not href:
                continue

            price = None
            for token in snippet.split():
                p = clean_price(token)
                # Минимальная цена зависит от валюты (UZS/RUB/KZT в десятках тысяч обычно)
                min_price = 100 if default_currency in ("UZS", "RUB", "KZT") else 1
                if p and min_price <= p < 1_000_000_000:
                    price = p
                    break
            if not price:
                continue

            domain = extract_domain(href)
            listings.append(Listing(
                title=title, price=price,
                currency=detect_currency(snippet, default_currency),
                seller_name=domain, address=snippet[:150],
                url=href, source=f"web ({domain})"
            ))
        except Exception:
            continue

    return listings


# ════════════════════════════════════════════════════════════════════════
# ОРКЕСТРАТОР
# ════════════════════════════════════════════════════════════════════════
async def search_all_sources(
    query: str, country: str = "UZ", region: str = ""
) -> List[Listing]:
    """
    Запускает все доступные скраперы для страны параллельно.
    Если основные дали мало результатов — добавляет фолбэк через DuckDuckGo.
    """
    funcs = SCRAPERS.get(country, [])
    tasks = [f(query) for f in funcs]
    results: List[Listing] = []

    if tasks:
        scraped = await asyncio.gather(*tasks, return_exceptions=True)
        for r in scraped:
            if isinstance(r, list):
                results.extend(r)
            elif isinstance(r, Exception):
                print(f"⚠ Scraper failed: {r}")

    # Фолбэк через DuckDuckGo если основных мало
    if len(results) < 3:
        try:
            ddg_results = await scrape_ddg(query, country)
            results.extend(ddg_results)
        except Exception as e:
            print(f"⚠ DDG fallback failed: {e}")

    return results
