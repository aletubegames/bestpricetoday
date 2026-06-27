"""curated_queries.py - Queries curadas para o sitemap.

IMPORTANTE: Só incluir queries que retornam ≥3 ofertas reais na API.
Queries vazias prejudicam SEO (thin content) e fazem o Google desindexar o site.

Última verificação: 2026-06-27 — 81 queries válidas após scraper da Amazon.
Catálogo: 1.084 produtos Amazon + 2.530 ML + AliExpress/Shopee ao vivo.

Para expandir: rodar scraper Amazon com mais queries e testar novamente.
"""

from typing import List

# Total: 81 queries (verificadas em 2026-06-27)
CURATED_QUERIES: List[str] = [
    # Airfryers (21 — originais, catálogo AliExpress)
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
    # Smartphones (17 — scraper Amazon)
    "iphone-16",
    "iphone-16-pro",
    "iphone-16-pro-max",
    "iphone-16-plus",
    "iphone-16e",
    "iphone-15",
    "iphone-15-pro",
    "iphone-15-pro-max",
    "iphone-14",
    "iphone-13",
    "iphone-12",
    "samsung-galaxy-s25",
    "samsung-galaxy-s24",
    "samsung-galaxy-a55",
    "samsung-galaxy-a35",
    "samsung-galaxy-m55",
    "xiaomi-redmi-note-13",
    "xiaomi-redmi-note-13-pro",
    "motorola-edge-50",
    "motorola-moto-g56",
    # Notebooks/Tablets (7 — scraper Amazon)
    "notebook-dell",
    "notebook-lenovo",
    "notebook-asus",
    "macbook-air-m3",
    "macbook-pro",
    "tablet-samsung",
    "ipad-10",
    "kindle-paperwhite",
    # Games (2 — scraper Amazon)
    "playstation-5",
    "ps5",
    # TVs (6 — scraper Amazon)
    "smart-tv-55",
    "smart-tv-50",
    "smart-tv-43",
    "smart-tv-65",
    "tv-lg-oled",
    "tv-samsung-qled",
    # Eletrodomésticos (8 — scraper Amazon)
    "airfryer-philips",
    "airfryer-philco",
    "geladeira-frost-free",
    "fogao-4-bocas",
    "microondas-electrolux",
    "lava-loucas",
    "ventilador-parede",
    "ar-condicionado-split",
    # Beleza (3 — scraper Amazon)
    "secador-philips",
    "prancha-babyliss",
    "barbeador-philips",
    # Ferramentas (2 — scraper Amazon)
    "furadeira-makita",
    "parafusadeira-bosch",
    # Pet (1 — scraper Amazon)
    "racao-15kg",
    # Moda (2 — scraper Amazon)
    "tenis-nike-masculino",
    "tenis-adidas",
    # Informática (6 — scraper Amazon)
    "ssd-nvme-1tb",
    "memoria-ram-16gb",
    "mouse-logitech",
    "teclado-mecanico",
    "monitor-24",
    "monitor-27",
    # Áudio (1 — scraper Amazon)
    "fone-bluetooth-jbl",
    # Casa (1 — scraper Amazon)
    "mochila-notebook",
]
