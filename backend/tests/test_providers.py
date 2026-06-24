import pytest

from app.schemas.schemas import OfferSchema, ProviderEnum
from app.services.providers.aliexpress import AliExpressProvider
from app.services.providers.lomadee import LomadeeProvider


def test_aliexpress_filters_irrelevant_accessories():
    """Filtro de relevância movido para AliExpressClient._filter_relevant."""
    from app.integrations.aliexpress import AliExpressClient
    from app.integrations.base import ProductResult, MarketplaceId

    client = AliExpressClient()
    results = [
        ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id="1",
            title="Caixa de telefone clara com bolso para iPhone 16 Pro",
            price=19.9,
            affiliate_url="https://example.com/case",
        ),
        ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id="2",
            title="Apple iPhone 16 Pro Smartphone 256GB",
            price=5999.0,
            affiliate_url="https://example.com/phone",
        ),
    ]

    filtered = client._filter_relevant("iphone 16 pro", results)

    assert len(filtered) == 1
    assert filtered[0].title == "Apple iPhone 16 Pro Smartphone 256GB"


@pytest.mark.asyncio
async def test_lomadee_parse_product_keeps_reais(monkeypatch):
    provider = LomadeeProvider()

    async def fake_fetch_suggested_price(product_url: str, current_price: float):
        return None

    async def fake_generate_affiliate_link(product_url: str, organization_id: str, campaign_id=None):
        return product_url

    monkeypatch.setattr(provider, "_fetch_suggested_price", fake_fetch_suggested_price)
    monkeypatch.setattr(provider, "_generate_affiliate_link", fake_generate_affiliate_link)

    item = {
        "organizationId": "org-1",
        "id": "1027452",
        "available": True,
        "name": "Ar Condicionado 12.000 Lg Dual Inverter Voice Q/f - PC / 2",
        "url": "https://example.com/ar-condicionado",
        "images": [{"url": "https://example.com/img.png"}],
        "options": [
            {
                "available": True,
                "pricing": [{"listPrice": 5950.22, "price": 5355.2, "metadata": []}],
                "images": [{"url": "https://example.com/img.png"}],
            }
        ],
    }

    offer = await provider._parse_product(item)

    assert offer is not None
    assert offer.final_price == 5355.2
    assert offer.original_price == 5950.22
    assert offer.affiliate_url == "https://example.com/ar-condicionado"