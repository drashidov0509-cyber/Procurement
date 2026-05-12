"""
Классификация поставщиков на дешёвый/средний/дорогой
"""
from typing import List
from dataclasses import dataclass, asdict
from scrapers import Listing


@dataclass
class Supplier:
    tier: str  # cheap | mid | exp
    supplier_name: str
    supplier_address: str
    supplier_phone: str
    supplier_website: str
    price_per_unit: float
    total: float
    source: str

    def dict(self):
        return asdict(self)


def classify_suppliers(listings: List[Listing], qty: float) -> List[Supplier]:
    """Из списка объявлений выбираем 3 представителей: min/median/max"""
    if not listings:
        return []

    valid = [l for l in listings if l.price and l.price > 0]
    if not valid:
        return []

    valid.sort(key=lambda x: x.price)
    n = len(valid)
    suppliers = []

    cheap = valid[0]
    suppliers.append(_to_supplier(cheap, "cheap", qty))

    if n >= 3:
        mid = valid[n // 2]
        suppliers.append(_to_supplier(mid, "mid", qty))
        exp = valid[-1]
        suppliers.append(_to_supplier(exp, "exp", qty))
    elif n == 2:
        # 2 поставщика: первый — cheap, второй — exp
        suppliers.append(_to_supplier(valid[1], "exp", qty))

    return suppliers


def _to_supplier(l: Listing, tier: str, qty: float) -> Supplier:
    name = l.seller_name or l.source or "Не указано"
    return Supplier(
        tier=tier,
        supplier_name=name,
        supplier_address=l.address or "",
        supplier_phone="",
        supplier_website=l.url or "",
        price_per_unit=round(l.price, 2),
        total=round(l.price * qty, 2),
        source=l.source,
    )
