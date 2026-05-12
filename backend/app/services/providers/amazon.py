"""Amazon Product Advertising API v5 Provider."""
import hmac
import hashlib
import datetime
import json
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum
from app.core.config import settings
from app.core.logging import logger


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
        if not settings.AMAZON_ACCESS_KEY:
            logger.warning("Amazon: not configured, skipping")
            return []
        try:
            return await self._do_search(query, limit)
        except Exception as e:
            logger.error(f"Amazon search error: {e}")
            return []

    async def _do_search(self, query: str, limit: int) -> List[OfferSchema]:
        now = datetime.datetime.utcnow()
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
        return self._parse(data)

    def _parse(self, data: dict) -> List[OfferSchema]:
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
