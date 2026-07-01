"""
AliExpress Open Platform — Client de Integração

Suporta dois protocolos:
  - TOP  (APIs legadas, método com ponto: aliexpress.affiliate.product.query)
  - GOP  (APIs novas, path com barra: /auth/token/create)

Autenticação:
  - app_key + app_secret
  - Assinatura HMAC-SHA256 (não MD5 como era no protocolo antigo)
  - sign_method=sha256

Endpoints implementados:
  - busca de produtos afiliados
  - hot products
  - detalhe de produto
  - geração de link afiliado (URL tracking)
  - consulta de cupons/promoções
"""
from __future__ import annotations

import hashlib
import hmac
import time
import re
import unicodedata
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.integrations.base import MarketplaceClient, MarketplaceId, ProductResult, CouponResult


# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────

TOP_ENDPOINT = "https://api-sg.aliexpress.com/sync"
GOP_ENDPOINT = "https://api-sg.aliexpress.com/rest"

# Mapeamento keyword → category_id para filtros mais precisos
CATEGORY_MAP: Dict[str, str] = {
    # Smartphones
    "smartphone": "200000340",
    "celular":    "200000340",
    "iphone":     "200000340",
    "galaxy":     "200000340",
    "redmi":      "200000340",
    "xiaomi":     "200000340",
    "motorola":   "200000340",
    "poco":       "200000340",
    # Computadores
    "notebook":   "200000352",
    "laptop":     "200000352",
    "macbook":    "200000352",
    "desktop":    "200000352",
    # Tablets
    "tablet":     "200000344",
    "ipad":       "200000344",
    # Áudio
    "fone":       "200000346",
    "headphone":  "200000346",
    "earphone":   "200000346",
    "airpod":     "200000346",
    "tws":        "200000346",
    "bluetooth":  "200000346",
    # Smartwatches
    "smartwatch": "200003655",
    "relogio":    "200003655",
    "watch":      "200003655",
    # TV e vídeo
    "tv":         "200000350",
    "televisao":  "200000350",
    "monitor":    "200000350",
    # Câmeras
    "camera":     "200000351",
    "fotografia": "200000351",
    "gopro":      "200000351",
    # Eletrodomésticos
    "geladeira":  "200001075",
    "microondas": "200001075",
    "lavadora":   "200001075",
    # Videogame
    "console":    "200000532",
    "playstation":"200000532",
    "xbox":       "200000532",
    "nintendo":   "200000532",
    # GPU / hardware
    "rtx":        "200000352",
    "rx ":        "200000352",
    "placa":      "200000352",
    "ssd":        "200000352",
    "ram":        "200000352",
    "processador":"200000352",
}

STOPWORDS = {
    "de", "da", "do", "das", "dos", "para", "com", "sem", "and", "the",
    "uma", "um", "por", "na", "no", "em", "new", "original", "plus", "o", "a",
}

# Palavras que indicam claramente produto acessório (capa, película, etc)
ACCESSORY_KEYWORDS = {
    # Capas / protetores para dispositivos
    "case", "cover", "capa", "capinha",
    "caixa de telefone", "caixa de celular",
    "bolso",
    "pelicula", "película", "tempered glass", "screen protector",
    "vidro temperado", "protetor de tela",
    # Decorativos puros
    "sticker", "adesivo", "decal",
    # Mouse pads
    "mouse pad", "mousepad",
    # Bolsas/mangas para laptop (quando query pede o notebook em si)
    "bolsa manga", "laptop bag", "notebook bag",
}

# Produtos que parecem acessório mas são standalone legítimos
# (pulseiras de relógio, cabos, carregadores, suportes, etc)
# NÃO filtrar como acessório.


# ─────────────────────────────────────────────
# Assinador de requisições
# ─────────────────────────────────────────────

class AliExpressSigner:
    """
    Gera assinaturas para requisições AliExpress Open Platform.

    Algoritmo comum (TOP e GOP):
      sign = HMAC-SHA256(key=app_secret, message=<string>).hexdigest().upper()

    Diferença entre protocolos:
      TOP  (Business Interface, método com ponto):
        message = sorted(k+v for k,v in all_params)   ← sem prefixo, método é parâmetro
      GOP  (System Interface, path com barra):
        message = api_path + sorted(k+v for k,v in all_params)  ← api_path prefixado

    Referência: https://openplatform.aliexpress.com/doc/doc.htm#/?docId=9871
    Vetores de teste (app_secret='helloworld'):
      TOP → F7F7926B67316C9D1E8E15F7E66940ED3059B1638C497D77973F30046EFB5BBB
      GOP → 35607762342831B6A417A0DED84B79C05FEFBF116969C48AD6DC00279A9F4D81
    """

    def __init__(self, app_key: str, app_secret: str) -> None:
        self.app_key = app_key
        self.app_secret = app_secret

    def _timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def sign_top(self, method: str, params: Dict[str, str]) -> Dict[str, str]:
        """
        Assina uma requisição TOP (protocolo legado com método pontilhado).

        Retorna dicionário completo de parâmetros prontos para envio.
        """
        full_params = {
            "app_key":     self.app_key,
            "method":      method,
            "timestamp":   self._timestamp(),
            "format":      "json",
            "v":           "2.0",
            "sign_method": "sha256",
            **params,
        }
        full_params["sign"] = self._compute_top_sign(full_params)
        return full_params

    def _compute_top_sign(self, params: Dict[str, str]) -> str:
        """
        Algoritmo de assinatura TOP (Business Interface):
          1. Ordenar todos os parâmetros por nome (ASCII)
             → inclui 'method' como parâmetro normal
          2. Concatenar: k1v1k2v2k3v3...
             → app_secret NÃO entra na string (é apenas a chave HMAC)
          3. HMAC-SHA256(key=app_secret, msg=string)
          4. HEX UPPERCASE
        """
        sorted_items = sorted(params.items())
        concat = "".join(f"{k}{v}" for k, v in sorted_items)
        return hmac.new(
            self.app_secret.encode("utf-8"),
            concat.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

    def sign_gop(self, api_path: str, params: Dict[str, str]) -> Dict[str, str]:
        """
        Assina uma requisição GOP (protocolo novo com path /xxx/yyy).

        Retorna dicionário completo de parâmetros.
        """
        full_params = {
            "app_key":     self.app_key,
            "timestamp":   self._timestamp(),
            "sign_method": "sha256",
            **params,
        }
        full_params["sign"] = self._compute_gop_sign(api_path, full_params)
        return full_params

    def _compute_gop_sign(self, api_path: str, params: Dict[str, str]) -> str:
        """
        Algoritmo de assinatura GOP (System Interface):
          1. Ordenar todos os parâmetros por nome (ASCII)
             → 'method' NÃO é parâmetro; api_path é prefixado na string
          2. Concatenar: api_path + k1v1k2v2k3v3...
             → app_secret NÃO entra na string (é apenas a chave HMAC)
          3. HMAC-SHA256(key=app_secret, msg=api_path+sorted_params)
          4. HEX UPPERCASE
        """
        sorted_items = sorted(params.items())
        concat = api_path + "".join(f"{k}{v}" for k, v in sorted_items)
        return hmac.new(
            self.app_secret.encode("utf-8"),
            concat.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()


# ─────────────────────────────────────────────
# Client principal
# ─────────────────────────────────────────────

class AliExpressClient(MarketplaceClient):
    """
    Cliente completo para AliExpress Open Platform.

    Usa o signer TOP/GOP para todos os endpoints.
    """
    marketplace_id = MarketplaceId.aliexpress
    timeout = 12

    def __init__(self) -> None:
        super().__init__()
        self._signer: Optional[AliExpressSigner] = None

    def _get_signer(self) -> Optional[AliExpressSigner]:
        if not settings.ALIEXPRESS_APP_KEY or not settings.ALIEXPRESS_APP_SECRET:
            return None
        if self._signer is None:
            self._signer = AliExpressSigner(
                app_key=settings.ALIEXPRESS_APP_KEY,
                app_secret=settings.ALIEXPRESS_APP_SECRET,
            )
        return self._signer

    def _is_configured(self) -> bool:
        return bool(settings.ALIEXPRESS_APP_KEY and settings.ALIEXPRESS_APP_SECRET)

    # ── Utilitários de texto ──────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFKD", text.lower().strip())
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _tokens(text: str) -> List[str]:
        normalized = AliExpressClient._normalize(text)
        return [t for t in re.findall(r"[a-z0-9]+", normalized)
                if len(t) > 1 and t not in STOPWORDS]

    @staticmethod
    def _guess_category(query: str) -> str:
        q = AliExpressClient._normalize(query)
        for keyword, cat_id in CATEGORY_MAP.items():
            if keyword in q:
                return cat_id
        return ""

    def _is_accessory(self, title: str) -> bool:
        normalized = self._normalize(title)
        return any(kw in normalized for kw in ACCESSORY_KEYWORDS)

    def _is_specific_product(self, query: str) -> bool:
        """True se a query parece ser um produto específico (ex: iphone, notebook, ps5)."""
        normalized = self._normalize(query)
        specific = {"iphone", "samsung", "notebook", "laptop", "ps5", "ps4", "xbox",
                    "macbook", "ipad", "tablet", "monitor", "tv", "celular", "smartphone",
                    "camera", "goPro", "console", "kindle"}
        return any(s in normalized for s in specific)

    def _is_relevant(self, query: str, title: str) -> bool:
        query_tokens = self._tokens(query)
        title_tokens = set(self._tokens(title))
        if not query_tokens or not title_tokens:
            return False

        # Tokens numéricos: exige que o número exato esteja presente
        # "rtx 4070" não aceita "rtx 4060"
        numeric = [t for t in query_tokens if t.isdigit() or re.match(r"^\d+gb$", t)]
        if numeric and not all(t in title_tokens for t in numeric):
            return False

        # Sobreposição mínima de tokens de texto (ignora numéricos para este check)
        text_query_tokens = [t for t in query_tokens if not t.isdigit() and not re.match(r"^\d+gb$", t)]
        if text_query_tokens:
            overlap = [t for t in text_query_tokens if t in title_tokens]
            min_overlap = 1  # pelo menos 1 token de texto em comum
            if len(overlap) < min_overlap:
                return False

        # Rejeita acessórios apenas para queries de produtos específicos
        # (ex: "iphone 15" não quer capas, mas "sapatos" pode querer palmilhas)
        if self._is_accessory(title) and self._is_specific_product(query):
            return False

        return True

    def _filter_relevant(self, query: str, results: List[ProductResult]) -> List[ProductResult]:
        """Filtra resultados relevantes. Fallback: retorna todos se nada passar."""
        relevant = [r for r in results if self._is_relevant(query, r.title)]
        if relevant:
            return relevant
        # Fallback: retorna todos os resultados sem filtro
        return results

    # ── Parsers ──────────────────────────────

    def _parse_top_products(self, data: dict) -> List[ProductResult]:
        """Parse resposta de aliexpress.affiliate.product.query (TOP)."""
        results: List[ProductResult] = []

        resp = data.get("aliexpress_affiliate_product_query_response", {})
        resp_result = resp.get("resp_result", {})

        if resp_result.get("resp_code") != 200:
            logger.warning(f"AliExpress TOP error: {resp_result.get('resp_msg')}")
            return []

        products = (
            resp_result.get("result", {})
            .get("products", {})
            .get("product", [])
        )

        for item in products:
            price = float(item.get("target_sale_price", 0) or 0)
            if not price:
                continue
            original = float(item.get("target_original_price") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0.0

            results.append(ProductResult(
                marketplace=MarketplaceId.aliexpress,
                external_id=str(item.get("product_id", "")),
                title=item.get("product_title", ""),
                price=price,
                original_price=original if original > price else None,
                discount_pct=discount,
                currency="BRL",
                image_url=item.get("product_main_image_url", ""),
                product_url=item.get("product_detail_url", ""),
                affiliate_url=item.get("promotion_link", ""),
                shipping_free=True,
                shipping_price=0.0,
                sales_count=int(item.get("lastest_volume", 0) or 0),
                extra={"commission_rate": item.get("commission_rate", "")},
            ))

        return results

    def _parse_hot_products(self, data: dict) -> List[ProductResult]:
        """Parse resposta de aliexpress.affiliate.hotproduct.query (TOP)."""
        results: List[ProductResult] = []

        resp = data.get("aliexpress_affiliate_hotproduct_query_response", {})
        resp_result = resp.get("resp_result", {})

        if resp_result.get("resp_code") != 200:
            return []

        products = (
            resp_result.get("result", {})
            .get("products", {})
            .get("product", [])
        )

        for item in products:
            price = float(item.get("target_sale_price", 0) or 0)
            if not price:
                continue
            original = float(item.get("target_original_price") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0.0

            results.append(ProductResult(
                marketplace=MarketplaceId.aliexpress,
                external_id=str(item.get("product_id", "")),
                title=item.get("product_title", ""),
                price=price,
                original_price=original if original > price else None,
                discount_pct=discount,
                currency="BRL",
                image_url=item.get("product_main_image_url", ""),
                product_url=item.get("product_detail_url", ""),
                affiliate_url=item.get("promotion_link", ""),
                shipping_free=True,
                shipping_price=0.0,
                sales_count=int(item.get("lastest_volume", 0) or 0),
            ))

        return results

    def _parse_product_detail(self, data: dict) -> Optional[ProductResult]:
        """Parse resposta de aliexpress.affiliate.product.detail.get (TOP)."""
        resp = data.get("aliexpress_affiliate_product_detail_get_response", {})
        resp_result = resp.get("resp_result", {})

        if resp_result.get("resp_code") != 200:
            return None

        item = resp_result.get("result", {})
        if not item:
            return None

        price = float(item.get("target_sale_price", 0) or 0)
        if not price:
            return None

        original = float(item.get("target_original_price") or price)
        discount = round((1 - price / original) * 100, 1) if original > price else 0.0

        return ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id=str(item.get("product_id", "")),
            title=item.get("product_title", ""),
            price=price,
            original_price=original if original > price else None,
            discount_pct=discount,
            currency="BRL",
            image_url=item.get("product_main_image_url", ""),
            product_url=item.get("product_detail_url", ""),
            affiliate_url=item.get("promotion_link", ""),
            shipping_free=True,
            shipping_price=0.0,
            rating=float(item.get("evaluate_rate", "0%").replace("%", "") or 0) / 100,
        )

    def _parse_affiliate_link(self, data: dict) -> Optional[str]:
        """Parse resposta de aliexpress.affiliate.link.generate (TOP)."""
        resp = data.get("aliexpress_affiliate_link_generate_response", {})
        resp_result = resp.get("resp_result", {})

        if resp_result.get("resp_code") != 200:
            return None

        links = (
            resp_result.get("result", {})
            .get("promotion_links", {})
            .get("promotion_link", [])
        )
        if links:
            return links[0].get("promotion_link", "")
        return None

    # ── Chamadas HTTP ─────────────────────────

    async def _call_top(self, method: str, params: Dict[str, Any]) -> dict:
        """Executa uma chamada ao endpoint TOP (sync)."""
        signer = self._get_signer()
        if not signer:
            raise RuntimeError("AliExpress não configurado (app_key/app_secret ausentes)")

        str_params = {k: str(v) for k, v in params.items()}
        signed = signer.sign_top(method, str_params)

        client = await self._get_client()
        resp = await client.post(TOP_ENDPOINT, data=signed)
        resp.raise_for_status()
        return resp.json()

    async def _call_gop(self, api_path: str, params: Dict[str, Any]) -> dict:
        """Executa uma chamada ao endpoint GOP (rest)."""
        signer = self._get_signer()
        if not signer:
            raise RuntimeError("AliExpress não configurado (app_key/app_secret ausentes)")

        str_params = {k: str(v) for k, v in params.items()}
        signed = signer.sign_gop(api_path, str_params)

        client = await self._get_client()
        resp = await client.post(f"{GOP_ENDPOINT}{api_path}", data=signed)
        resp.raise_for_status()
        return resp.json()

    # ── Endpoints públicos ────────────────────

    async def search(self, query: str, limit: int = 10) -> List[ProductResult]:
        """
        Busca produtos afiliados AliExpress.

        Usa: aliexpress.affiliate.product.query (TOP)
        Com filtro de categoria quando detectável e filtro de relevância.
        """
        if not self._is_configured():
            return []

        params: Dict[str, Any] = {
            "keywords":        query,
            "page_size":       str(min(limit * 2, 50)),   # busca mais para filtrar
            "page_no":         "1",
            "target_currency": "BRL",
            "ship_to_country": "BR",
        }

        if settings.ALIEXPRESS_TRACKING_ID:
            params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID

        data = await self._call_top("aliexpress.affiliate.product.query", params)

        # Se o tracking_id causou erro (resp_code 402), tenta sem ele
        resp_result = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
        if resp_result.get("resp_code") == 402 and "tracking_id" in params:
            logger.warning("AliExpress: tracking_id inválido, tentando sem tracking_id")
            params.pop("tracking_id")
            data = await self._call_top("aliexpress.affiliate.product.query", params)
            resp_result = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})

        # Se 405 (result is empty), tenta sem min_sale_price
        if resp_result.get("resp_code") == 405 and "min_sale_price" in params:
            logger.warning("AliExpress: 405 com min_sale_price, tentando sem filtro")
            params.pop("min_sale_price")
            data = await self._call_top("aliexpress.affiliate.product.query", params)

        raw = self._parse_top_products(data)
        relevant = self._filter_relevant(query, raw)

        logger.info(
            f"AliExpress search '{query}': {len(raw)} raw → {len(relevant)} relevant"
        )
        return relevant[:limit]

    async def get_hot_products(self, limit: int = 20) -> List[ProductResult]:
        """
        Retorna produtos em alta/promoção.

        Usa: aliexpress.affiliate.hotproduct.query (TOP)
        """
        if not self._is_configured():
            return []

        params: Dict[str, Any] = {
            "page_size":       str(min(limit, 50)),
            "page_no":         "1",
            "sort":            "LAST_VOLUME_DESC",
            "target_currency": "BRL",
            "ship_to_country": "BR",
        }

        if settings.ALIEXPRESS_TRACKING_ID:
            params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID

        data = await self._call_top("aliexpress.affiliate.hotproduct.query", params)
        return self._parse_hot_products(data)

    async def get_product_detail(self, product_id: str) -> Optional[ProductResult]:
        """
        Retorna detalhes completos de um produto.

        Usa: aliexpress.affiliate.product.detail.get (TOP)
        """
        if not self._is_configured():
            return None

        params: Dict[str, Any] = {
            "product_ids":     product_id,
            "target_currency": "BRL",
            "target_language": "PT",
            "ship_to_country": "BR",
        }

        if settings.ALIEXPRESS_TRACKING_ID:
            params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID

        data = await self._call_top("aliexpress.affiliate.product.detail.get", params)
        return self._parse_product_detail(data)

    async def get_affiliate_link(self, product_url: str, **kwargs) -> str:
        """
        Gera link de afiliado rastreado.

        Usa: aliexpress.affiliate.link.generate (TOP)
        Se falhar, usa fallback de deep link.
        """
        if not self._is_configured():
            return self._fallback_affiliate_link(product_url)

        params: Dict[str, Any] = {
            "source_values":    product_url,
            "promotion_link_type": "0",   # 0 = normal, 1 = hot
        }

        if settings.ALIEXPRESS_TRACKING_ID:
            params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID

        try:
            data = await self._call_top("aliexpress.affiliate.link.generate", params)
            link = self._parse_affiliate_link(data)
            if link:
                return link
        except Exception as e:
            logger.warning(f"AliExpress link generate failed, using fallback: {e}")

        return self._fallback_affiliate_link(product_url)

    def _fallback_affiliate_link(self, product_url: str) -> str:
        """Deep link de afiliado quando a API não responde."""
        tracking = settings.ALIEXPRESS_TRACKING_ID or "bestpricetoday"
        # Extrai product_id da URL se possível
        match = re.search(r"/item/(\d+)\.html", product_url)
        if match:
            pid = match.group(1)
            return (
                f"https://s.click.aliexpress.com/e/_oFnMhD7"
                f"?bz={pid}"
                f"&dl=https%3A%2F%2Fwww.aliexpress.com%2Fitem%2F{pid}.html"
                f"&aff_fcid={tracking}"
            )
        return product_url

    async def get_coupons(self, store: str = "") -> List[CouponResult]:
        """
        Retorna promoções de tempo limitado (flash deals).

        Usa: aliexpress.affiliate.promotion.flash.get (TOP)
        """
        if not self._is_configured():
            return []

        params: Dict[str, Any] = {
            "page_size":       "20",
            "page_no":         "1",
            "target_currency": "BRL",
            "target_language": "PT",
            "ship_to_country": "BR",
        }

        if settings.ALIEXPRESS_TRACKING_ID:
            params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID

        try:
            data = await self._call_top(
                "aliexpress.affiliate.promotion.flash.get", params
            )
            return self._parse_flash_deals(data)
        except Exception as e:
            logger.warning(f"AliExpress flash deals failed: {e}")
            return []

    def _parse_flash_deals(self, data: dict) -> List[CouponResult]:
        resp = data.get("aliexpress_affiliate_promotion_flash_get_response", {})
        resp_result = resp.get("resp_result", {})

        if resp_result.get("resp_code") != 200:
            return []

        deals = (
            resp_result.get("result", {})
            .get("products", {})
            .get("product", [])
        )

        coupons = []
        for d in deals:
            price = float(d.get("target_sale_price", 0) or 0)
            original = float(d.get("target_original_price") or price)
            if not price or original <= price:
                continue
            discount = round((1 - price / original) * 100, 1)
            coupons.append(CouponResult(
                marketplace=MarketplaceId.aliexpress,
                code="",
                description=f"Flash Deal: {d.get('product_title', '')[:80]}",
                discount_type="percent",
                discount_value=discount,
                min_purchase=price,
                store="aliexpress",
            ))

        return coupons
