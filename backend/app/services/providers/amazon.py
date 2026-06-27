"""Amazon Provider — 3 modos de operação:

1. PA-API ativa (AMAZON_ACCESS_KEY preenchida) → busca via API oficial
2. Scraper local (produtos na tabela affiliate_products) → busca no banco
3. Fallback → gera link de busca com tag de afiliado (sem preço, mas rastreia comissão)

O modo 3 garante que sempre haja um resultado da Amazon, mesmo sem API ou scraper.
"""
import hmac
import hashlib
import datetime
from datetime import timezone as _tz
import json
import re
import unicodedata
import urllib.parse
from typing import List, Optional
import httpx
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings
from app.core.logging import logger


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokenize(query: str) -> list[str]:
    tokens = re.findall(r"\w+", _normalize(query))
    return [t for t in tokens if len(t) > 2]


def _score(title: str, tokens: list[str]) -> float:
    if not tokens:
        return 1.0
    norm = _normalize(title)
    hits = sum(1 for t in tokens if t in norm)
    return hits / len(tokens)


class AmazonProvider(BaseProvider):
    name = "amazon"
    SERVICE = "ProductAdvertisingAPI"
    REGION = "us-east-1"
    HOST = "webservices.amazon.com.br"
    PATH = "/paapi5/searchitems"

    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signature_key(self, date_stamp: str) -> bytes:
        k_date = self._sign(("AWS4" + settings.AMAZON_SECRET_KEY).encode("utf-8"), date_stamp)
        k_region = self._sign(k_date, self.REGION)
        k_service = self._sign(k_region, self.SERVICE)
        return self._sign(k_service, "aws4_request")

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        # Modo 1: PA-API oficial (se credenciais completas)
        if settings.AMAZON_ACCESS_KEY and settings.AMAZON_SECRET_KEY:
            try:
                offers = await self._do_search_api(query, limit)
                if offers:
                    self.set_status(
                        ProviderSearchState.ok,
                        message=f"Amazon PA-API: {len(offers)} ofertas.",
                        raw_count=len(offers),
                        returned_count=len(offers),
                    )
                    return offers
                # Se API não retornou, cai para modo 2/3
            except Exception as e:
                logger.warning(f"Amazon PA-API falhou: {e}")

        # Modo 2: Scraper local (produtos na tabela affiliate_products)
        offers = await self._local_search(query, limit)
        if offers:
            self.set_status(
                ProviderSearchState.ok,
                message=f"Amazon (scraper local): {len(offers)} ofertas.",
                raw_count=len(offers),
                returned_count=len(offers),
            )
            return offers

        # Modo 3: Fallback — gera link de busca com tag de afiliado
        # Sem preço/imagem, mas rastreia comissão (24h cookie)
        if settings.AMAZON_PARTNER_TAG:
            search_link = self._build_search_link(query)
            fallback_offer = OfferSchema(
                provider=ProviderEnum.amazon,
                title=f"Ver ofertas de '{query}' na Amazon",
                price=0,
                original_price=0,
                discount_percent=0,
                shipping_free=True,
                shipping_price=0,
                final_price=0,
                score=50,
                product_id="",
                product_url=search_link,
                affiliate_url=search_link,
                image_url="",
            )
            self.set_status(
                ProviderSearchState.ok,
                message="Amazon: link de busca (sem catálogo local, rastreia comissão).",
                raw_count=1,
                returned_count=1,
            )
            return [fallback_offer]

        self.set_status(
            ProviderSearchState.not_configured,
            message="Amazon: AMAZON_PARTNER_TAG não configurado.",
        )
        return []

    def _build_search_link(self, query: str) -> str:
        """Gera URL de busca da Amazon com tag de afiliado."""
        encoded = urllib.parse.quote_plus(query)
        return f"https://www.amazon.com.br/s?k={encoded}&tag={settings.AMAZON_PARTNER_TAG}"

    async def _local_search(self, query: str, limit: int) -> List[OfferSchema]:
        """Busca produtos Amazon na tabela affiliate_products (do scraper)."""
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.models import AffiliateProduct
            from sqlalchemy import select, or_, and_, func

            tokens = _tokenize(query)

            async with AsyncSessionLocal() as db:
                if tokens:
                    # AND: todos tokens devem aparecer no título
                    token_filters = [
                        or_(
                            func.lower(AffiliateProduct.title).like(f"%{t}%"),
                            func.lower(AffiliateProduct.category).like(f"%{t}%"),
                        )
                        for t in tokens
                    ]
                    # Só produtos Amazon (notes contém 'source=amazon_scraper')
                    where_clause = and_(
                        *token_filters,
                        func.lower(AffiliateProduct.notes).like("%amazon_scraper%"),
                    )
                else:
                    where_clause = and_(
                        func.lower(AffiliateProduct.notes).like("%amazon_scraper%"),
                    )

                stmt = (
                    select(AffiliateProduct)
                    .where(
                        AffiliateProduct.is_active == True,
                        AffiliateProduct.title != None,
                        where_clause,
                    )
                    .limit(limit * 3)
                )
                result = await db.execute(stmt)
                products = result.scalars().all()

            if not products:
                return []

            # Filtra por score mínimo e ordena
            min_score = 0.5 if len(tokens) > 1 else 0.0
            scored = sorted(
                products,
                key=lambda p: _score(p.title or "", tokens),
                reverse=True,
            )
            scored = [p for p in scored if _score(p.title or "", tokens) >= min_score][:limit]

            offers = []
            for p in scored:
                price = p.price or 0
                # Verifica se é Prime
                is_prime = "prime=true" in (p.notes or "")
                offers.append(OfferSchema(
                    provider=ProviderEnum.amazon,
                    title=p.title or "",
                    price=price,
                    original_price=price,
                    discount_percent=0.0,
                    shipping_free=is_prime,
                    shipping_price=0.0 if is_prime else 20.0,
                    final_price=price + (0 if is_prime else 20.0),
                    score=round(_score(p.title or "", tokens), 4),
                    product_id=p.ml_code or "",
                    product_url=p.affiliate_url or "",
                    affiliate_url=p.affiliate_url or "",
                    image_url=p.image_url or "",
                    economy=0.0,
                ))

            return offers

        except Exception as e:
            logger.error(f"Amazon local search error: {e}")
            return []

    async def _do_search_api(self, query: str, limit: int) -> List[OfferSchema]:
        """Busca via Product Advertising API v5 (requer credenciais AWS)."""
        now = datetime.datetime.now(_tz.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        payload = {
            "Keywords": query,
            "Marketplace": "www.amazon.com.br",
            "PartnerTag": settings.AMAZON_PARTNER_TAG,
            "PartnerType": "Associates",
            "Resources": [
                "Images.Primary.Medium",
                "ItemInfo.Title",
                "Offers.Listings.Price",
                "Offers.Listings.DeliveryInfo.IsFreeShippingEligible",
                "Offers.Summaries.LowestPrice",
            ],
            "SearchIndex": "All",
            "ItemCount": min(limit, 10),
            "SortBy": "Price:LowToHigh",
        }

        payload_str = json.dumps(payload)
        headers = {
            "content-encoding": "amz-1.0",
            "content-type": "application/json; charset=utf-8",
            "host": self.HOST,
            "x-amz-date": amz_date,
            "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
        }

        canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(headers.items()))
        signed_headers = ";".join(sorted(headers.keys()))
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        canonical_request = "\n".join([
            "POST", self.PATH, "",
            canonical_headers, signed_headers, payload_hash
        ])

        credential_scope = f"{date_stamp}/{self.REGION}/{self.SERVICE}/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256", amz_date, credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest()
        ])

        sig_key = self._get_signature_key(date_stamp)
        signature = hmac.new(sig_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

        auth_header = (
            f"AWS4-HMAC-SHA256 Credential={settings.AMAZON_ACCESS_KEY}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        headers["Authorization"] = auth_header

        client = await self.get_client()
        resp = await client.post(
            f"https://{self.HOST}{self.PATH}",
            headers=headers,
            content=payload_str,
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_api(data)

    def _parse_api(self, data: dict) -> List[OfferSchema]:
        offers = []
        items = data.get("SearchResult", {}).get("Items", [])
        for item in items:
            title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "")
            image = item.get("Images", {}).get("Primary", {}).get("Medium", {}).get("URL", "")
            url = item.get("DetailPageURL", "")

            listings = item.get("Offers", {}).get("Listings", [])
            if not listings:
                continue
            listing = listings[0]
            price = listing.get("Price", {}).get("Amount", 0)
            free_ship = listing.get("DeliveryInfo", {}).get("IsFreeShippingEligible", False)
            shipping_cost = 0 if free_ship else 20.0

            offers.append(OfferSchema(
                provider=ProviderEnum.amazon,
                title=title,
                price=float(price),
                shipping_free=free_ship,
                shipping_price=shipping_cost,
                final_price=float(price) + shipping_cost,
                affiliate_url=url,
                image_url=image,
            ))
        return offers
