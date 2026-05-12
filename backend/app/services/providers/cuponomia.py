"""Cuponomia public API for coupon integration."""
import httpx
from typing import List, Dict
from app.services.providers.base import BaseProvider
from app.core.config import settings
from app.core.logging import logger


class CuponomiaProvider(BaseProvider):
    name = "cuponomia"
    BASE_URL = "https://www.cuponomia.com.br/api"

    async def get_coupons(self, store: str = "") -> List[Dict]:
        try:
            client = await self.get_client()
            params = {"store": store} if store else {}
            if settings.CUPONOMIA_API_KEY:
                params["token"] = settings.CUPONOMIA_API_KEY
            resp = await client.get(f"{self.BASE_URL}/coupons", params=params)
            resp.raise_for_status()
            data = resp.json()
            coupons = data if isinstance(data, list) else data.get("coupons", [])
            return [
                {
                    "code": c.get("code", ""),
                    "description": c.get("title", c.get("description", "")),
                    "discount_type": "percent" if "%" in str(c.get("discount", "")) else "fixed",
                    "discount_value": self._extract_discount(str(c.get("discount", "0"))),
                    "store": c.get("store", ""),
                    "valid_until": c.get("expire_at", None),
                }
                for c in coupons if c.get("code")
            ]
        except Exception as e:
            logger.error(f"Cuponomia error: {e}")
            return []

    def _extract_discount(self, s: str) -> float:
        import re
        match = re.search(r"[\d,.]+", s)
        if match:
            return float(match.group().replace(",", "."))
        return 0.0

    async def search(self, query: str, limit: int = 10):
        return []
