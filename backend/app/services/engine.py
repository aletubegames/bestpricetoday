"""AI-powered offer ranking engine."""
import re
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

# Termos que indicam acessorio (nao o produto principal)
_ACCESSORY_KEYWORDS = re.compile(
    r"\b(case|capa|cover|pelicula|protetor|screen protector|film|skin|sticker|"
    r"holder|stand|mount|suporte|bracelet|pulseira|strap|correia|band|"
    r"charger|carregador|cable|cabo|adapter|adaptador|dock|base|"
    r"earphone|earbuds|fone|headphone|headset)\b",
    re.IGNORECASE,
)

# Termos que indicam que a query busca um produto principal (nao acessorio)
_MAIN_PRODUCT_KEYWORDS = re.compile(
    r"\b(iphone|samsung|galaxy|xiaomi|redmi|motorola|moto|realme|pixel|"
    r"notebook|macbook|laptop|ultrabook|chromebook|"
    r"ps5|playstation|xbox|nintendo|switch|"
    r"tv|smart.?tv|monitor|"
    r"airfryer|geladeira|refrigerador|fogao|cooktop|microondas|lava|"
    r"ar.?condicionado|"
    r"rtx|placa.?de.?video|processador|"
    r"tenis|sapato|sandalia|bota|"
    r"perfume|colon ia|"
    r"bicicleta|esteira|halter|"
    r"camera|canon|nikon|sony|gopro)\b",
    re.IGNORECASE,
)


def _is_accessory(title: str) -> bool:
    """Detecta se o titulo parece ser um acessorio (capa, case, etc)."""
    return bool(_ACCESSORY_KEYWORDS.search(title))


def _is_main_product_query(query: str) -> bool:
    """Detecta se a query busca um produto principal (smartphone, notebook, etc)."""
    return bool(_MAIN_PRODUCT_KEYWORDS.search(query))


def filter_accessories(offers: List[OfferSchema], query: str) -> List[OfferSchema]:
    """Remove acessorios quando a query busca um produto principal.

    Ex: buscar 'iphone 16 pro' nao deve retornar capas de iphone.
    """
    if not _is_main_product_query(query):
        return offers

    filtered = [o for o in offers if not _is_accessory(o.title or "")]
    # Se filtrou tudo, retorna original (melhor ter acessorios do que nada)
    return filtered if filtered else offers


def detect_fake_discount(offer: OfferSchema) -> bool:
    if not offer.original_price or offer.original_price <= 0:
        return False
    if offer.discount_percent > 80:
        return True
    if offer.original_price > 0 and offer.price / offer.original_price < 0.10:
        return True
    return False



def rank_offers(offers: List[OfferSchema], query: str = "") -> List[OfferSchema]:
    if not offers:
        return []

    # Filtra acessorios se a query busca produto principal
    if query:
        offers = filter_accessories(offers, query)

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
