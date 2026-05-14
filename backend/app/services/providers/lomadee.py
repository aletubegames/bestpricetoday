"""Lomadee Affiliate Provider — API Beta v2
Docs: https://docs.lomadee.com.br
Base: https://api-beta.lomadee.com.br/affiliate

Fluxo correto:
1. GET /affiliate/products?search=query  -> lista produtos
2. POST /affiliate/shortener/url         -> gera link afiliado rastreado
3. Usa link rastreado no botão "Ver oferta"
"""
import httpx
from typing import List, Optional
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings
from app.core.logging import logger
import asyncio


class LomadeeProvider(BaseProvider):
    name = "lomadee"
    BASE_URL = "https://api-beta.lomadee.com.br/affiliate"
    CHANNEL_ID = "6ff2699e-ceaa-4fad-a58a-8b91f885485f"

    def __init__(self):
        super().__init__()
        self._catalog_access: Optional[bool] = None

    # Preços sugeridos de referência (MSRP) para calcular desconto real
    # quando a fonte não fornece preço original
    MSRP_REF = {
        # Samsung Galaxy
        "galaxy a05": 799, "galaxy a05s": 899,
        "galaxy a12": 599, "galaxy a13": 649,
        "galaxy a14": 699, "galaxy a15": 649,
        "galaxy a16": 1299, "galaxy a25": 1499,
        "galaxy a34": 1799, "galaxy a35": 1999,
        "galaxy a54": 2499, "galaxy a55": 2799,
        "galaxy s23": 3999, "galaxy s24": 4499,
        # Motorola
        "moto e22": 899, "moto e32": 999, "moto g14": 1099,
        "moto g24": 1299, "moto g34": 1499, "moto g54": 1799,
        "moto g84": 2299, "edge 40": 2799,
        # Notebooks
        "chromebook": 1799, "notebook samsung": 2999,
        "notebook lenovo": 2499, "notebook dell": 3499,
        # Fones
        "buds2": 599, "buds pro": 899, "buds live": 699,
        "fone bluetooth": 299,
        # TVs
        "smart tv 32": 1299, "smart tv 43": 1999, "smart tv 50": 2799,
        "smart tv 55": 3499,
    }

    def _get_msrp(self, title: str, price: float) -> Optional[float]:
        """Retorna preço sugerido de referência se houver, mínimo 10% acima do preco atual."""
        t = title.lower()
        for key, msrp in self.MSRP_REF.items():
            if key in t:
                if msrp > price * 1.10:
                    return float(msrp)
        return None

    async def _fetch_suggested_price(self, product_url: str, current_price: float) -> Optional[float]:
        """Tenta buscar preço original/sugerido na página do produto para calcular desconto real."""
        if not product_url:
            return None
        try:
            client = await self.get_client()
            resp = await client.get(product_url, timeout=5,
                                    headers={"User-Agent": "Mozilla/5.0 Chrome/120.0"})
            if resp.status_code != 200:
                return None
            import re
            html = resp.text
            # Procura por "preço de" / "de:" / "price" no HTML
            patterns = [
                r'"listPrice"\s*:\s*"?([\d.,]+)"?',
                r'"originalPrice"\s*:\s*"?([\d.,]+)"?',
                r'class="[^"]*(?:list|original|de|from)[^"]*"[^>]*>\s*R\$\s*([\d.,]+)',
                r'(?:de|por|from|list)[^\d]{0,10}([\d]{2,4}[,.]\d{2})',
            ]
            for pat in patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    val_str = m.group(1).replace(".", "").replace(",", ".")
                    try:
                        val = float(val_str)
                        if val > current_price * 1.05:  # pelo menos 5% maior
                            return round(val, 2)
                    except:
                        continue
        except Exception:
            pass
        return None

    def _build_affiliate_url(self, product_url: str) -> str:
        """Gera link de afiliado Lomadee com sourceId para rastreamento de comissão."""
        if not product_url:
            return ""
        sep = "&" if "?" in product_url else "?"
        return f"{product_url}{sep}utm_source=lomadee&utm_medium=affiliate&sourceId={self.CHANNEL_ID}"

    async def _generate_affiliate_link(
        self,
        product_url: str,
        organization_id: Optional[str],
        campaign_id: Optional[str] = None,
    ) -> Optional[str]:
        """Retorna link de afiliado com sourceId para rastreamento Lomadee."""
        return self._build_affiliate_url(product_url)

    async def _has_catalog_access(self) -> bool:
        if self._catalog_access is not None:
            return self._catalog_access

        try:
            client = await self.get_client()
            resp = await client.get(
                f"{self.BASE_URL}/products",
                params={"limit": 1, "page": 1},
                headers={"x-api-key": settings.LOMADEE_API_KEY},
            )
            resp.raise_for_status()
            self._catalog_access = bool((resp.json().get("data") or []))
        except Exception:
            self._catalog_access = False

        return self._catalog_access

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.LOMADEE_API_KEY:
            self.set_status(
                ProviderSearchState.not_configured,
                message="LOMADEE_API_KEY não configurada.",
            )
            logger.warning("Lomadee: LOMADEE_API_KEY not configured, skipping")
            return []
        try:
            client = await self.get_client()
            resp = await client.get(
                f"{self.BASE_URL}/products",
                params={
                    "search": query,
                    "limit": min(limit, 20),
                    "page": 1,
                    "isAvailable": True,
                },
                headers={"x-api-key": settings.LOMADEE_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            products = data.get("data", [])
            raw_count = int(data.get("count") or (data.get("meta") or {}).get("total") or len(products))

            if not products:
                has_catalog_access = await self._has_catalog_access()
                self.set_status(
                    ProviderSearchState.no_results,
                    message=(
                        "Lomadee respondeu 200, mas não encontrou produtos compatíveis no catálogo acessível."
                        if has_catalog_access
                        else "Lomadee respondeu 200, mas a conta não expõe catálogo acessível."
                    ),
                    http_status=resp.status_code,
                    raw_count=raw_count,
                )
                return []

            # Gera links afiliados em paralelo (max 5 por vez)
            offers = await self._parse_with_links(products[:limit])
            valid_offers = [o for o in offers if o.price]

            self.set_status(
                ProviderSearchState.ok if valid_offers else ProviderSearchState.no_results,
                message=(
                    f"Lomadee retornou {len(valid_offers)} ofertas."
                    if valid_offers
                    else "Lomadee retornou produtos, mas nenhum pôde ser convertido em oferta válida."
                ),
                http_status=resp.status_code,
                raw_count=raw_count,
                returned_count=len(valid_offers),
            )
            return valid_offers
        except Exception as e:
            self.set_status(ProviderSearchState.error, message=f"Lomadee falhou: {e}")
            logger.error(f"Lomadee search error: {e}")
            return []

    async def _parse_with_links(self, products: list) -> List[OfferSchema]:
        """Parse produtos e gera links afiliados em paralelo."""
        tasks = [self._parse_product(item) for item in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        offers = []
        for r in results:
            if isinstance(r, OfferSchema):
                offers.append(r)
        return offers

    async def _parse_product(self, item: dict) -> Optional[OfferSchema]:
        try:
            if not item.get("available", True):
                return None

            # Melhor opção disponível
            options = item.get("options", [])
            best_opt = None
            best_price = float("inf")
            for opt in options:
                if not opt.get("available", True):
                    continue
                pricing = opt.get("pricing", [])
                if pricing:
                    p = pricing[0].get("price", 0)
                    if p and p < best_price:
                        best_price = p
                        best_opt = opt

            if not best_opt and options:
                best_opt = options[0]

            # Preco ja vem em reais
            pricing = (best_opt or {}).get("pricing", [{}])
            price_raw = pricing[0].get("price", 0) if pricing else 0
            list_raw  = pricing[0].get("listPrice", price_raw) if pricing else price_raw
            price      = round(float(price_raw), 2) if price_raw else None
            list_price = round(float(list_raw), 2) if list_raw else None

            # Lomadee freq. retorna listPrice == price (sem desconto na fonte)
            # Tenta scraping da página, depois MSRP de referência
            if not list_price or list_price <= price:
                product_url_tmp = item.get("url", "")
                list_price = await self._fetch_suggested_price(product_url_tmp, price)
            if not list_price or list_price <= price:
                list_price = self._get_msrp(item.get("name", ""), price)

            if not price:
                return None

            discount = 0
            economy  = 0
            if list_price and list_price > price:
                discount = round((1 - price / list_price) * 100, 1)
                economy  = round(list_price - price, 2)

            # Imagem
            images = item.get("images", []) or (best_opt or {}).get("images", [])
            image_url = images[0].get("url", "") if images else ""

            # URL do produto
            product_url = item.get("url", "")
            organization_id = item.get("organizationId", "")

            # Gera link afiliado rastreado
            affiliate_url = await self._generate_affiliate_link(product_url, organization_id)
            if not affiliate_url:
                affiliate_url = product_url  # fallback para URL direta

            return OfferSchema(
                provider=ProviderEnum.lomadee,
                title=item.get("name", ""),
                price=price,
                original_price=list_price,
                discount_percent=discount,
                shipping_free=False,
                shipping_price=0,
                final_price=price,
                product_id=str(item.get("id", "")),
                product_url=product_url,
                affiliate_url=affiliate_url,
                tracking_id=self.CHANNEL_ID,
                image_url=image_url,
                economy=economy,
                coupon_discount=0,
                cashback_percent=0,
                is_fake_discount=discount > 80,
            )
        except Exception as e:
            logger.error(f"Lomadee parse product error: {e}")
            return None
