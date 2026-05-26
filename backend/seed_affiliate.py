"""
Seed dos 33 links ML afiliados iniciais.
Uso: python seed_affiliate.py
"""
import asyncio
import httpx

import os

LINKS = [
    ("S5L99N-Y7WN",  "https://meli.la/2XJkFQV"),
    ("S5L99N-QE4H",  "https://meli.la/1EQUr2w"),
    ("S5L99N-THVL",  "https://meli.la/27Ho3HE"),
    ("S5L99N-Z962",  "https://meli.la/1pjoQwN"),
    ("S5L99N-91T0",  "https://meli.la/2NzkFC5"),
    ("S5L99N-DPEJ",  "https://meli.la/2mr1w1E"),
    ("S5L99N-WX55",  "https://meli.la/2dJKC4m"),
    ("S5L99N-ZLTK",  "https://meli.la/2TA1emg"),
    ("S5L99N-L3TF",  "https://meli.la/1tALUPF"),
    ("S5L99N-65K5",  "https://meli.la/2G85zcM"),
    ("S5L99N-2D10",  "https://meli.la/1q5SCuz"),
    ("S5L99N-1BM3",  "https://meli.la/2BU5Gcq"),
    ("S5L99N-BVQR",  "https://meli.la/2qykwFR"),
    ("S5L99N-K35P",  "https://meli.la/1Ym3mTb"),
    ("S5L99N-06TE",  "https://meli.la/2XVhCW8"),
    ("S5L99N-MMEM",  "https://meli.la/2aMG27D"),
    ("S5L99N-QEDJ",  "https://meli.la/2tKqTU2"),
    ("S5L99N-M9SK",  "https://meli.la/1L8oCBg"),
    ("S5L99N-W14P",  "https://meli.la/1SZ4aYX"),
    ("S5L99N-2KW1",  "https://meli.la/28rAgLA"),
    ("S5L99N-SS5W",  "https://meli.la/2AdWrW9"),
    ("S5L99N-BZ6N",  "https://meli.la/1qwtQmM"),
    ("S5L99N-63EB",  "https://meli.la/1kTutuL"),
    ("S5L99N-GFSE",  "https://meli.la/2Z782Xb"),
    ("S5L99N-DTG8",  "https://meli.la/1PgVZTx"),
    ("S5L99N-M0T3",  "https://meli.la/1t53yz7"),
    ("S5L99N-K1FS",  "https://meli.la/1fm8s9P"),
    ("S5L99N-07SD",  "https://meli.la/2yVsVVb"),
    ("S5L99N-GB3D",  "https://meli.la/1UcRK4d"),
    ("S5L99N-DTZH",  "https://meli.la/2zuc55S"),
    ("S5L99N-7HMA",  "https://meli.la/15nobu8"),
    ("S5L99N-5RQ3",  "https://meli.la/1sYLDg3"),
    ("S5L99N-YHT3",  "https://meli.la/2PDYyF6"),
]

API = os.environ.get("BPT_API_URL", "https://alessandro2090-bestpricetoday-api.hf.space")
ADMIN_KEY = os.environ.get("BPT_ADMIN_KEY", "")
if not ADMIN_KEY:
    raise ValueError("BPT_ADMIN_KEY não definida. Exporte a variável de ambiente.")

async def main():
    items = [{"ml_code": code, "affiliate_url": url} for code, url in LINKS]
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{API}/api/v1/affiliate/products/seed",
            json={"items": items},
            headers={"X-Admin-Key": ADMIN_KEY},
        )
        print(r.status_code, r.json())

asyncio.run(main())
