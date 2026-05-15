"""
Shopee Affiliate Open Platform — Client de Integração

API: GraphQL via https://open-api.affiliate.shopee.com.br/graphql
Autenticação: HMAC-SHA256 via header Authorization

Header:
  Authorization: SHA256 Credential={app_id},Timestamp={ts},Signature={sig}

Assinatura:
  sig = HMAC-SHA256(app_secret, f"{app_id}{timestamp}")

Endpoints implementados:
  - busca de produtos (productOfferV2)
  - hot products / lista de destaque
  - geração de link afiliado (generateShortLink)
  - consulta de cupons de loja
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.integrations.base import MarketplaceClient, MarketplaceId, ProductResult, CouponResult


GRAPHQL_ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

# Tipos de lista para productOfferV2
LIST_TYPE_SEARCH    = 0   # busca por keyword
LIST_TYPE_SIMILAR   = 1   # produtos similares
LIST_TYPE_BESTSELLER = 3  # mais vendidos

# Tipos de ordenação
SORT_RELEVANCE  = 1
SORT_PRICE_ASC  = 2
SORT_SALES_DESC = 3
SORT_NEWEST     = 5


class ShopeeSigner:
    """
    Gera o header de autenticação para a API Shopee Affiliate.

    Formato do header:
      SHA256 Credential={app_id},Timestamp={ts},Signature={sig}

    Assinatura:
      HMAC-SHA256(app_secret, "{app_id}{timestamp}")
    """

    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret

    def auth_header(self) -> str:
        ts = str(int(time.time()))
        sign_str = f"{self.app_id}{ts}"
        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"SHA256 Credential={self.app_id},Timestamp={ts},Signature={signature}"


class ShopeeClient(MarketplaceClient):
    """
    Cliente para Shopee Affiliate API (GraphQL).
    """
    marketplace_id = MarketplaceId.shopee
    timeout = 10

    def __init__(self) -> None:
        super().__init__()
        self._signer: Optional[ShopeeSigner] = None

    def _get_signer(self) -> Optional[ShopeeSigner]:
        if not settings.SHOPEE_APP_ID or not settings.SHOPEE_SECRET:
            return None
        if self._signer is None:
            self._signer = ShopeeSigner(
                app_id=settings.SHOPEE_APP_ID,
                app_secret=settings.SHOPEE_SECRET,
            )
        return self._signer

    def _is_configured(self) -> bool:
        return bool(settings.SHOPEE_APP_ID and settings.SHOPEE_SECRET)

    async def _execute(self, query: str, variables: Dict[str, Any]) -> dict:
        """Executa uma query GraphQL autenticada."""
        signer = self._get_signer()
        if not signer:
            raise RuntimeError("Shopee não configurado (APP_ID/SECRET ausentes)")

        client = await self._get_client()
        resp = await client.post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": signer.auth_header(),
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ── Parsers ──────────────────────────────

    def _parse_product_nodes(self, nodes: List[dict]) -> List[ProductResult]:
        results: List[ProductResult] = []
        for item in nodes:
            price = float(item.get("priceMin", 0) or 0)
            if not price:
                continue

            price_max = float(item.get("priceMax", price) or price)
            cashback = float(item.get("commissionRate", 0) or 0)

            results.append(ProductResult(
                marketplace=MarketplaceId.shopee,
                external_id=str(item.get("itemId", "")),
                title=item.get("productName", ""),
                price=price,
                original_price=price_max if price_max > price else None,
                discount_pct=0.0,
                currency="BRL",
                image_url=item.get("imageUrl", ""),
                product_url=item.get("productLink", item.get("offerLink", "")),
                affiliate_url=item.get("offerLink", ""),
                shipping_free=True,   # Shopee frequentemente oferece frete grátis
                shipping_price=0.0,
                cashback_pct=cashback,
                sales_count=int(item.get("sales", 0) or 0),
                extra={
                    "shop_name":   item.get("shopName", ""),
                    "commission":  cashback,
                },
            ))

        return results

    # ── Endpoints públicos ────────────────────

    async def search(self, query: str, limit: int = 10) -> List[ProductResult]:
        """
        Busca produtos por keyword.

        Usa: productOfferV2 (listType=0)
        """
        if not self._is_configured():
            return []

        gql = """
        query searchProducts($keyword: String!, $limit: Int!, $sortType: Int!) {
          productOfferV2(
            listType: 0
            sortType: $sortType
            limit: $limit
            keyword: $keyword
          ) {
            nodes {
              itemId
              productName
              priceMin
              priceMax
              imageUrl
              shopName
              offerLink
              productLink
              commissionRate
              sales
            }
          }
        }
        """

        try:
            data = await self._execute(gql, {
                "keyword":  query,
                "limit":    min(limit, 50),
                "sortType": SORT_RELEVANCE,
            })
            nodes = (
                data.get("data", {})
                    .get("productOfferV2", {})
                    .get("nodes", [])
            )
            results = self._parse_product_nodes(nodes)
            logger.info(f"Shopee search '{query}': {len(results)} results")
            return results[:limit]

        except Exception as e:
            logger.error(f"Shopee search error: {e}")
            return []

    async def get_hot_products(self, limit: int = 20) -> List[ProductResult]:
        """
        Retorna produtos mais vendidos.

        Usa: productOfferV2 (listType=3 bestseller)
        """
        if not self._is_configured():
            return []

        gql = """
        query hotProducts($limit: Int!) {
          productOfferV2(
            listType: 3
            sortType: 3
            limit: $limit
          ) {
            nodes {
              itemId
              productName
              priceMin
              priceMax
              imageUrl
              shopName
              offerLink
              commissionRate
              sales
            }
          }
        }
        """

        try:
            data = await self._execute(gql, {"limit": min(limit, 50)})
            nodes = (
                data.get("data", {})
                    .get("productOfferV2", {})
                    .get("nodes", [])
            )
            return self._parse_product_nodes(nodes)
        except Exception as e:
            logger.error(f"Shopee hot products error: {e}")
            return []

    async def get_affiliate_link(self, product_url: str, **kwargs) -> str:
        """
        Gera link de afiliado rastreado.

        Usa: generateShortLink (mutation)
        """
        if not self._is_configured():
            return product_url

        gql = """
        mutation generateLink($originalUrl: String!) {
          generateShortLink(input: { originUrl: $originalUrl }) {
            shortLink
            longLink
          }
        }
        """

        try:
            data = await self._execute(gql, {"originalUrl": product_url})
            result = data.get("data", {}).get("generateShortLink", {})
            return result.get("shortLink") or result.get("longLink") or product_url
        except Exception as e:
            logger.warning(f"Shopee affiliate link generation failed: {e}")
            return product_url

    async def get_coupons(self, store: str = "") -> List[CouponResult]:
        """
        Retorna vouchers/cupons disponíveis.

        Usa: shopVoucherV2
        """
        if not self._is_configured():
            return []

        gql = """
        query getVouchers($limit: Int!) {
          shopVoucherV2(limit: $limit) {
            nodes {
              voucherCode
              discountValue
              discountType
              minimumSpend
              startTime
              endTime
              shopName
            }
          }
        }
        """

        try:
            data = await self._execute(gql, {"limit": 50})
            nodes = (
                data.get("data", {})
                    .get("shopVoucherV2", {})
                    .get("nodes", [])
            )
            return [
                CouponResult(
                    marketplace=MarketplaceId.shopee,
                    code=v.get("voucherCode", ""),
                    description=f"Cupom {v.get('shopName', 'Shopee')}",
                    discount_type="percent" if v.get("discountType") == 1 else "fixed",
                    discount_value=float(v.get("discountValue", 0) or 0),
                    min_purchase=float(v.get("minimumSpend", 0) or 0),
                    store=v.get("shopName", "shopee"),
                    valid_until=v.get("endTime"),
                )
                for v in nodes if v.get("voucherCode")
            ]
        except Exception as e:
            logger.warning(f"Shopee coupons error: {e}")
            return []
