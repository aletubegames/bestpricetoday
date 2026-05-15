"""
Testes da camada integrations/ — AliExpress e Shopee.

Cobre:
  - AliExpressSigner: TOP e GOP
  - Filtros de relevância e acessórios
  - Parsing de respostas mock
  - ShopeeClient: parsing
  - ProductResult: final_price, economy
"""
import pytest
from app.integrations.base import ProductResult, MarketplaceId
from app.integrations.aliexpress import AliExpressClient, AliExpressSigner
from app.integrations.shopee import ShopeeSigner


# ─── AliExpressSigner ────────────────────────────────────────────────────────

class TestAliExpressSigner:
    def setup_method(self):
        self.signer = AliExpressSigner(app_key="testkey", app_secret="testsecret")

    def test_sign_top_returns_all_required_fields(self):
        params = self.signer.sign_top(
            "aliexpress.affiliate.product.query",
            {"keywords": "iphone", "page_size": "10"},
        )
        assert "sign" in params
        assert "app_key" in params
        assert "method" in params
        assert "timestamp" in params
        assert params["sign_method"] == "sha256"
        assert params["format"] == "json"
        assert params["v"] == "2.0"

    def test_sign_top_produces_64_char_hex_uppercase(self):
        params = self.signer.sign_top("aliexpress.affiliate.product.query", {})
        assert len(params["sign"]) == 64
        assert params["sign"] == params["sign"].upper()

    def test_sign_top_is_deterministic_for_same_secret(self):
        """Mesmos params + secret devem produzir mesma assinatura."""
        ts = "1715800000000"
        p1 = {
            "app_key": "testkey",
            "method": "aliexpress.affiliate.product.query",
            "timestamp": ts,
            "format": "json",
            "v": "2.0",
            "sign_method": "sha256",
            "keywords": "iphone",
        }
        p2 = p1.copy()
        import hmac, hashlib
        def compute(params, secret):
            sorted_items = sorted(params.items())
            concat = secret + "".join(f"{k}{v}" for k, v in sorted_items) + secret
            return hmac.new(
                secret.encode(), concat.encode(), hashlib.sha256
            ).hexdigest().upper()
        assert compute(p1, "testsecret") == compute(p2, "testsecret")

    def test_sign_gop_includes_api_path_in_sign(self):
        """GOP e TOP com os mesmos params devem gerar assinaturas diferentes (path no GOP)."""
        shared_params = {"code": "abc123"}
        top = self.signer.sign_top("aliexpress.affiliate.product.query", shared_params)
        gop = self.signer.sign_gop("/auth/token/create", shared_params)
        # Assinaturas diferentes porque GOP prefixo o api_path
        assert top["sign"] != gop["sign"]

    def test_sign_gop_hex_uppercase_64(self):
        params = self.signer.sign_gop("/auth/token/create", {"code": "xyz"})
        assert len(params["sign"]) == 64
        assert params["sign"] == params["sign"].upper()


# ─── AliExpressClient — filtros de relevância ────────────────────────────────

class TestAliExpressRelevance:
    def setup_method(self):
        self.client = AliExpressClient()

    def _make_result(self, title: str) -> ProductResult:
        return ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id="1",
            title=title,
            price=100.0,
            affiliate_url="https://example.com",
        )

    def test_keeps_relevant_product(self):
        results = [self._make_result("Apple iPhone 16 Pro Max 256GB Smartphone")]
        filtered = self.client._filter_relevant("iphone 16 pro", results)
        assert len(filtered) == 1

    def test_rejects_accessory_when_query_is_not(self):
        results = [
            self._make_result("Capa capinha para iPhone 16 Pro transparente"),
            self._make_result("Apple iPhone 16 Pro 128GB"),
        ]
        filtered = self.client._filter_relevant("iphone 16 pro", results)
        assert len(filtered) == 1
        assert "iPhone 16 Pro 128GB" in filtered[0].title

    def test_keeps_accessory_when_query_is_accessory(self):
        results = [self._make_result("Capa para iPhone 16 Pro Max silicone")]
        filtered = self.client._filter_relevant("capa iphone 16 pro", results)
        assert len(filtered) == 1

    def test_rejects_wrong_numeric(self):
        """RTX 4060 não deve aparecer em busca de RTX 4070."""
        results = [
            self._make_result("ASUS RTX 4060 8GB OC"),
            self._make_result("GIGABYTE RTX 4070 12GB"),
        ]
        filtered = self.client._filter_relevant("rtx 4070", results)
        assert len(filtered) == 1
        assert "4070" in filtered[0].title

    def test_empty_results_returns_empty(self):
        assert self.client._filter_relevant("iphone", []) == []

    def test_guess_category_smartphone(self):
        assert self.client._guess_category("iphone 16 pro") != ""
        assert self.client._guess_category("galaxy s24") != ""

    def test_guess_category_no_match(self):
        assert self.client._guess_category("martelo de madeira") == ""


# ─── AliExpressClient — parsing de resposta mock ─────────────────────────────

class TestAliExpressParsing:
    def setup_method(self):
        self.client = AliExpressClient()

    def _top_response(self, products: list) -> dict:
        return {
            "aliexpress_affiliate_product_query_response": {
                "resp_result": {
                    "resp_code": 200,
                    "result": {
                        "products": {"product": products}
                    }
                }
            }
        }

    def test_parse_top_basic(self):
        raw = self._top_response([{
            "product_id": "123",
            "product_title": "Samsung Galaxy S24",
            "target_sale_price": "3499.00",
            "target_original_price": "4299.00",
            "product_main_image_url": "https://img.aliexpress.com/1.jpg",
            "product_detail_url": "https://www.aliexpress.com/item/123.html",
            "promotion_link": "https://s.click.aliexpress.com/xxx",
            "lastest_volume": "1500",
        }])
        results = self.client._parse_top_products(raw)
        assert len(results) == 1
        r = results[0]
        assert r.external_id == "123"
        assert r.title == "Samsung Galaxy S24"
        assert r.price == 3499.0
        assert r.original_price == 4299.0
        assert r.discount_pct > 0
        assert r.affiliate_url == "https://s.click.aliexpress.com/xxx"
        assert r.sales_count == 1500

    def test_parse_top_skips_zero_price(self):
        raw = self._top_response([{
            "product_id": "456",
            "product_title": "Produto sem preço",
            "target_sale_price": "0",
        }])
        results = self.client._parse_top_products(raw)
        assert len(results) == 0

    def test_parse_top_error_code_returns_empty(self):
        raw = {
            "aliexpress_affiliate_product_query_response": {
                "resp_result": {"resp_code": 400, "resp_msg": "Invalid request"}
            }
        }
        results = self.client._parse_top_products(raw)
        assert results == []

    def test_parse_affiliate_link(self):
        raw = {
            "aliexpress_affiliate_link_generate_response": {
                "resp_result": {
                    "resp_code": 200,
                    "result": {
                        "promotion_links": {
                            "promotion_link": [
                                {"promotion_link": "https://s.click.aliexpress.com/aff123"}
                            ]
                        }
                    }
                }
            }
        }
        link = self.client._parse_affiliate_link(raw)
        assert link == "https://s.click.aliexpress.com/aff123"

    def test_fallback_affiliate_link_extracts_product_id(self):
        url = "https://www.aliexpress.com/item/1005006789012345.html"
        link = self.client._fallback_affiliate_link(url)
        assert "1005006789012345" in link
        assert "s.click.aliexpress.com" in link


# ─── ShopeeSigner ────────────────────────────────────────────────────────────

class TestShopeeSigner:
    def test_auth_header_format(self):
        signer = ShopeeSigner(app_id="12345", app_secret="mysecret")
        header = signer.auth_header()
        assert header.startswith("SHA256 Credential=12345,Timestamp=")
        assert "Signature=" in header

    def test_auth_header_signature_is_hex_lowercase(self):
        signer = ShopeeSigner(app_id="12345", app_secret="mysecret")
        header = signer.auth_header()
        sig_part = header.split("Signature=")[1]
        # SHA256 em hex = 64 chars lowercase
        assert len(sig_part) == 64
        assert sig_part == sig_part.lower()

    def test_auth_header_changes_with_time(self):
        """Dois headers gerados em momentos diferentes devem ter timestamps diferentes."""
        import time
        signer = ShopeeSigner(app_id="12345", app_secret="mysecret")
        h1 = signer.auth_header()
        time.sleep(1)
        h2 = signer.auth_header()
        ts1 = h1.split("Timestamp=")[1].split(",")[0]
        ts2 = h2.split("Timestamp=")[1].split(",")[0]
        assert ts1 != ts2


# ─── ProductResult ────────────────────────────────────────────────────────────

class TestProductResult:
    def test_final_price_sem_frete_sem_cupom(self):
        p = ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id="1", title="Teste",
            price=500.0, shipping_free=True,
        )
        assert p.final_price == 500.0

    def test_final_price_com_frete(self):
        p = ProductResult(
            marketplace=MarketplaceId.shopee,
            external_id="2", title="Teste",
            price=300.0, shipping_price=29.90,
        )
        assert p.final_price == 329.90

    def test_final_price_com_cupom(self):
        p = ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id="3", title="Teste",
            price=1000.0, coupon_discount=100.0,
        )
        assert p.final_price == 900.0

    def test_economy_com_preco_original(self):
        p = ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id="4", title="Teste",
            price=800.0, original_price=1200.0,
        )
        assert p.economy == 400.0

    def test_economy_sem_preco_original(self):
        p = ProductResult(
            marketplace=MarketplaceId.aliexpress,
            external_id="5", title="Teste",
            price=500.0,
        )
        assert p.economy == 0.0

    def test_final_price_nao_negativo(self):
        p = ProductResult(
            marketplace=MarketplaceId.shopee,
            external_id="6", title="Teste",
            price=50.0, coupon_discount=200.0,
        )
        assert p.final_price == 0.0
