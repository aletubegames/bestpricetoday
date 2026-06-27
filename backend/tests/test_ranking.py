from app.services.ranking.engine import rank_offers, detect_fake_discount
from app.schemas.schemas import OfferSchema, ProviderEnum


def make_offer(**kwargs):
    defaults = dict(
        provider=ProviderEnum.mercadolivre,
        title="Test",
        price=100.0,
        final_price=100.0,
        shipping_free=False,
        shipping_price=0,
        discount_percent=0,
        cashback_percent=0,
        coupon_discount=0,
        score=0,
        affiliate_url="https://example.com",
        economy=0,
        is_fake_discount=False,
    )
    defaults.update(kwargs)
    return OfferSchema(**defaults)


def test_rank_orders_by_score():
    offers = [
        make_offer(price=200, final_price=200),
        make_offer(price=100, final_price=100, shipping_free=True),
    ]
    ranked = rank_offers(offers)
    assert ranked[0].final_price == 100


def test_fake_discount_detection():
    offer = make_offer(price=10, original_price=1000, discount_percent=99)
    assert detect_fake_discount(offer) is True


def test_no_fake_discount():
    offer = make_offer(price=90, original_price=100, discount_percent=10)
    assert detect_fake_discount(offer) is False
