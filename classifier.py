"""
Классификация поставщиков на дешёвый/средний/дорогой.
Фильтрует аномальные цены и нерелевантные результаты.
"""
from typing import List
from dataclasses import dataclass, asdict
from scrapers import Listing
import re


@dataclass
class Supplier:
    tier: str
    supplier_name: str
    supplier_address: str
    supplier_phone: str
    supplier_website: str
    price_per_unit: float
    total: float
    source: str

    def dict(self):
        return asdict(self)


def is_relevant(listing: Listing, query: str) -> bool:
    """Проверяет соответствие объявления запросу (хотя бы 1 слово совпадает)"""
    query_words = set(re.sub(r'[^\w\s]', '', query.lower()).split())
    title_words = set(re.sub(r'[^\w\s]', '', listing.title.lower()).split())
    return bool(query_words & title_words)


def filter_anomalies(listings: List[Listing]) -> List[Listing]:
    """Убирает аномально высокие цены (в 100+ раз выше медианы)"""
    if len(listings) < 2:
        return listings
    prices = sorted(l.price for l in listings)
    median = prices[len(prices) // 2]
    filtered = [l for l in listings if l.price <= median * 100]
    return filtered if filtered else listings[:3]


def classify_suppliers(listings: List[Listing], qty: float, query: str = "") -> List[Supplier]:
    """Выбирает 3 поставщиков: дешёвый / средний / дорогой"""
    if not listings:
        return []

    # Фильтр по релевантности
    if query:
        relevant = [l for l in listings if is_relevant(l, query)]
        if len(relevant) >= 2:
            listings = relevant

    valid = [l for l in listings if l.price and l.price > 0]
    valid = filter_anomalies(valid)
    if not valid:
        return []

    valid.sort(key=lambda x: x.price)
    n = len(valid)
    suppliers = [_to_supplier(valid[0], "cheap", qty)]

    if n >= 3:
        suppliers.append(_to_supplier(valid[n // 2], "mid", qty))
        suppliers.append(_to_supplier(valid[-1], "exp", qty))
    elif n == 2:
        suppliers.append(_to_supplier(valid[-1], "exp", qty))

    return suppliers


def _to_supplier(l: Listing, tier: str, qty: float) -> Supplier:
    return Supplier(
        tier=tier,
        supplier_name=l.seller_name or l.source or "Не указано",
        supplier_address=l.address or "",
        supplier_phone="",
        supplier_website=l.url or "",
        price_per_unit=round(l.price, 2),
        total=round(l.price * qty, 2),
        source=l.source,)
