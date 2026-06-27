"""curated_queries.py - Queries curadas para o sitemap.

IMPORTANTE: Só incluir queries que retornam ≥3 ofertas reais na API.
Queries vazias prejudicam SEO (thin content) e fazem o Google desindexar o site.

Última verificação: 2026-06-27 — testadas 6.759 queries, só 21 tinham ≥3 ofertas.
As 21 válidas são quase todas airfryers (único nicho com catálogo real no AliExpress).

Para expandir: adicionar produtos ao catálogo (scraper ML, Amazon Associates) e
rodar /tmp/test_queries.py novamente para descobrir novas queries válidas.
"""

from typing import List

# Total: 21 queries (verificadas em 2026-06-27)
CURATED_QUERIES: List[str] = [
    "abajur",
    "adaptador-usb-c",
    "airfryer",
    "airfryer-3l",
    "airfryer-4l",
    "airfryer-5l",
    "airfryer-6l",
    "airfryer-arno",
    "airfryer-arno-5l",
    "airfryer-arno-6l",
    "airfryer-arno-digital",
    "airfryer-arno-sem-oleo",
    "airfryer-britania",
    "airfryer-britania-3l",
    "airfryer-britania-4l",
    "airfryer-britania-5l",
    "airfryer-britania-6l",
    "airfryer-britania-digital",
    "airfryer-britania-digital-5l",
    "airfryer-britania-sem-oleo",
    "airfryer-cadence-3l",
]
