"""Bloco de apoio/doação anexado às descrições de vídeos publicados.

Ordem do dono (2026-10-19): todo programa que gera vídeo carrega o mesmo
pedido de ajuda do CryptoKitchen (BTC2026/crypto_toon). Os endereços são
públicos por natureza (vão em descrição pública) e podem ser sobrescritos
por env: SUPPORT_BTC_ADDRESS / SUPPORT_ETH_ADDRESS.
"""

from __future__ import annotations

import os

BTC_ADDRESS = os.getenv("SUPPORT_BTC_ADDRESS", "bc1qnyqg92pkr3ruthk2cc3t60auyqf6gw9yywg5tg")
ETH_ADDRESS = os.getenv("SUPPORT_ETH_ADDRESS", "0x95DdD84F3c982A6FEc3A03416CE2B9565E64f5FF")

SUPPORT_PT = (
    "Gostando do conteúdo? Ajude o canal a continuar no ar e apoie novos "
    "episódios com uma doação:\n"
    f"BTC: {BTC_ADDRESS}\n"
    f"ETH (ERC-20): {ETH_ADDRESS}"
)

SEPARATOR = "\n\n"


def append_support(description: str, block: str = SUPPORT_PT) -> str:
    """Anexa o bloco de apoio no fim da descrição (idempotente)."""
    if not description:
        return block
    if block in description:
        return description
    return f"{description.rstrip()}{SEPARATOR}{block}"


def fit_limit(text: str, limit: int) -> str:
    """Respeita o limite de caracteres da plataforma sem cortar o bloco de apoio.

    Se o texto passar do limite, descarta o bloco de apoio inteiro (nunca
    corta endereço de carteira no meio — doação pela metade é pior que nada)
    e só então trunca o restante.
    """
    if len(text) <= limit:
        return text
    cut = text.rfind("\n\n" + SUPPORT_PT[:24])
    if cut > 0:
        text = text[:cut]
        if len(text) <= limit:
            return text
    return text[:limit]
