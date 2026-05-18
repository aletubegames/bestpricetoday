"""AI-powered offer ranking engine."""
from typing import List
from app.schemas.schemas import OfferSchema


PROVIDER_TRUST = {
    "mercadolivre": 0.95,
    "amazon": 0.98,
    "kabum": 0.92,
    "shopee": 0.85,
    "lomadee": 0.80,
    "awin": 0.80,
    "aliexpress": 0.75,
}

FAKE_DISCOUNT_THRESHOLD = 0.80  # if discount > 80%, likely fake


def detect_fake_discount(offer: OfferSchema) -> bool:
    if not offer.original_price or offer.original_price <= 0:
        return False
    if offer.discount_percent > 80:
        return True
    if offer.original_price > 0 and offer.price / offer.original_price < 0.10:
        return True
    return False



def rank_offers(offers: List[OfferSchema]) -> List[OfferSchema]:
    if not offers:
        return []

    # Detect fake discounts
    for offer in offers:
        offer.is_fake_discount = detect_fake_discount(offer)

    # Normalize prices for relative scoring
    prices = [o.final_price for o in offers if o.final_price > 0]
    if not prices:
        return offers
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price or 1

    for offer in offers:
        # Price score: 0-40 (lower price = higher score)
        price_norm = 1 - ((offer.final_price - min_price) / price_range)
        base = price_norm * 40

        if offer.shipping_free:
            base += 20
        base += min(offer.discount_percent, 50) * 0.30
        base += min(offer.cashback_percent * 2, 10)
        trust = PROVIDER_TRUST.get(offer.provider.value, 0.75)
        base += trust * 10
        if offer.coupon_code:
            base += 5
        if offer.is_fake_discount:
            base *= 0.5

        offer.score = round(min(base, 100), 2)

    return sorted(offers, key=lambda o: o.score, reverse=True)
