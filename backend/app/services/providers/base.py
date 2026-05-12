"""Base provider interface."""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.schemas import OfferSchema
import httpx
import asyncio
from app.core.logging import logger


class BaseProvider(ABC):
    name: str = ""
    timeout: int = 10
    max_retries: int = 3

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "BestPriceToday/1.0"},
                follow_redirects=True,
            )
        return self._client

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        pass

    async def safe_search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        for attempt in range(self.max_retries):
            try:
                return await self.search(query, limit)
            except httpx.TimeoutException:
                logger.warning(f"{self.name}: timeout on attempt {attempt+1}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as e:
                logger.error(f"{self.name}: error on attempt {attempt+1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        return []

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
