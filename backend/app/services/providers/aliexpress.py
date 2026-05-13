"""AliExpress Portals Affiliate Provider.

Sem App Key: gera links de afiliado via deep link do portal.
Com App Key (Open Platform): usa API completa.
"""
import time
import hashlib
import re
import unicodedata
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings
from app.core.logging import logger


class AliExpressProvider(BaseProvider):
    name = "aliexpress"
    BASE_URL = "https://api-sg.aliexpress.com/sync"
    METHOD = "aliexpress.affiliate.product.query"
    PORTAL_SEARCH = "https://portals.aliexpress.com/appPortal/api/affiliate/product/query"
    STOPWORDS = {
        "de", "da", "do", "das", "dos", "para", "com", "sem", "and", "the",
        "uma", "um", "por", "na", "no", "em", "new", "original", "plus",
    }
    ACCESSORY_KEYWORDS = {
        "case", "cover", "capa", "capinha", "caixa", "pelicula", "película", "film", "glass",
        "sticker", "adesivo", "decal", "pin", "badge", "bracelet", "bracelete",
        "pulseira", "strap", "shell", "housing", "keychain", "chaveiro",
    }

    def _sign_request(self, params: dict) -> str:
        sorted_params = sorted(params.items())
        sign_str = settings.ALIEXPRESS_APP_SECRET + "".join(f"{k}{v}" for k, v in sorted_params) + settings.ALIEXPRESS_APP_SECRET
        return hashlib.md5(sign_str.encode()).hexdigest().upper()

    def _build_affiliate_link(self, product_id: str) -> str:
        tracking = settings.ALIEXPRESS_TRACKING_ID or "bestpricetoday"
        return f"https://s.click.aliexpress.com/e/_oFnMhD7?bz={product_id}&dl=https%3A%2F%2Fwww.aliexpress.com%2Fitem%2F{product_id}.html&aff_fcid={tracking}"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        raw_offers: List[OfferSchema] = []
        last_error = None

        if settings.ALIEXPRESS_APP_KEY:
            try:
                raw_offers = await self._search_api(query, limit)
            except Exception as e:
                last_error = e
                logger.error(f"AliExpress API error: {e}")

        if not raw_offers:
            try:
                raw_offers = await self._search_portal(query, limit)
            except Exception as e:
                last_error = e
                logger.error(f"AliExpress portal fallback error: {e}")

        if not raw_offers:
            self.set_status(
                ProviderSearchState.error if last_error else ProviderSearchState.no_results,
                message=(
                    f"AliExpress falhou: {last_error}"
                    if last_error
                    else "AliExpress não retornou produtos para esta busca."
                ),
            )
            return []

        relevant_offers = self._filter_relevant_offers(query, raw_offers)
        filtered_count = max(0, len(raw_offers) - len(relevant_offers))

        if not relevant_offers:
            self.set_status(
                ProviderSearchState.low_relevance,
                message=(
                    f"AliExpress retornou {len(raw_offers)} itens, mas todos pareceram acessórios ou resultados pouco relevantes."
                ),
                raw_count=len(raw_offers),
                filtered_count=filtered_count,
            )
            return []

        message = f"AliExpress retornou {len(relevant_offers)} itens relevantes."
        if filtered_count:
            message += f" {filtered_count} itens irrelevantes foram filtrados."

        self.set_status(
            ProviderSearchState.ok,
            message=message,
            raw_count=len(raw_offers),
            returned_count=len(relevant_offers),
            filtered_count=filtered_count,
        )
        return relevant_offers[:limit]

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower().strip())
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _tokens(self, text: str) -> List[str]:
        tokens = re.findall(r"[a-z0-9]+", self._normalize_text(text))
        return [token for token in tokens if len(token) > 1 and token not in self.STOPWORDS]

    def _contains_accessory_term(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        return any(keyword in normalized for keyword in self.ACCESSORY_KEYWORDS)

    def _is_relevant_offer(self, query: str, title: str) -> bool:
        query_tokens = self._tokens(query)
        title_tokens = set(self._tokens(title))
        if not query_tokens or not title_tokens:
            return False

        numeric_tokens = [token for token in query_tokens if token.isdigit()]
        if numeric_tokens and not all(token in title_tokens for token in numeric_tokens):
            return False

        overlap = [token for token in query_tokens if token in title_tokens]
        min_overlap = 1 if len(query_tokens) < 3 else 2
        if len(overlap) < min_overlap:
            return False

        if self._contains_accessory_term(title) and not self._contains_accessory_term(query):
            return False

        return True

    def _filter_relevant_offers(self, query: str, offers: List[OfferSchema]) -> List[OfferSchema]:
        return [offer for offer in offers if self._is_relevant_offer(query, offer.title)]

    async def _search_portal(self, query: str, limit: int) -> List[OfferSchema]:
        """Busca via portal de afiliados (sem app_key)."""
        try:
            client = await self.get_client()
            resp = await client.get(
                self.PORTAL_SEARCH,
                params={
                    "keywords": query,
                    "pageSize": min(limit, 20),
                    "pageNo": 1,
                    "currency": "BRL",
                    "country": "BR",
                    "language": "PT",
                    "trackingId": settings.ALIEXPRESS_TRACKING_ID or "bestpricetoday",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    "Referer": "https://portals.aliexpress.com",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("result", {}).get("productList", data.get("data", {}).get("products", []))
                if products:
                    return self._parse_portal(products)
        except Exception as e:
            logger.error(f"AliExpress portal error: {e}")

        logger.warning("AliExpress: portal indisponível ou sem resultados, skipping")
        return []

    def _parse_portal(self, products: list) -> List[OfferSchema]:
        offers = []
        for item in products:
            price = float(item.get("salePrice", item.get("originalPrice", 0)) or 0)
            original = float(item.get("originalPrice", price) or price)
            discount = round((1 - price / original) * 100, 1) if original > price and price > 0 else 0
            pid = str(item.get("productId", ""))
            offers.append(OfferSchema(
                provider=ProviderEnum.aliexpress,
                title=item.get("productTitle", item.get("title", "")),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=True,
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("promotionLink", self._build_affiliate_link(pid)),
                image_url=item.get("imageUrl", item.get("productMainImageUrl", "")),
                economy=original - price if original > price else 0,
                coupon_discount=0,
                cashback_percent=0,
                is_fake_discount=False,
            ))
        return offers

    def _guess_category(self, query: str) -> str:
        """Mapeia keywords para category_ids do AliExpress para melhorar relevância."""
        q = query.lower()
        if any(w in q for w in ["smartphone", "celular", "iphone", "galaxy", "redmi", "xiaomi", "motorola"]):
            return "200000340"  # Phones & Telecommunications
        if any(w in q for w in ["notebook", "laptop", "macbook"]):
            return "200000352"  # Computer & Office
        if any(w in q for w in ["tablet", "ipad"]):
            return "200000344"  # Tablets
        if any(w in q for w in ["fone", "headphone", "earphone", "airpod", "tws"]):
            return "200000346"  # Consumer Electronics > Audio
        if any(w in q for w in ["smartwatch", "relogio", "relógio", "watch"]):
            return "200003655"  # Watches
        if any(w in q for w in ["tv", "televisao", "televisão", "monitor"]):
            return "200000350"  # TV & Video
        if any(w in q for w in ["camera", "câmera", "fotografia"]):
            return "200000351"  # Camera & Photo
        if any(w in q for w in ["ar condicionado", "geladeira", "eletrodomestico"]):
            return "200001075"  # Home Appliances
        return ""  # sem filtro de categoria

    async def _search_api(self, query: str, limit: int) -> List[OfferSchema]:
        timestamp = str(int(time.time() * 1000))
        params = {
            "app_key": settings.ALIEXPRESS_APP_KEY,
            "method": self.METHOD,
            "timestamp": timestamp,
            "format": "json",
            "v": "2.0",
            "sign_method": "md5",
            "keywords": query,
            "page_size": str(min(limit, 50)),
            "page_no": "1",
            "sort": "LAST_VOLUME_DESC",
            "target_currency": "BRL",
            "target_language": "PT",
            "ship_to_country": "BR",
            "min_sale_price": "50",
        }
        cat = self._guess_category(query)
        if cat:
            params["category_ids"] = cat
        # tracking_id é opcional — não enviar se vazio (causa erro 402)
        if settings.ALIEXPRESS_TRACKING_ID:
            params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID
        params["sign"] = self._sign_request(params)
        client = await self.get_client()
        resp = await client.post(self.BASE_URL, data=params)
        resp.raise_for_status()
        data = resp.json()
        return self._parse_api(data)

    def _parse_api(self, data: dict) -> List[OfferSchema]:
        offers = []
        result = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
        if result.get("resp_code") != 200:
            return []
        products = result.get("result", {}).get("products", {}).get("product", [])
        for item in products:
            price = float(item.get("target_sale_price", 0))
            original = float(item.get("target_original_price") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0
            offers.append(OfferSchema(
                provider=ProviderEnum.aliexpress,
                title=item.get("product_title", ""),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=True,
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("promotion_link", item.get("product_detail_url", "")),
                image_url=item.get("product_main_image_url", ""),
                economy=original - price if original > price else 0,
                coupon_discount=0,
                cashback_percent=0,
                is_fake_discount=False,
            ))
        return offers
