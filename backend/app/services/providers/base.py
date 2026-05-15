"""Base provider interface."""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState, ProviderStatusSchema
import httpx
import asyncio
from app.core.logging import logger


def add_utm(url: str, provider: str, source: str = "web") -> str:
    """Add UTM params to affiliate link if not already present."""
    if not url or "utm_source" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source=bestpricetoday&utm_medium=affiliate&utm_campaign=search&utm_content={provider}"


class BaseProvider(ABC):
    name: str = ""
    timeout: int = 10
    max_retries: int = 3

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self.last_status: Optional[ProviderStatusSchema] = None

    def _provider_enum(self) -> ProviderEnum:
        return ProviderEnum(self.name)

    def set_status(
        self,
        status: ProviderSearchState,
        message: Optional[str] = None,
        *,
        http_status: Optional[int] = None,
        raw_count: int = 0,
        returned_count: int = 0,
        filtered_count: int = 0,
    ) -> None:
        self.last_status = ProviderStatusSchema(
            provider=self._provider_enum(),
            status=status,
            message=message,
            http_status=http_status,
            raw_count=raw_count,
            returned_count=returned_count,
            filtered_count=filtered_count,
        )

    def _finalize_status(self, results: List[OfferSchema]) -> None:
        if self.last_status is None:
            if results:
                self.set_status(
                    ProviderSearchState.ok,
                    message=f"{len(results)} ofertas retornadas.",
                    raw_count=len(results),
                    returned_count=len(results),
                )
            else:
                self.set_status(
                    ProviderSearchState.no_results,
                    message="Nenhum resultado retornado por este provider.",
                )
            return

        if results and self.last_status.raw_count == 0:
            self.last_status.raw_count = len(results)
        if results and self.last_status.returned_count == 0:
            self.last_status.returned_count = len(results)

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
                results = await self.search(query, limit)
                self._finalize_status(results)
                return results
            except httpx.TimeoutException:
                logger.warning(f"{self.name}: timeout on attempt {attempt+1}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as e:
                logger.error(f"{self.name}: error on attempt {attempt+1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    self.set_status(
                        ProviderSearchState.error,
                        message=f"Erro interno no provider {self.name}: {e}",
                    )
        if self.last_status is None:
            self.set_status(ProviderSearchState.error, message=f"Falha desconhecida no provider {self.name}.")
        return []

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
