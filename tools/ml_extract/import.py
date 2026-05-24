#!/usr/bin/env python3
"""
import.py — Importa afiliados_ml_*.json → affiliate_products no BD.

Uso:
  python tools/ml_extract/import.py                       # importa o JSON mais recente
  python tools/ml_extract/import.py --file caminho.json   # importa arquivo específico
  python tools/ml_extract/import.py --dry-run             # simula sem escrever no BD
  python tools/ml_extract/import.py --verbose              # log detalhado por produto

Requisitos:
  asyncpg (venv do backend já tem): pip install asyncpg
  DATABASE_URL: lida do backend/.env automaticamente
"""

import asyncio
import json
import re
import sys
import os
import glob
import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent          # tools/ml_extract/
PROJECT_ROOT = SCRIPT_DIR.parent.parent                # repo root
BACKEND_DIR = PROJECT_ROOT / "backend"
ENV_FILE = BACKEND_DIR / ".env"


# ── load .env ─────────────────────────────────────────────────────────────────
def load_env() -> dict:
    """Le DATABASE_URL do backend/.env (sem dependencia externa)."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


# ── parsing helpers ───────────────────────────────────────────────────────────
def parse_price(raw: str) -> float | None:
    """Extrai float de 'R$ 1.998 9% OFF' -> 1998.0"""
    if not raw:
        return None
    m = re.search(r"R\$\s*([\d.,]+)", raw)
    if not m:
        return None
    num = m.group(1)
    if "." in num and "," in num:
        num = num.replace(".", "").replace(",", ".")
    elif "." in num and "," not in num:
        parts = num.split(".")
        if len(parts[-1]) == 3 and len(parts) == 2:
            num = num.replace(".", "")
    try:
        return round(float(num), 2)
    except ValueError:
        return None


def parse_commission(raw: str) -> float | None:
    """Extrai '15%' -> 15.0"""
    if not raw:
        return None
    m = re.search(r"([\d.,]+)\s*%", raw)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_rating(raw: str) -> float | None:
    """Extrai '4.9' de '4.9' ou '4.9 *'"""
    if not raw:
        return None
    m = re.search(r"([\d.,]+)", raw)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_sold_count(raw: str) -> int | None:
    """Extrai '1000 vendidos' -> 1000, '10mil vendidos' -> 10000"""
    if not raw:
        return None
    text = raw.lower().replace(".", "")
    m = re.search(r"(\d+)\s*mil", text)
    if m:
        return int(m.group(1)) * 1000
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return None


# ── DB import ─────────────────────────────────────────────────────────────────
async def import_to_db(
    records: list[dict],
    database_url: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Importa lista de dicts para affiliate_products. Retorna stats."""
    try:
        import asyncpg
    except ImportError:
        print("ERRO: asyncpg nao instalado. Rode:")
        print("   cd backend && .venv/bin/pip install asyncpg")
        sys.exit(1)

    stats = {
        "total": len(records),
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    if dry_run:
        print(f"\nDRY RUN -- {len(records)} registros (sem escrever no BD)\n")
        for i, r in enumerate(records, 1):
            title = (r.get("nome") or "")[:60]
            price = parse_price(r.get("preco", "") or "")
            comm = parse_commission(r.get("ganhos", "") or "")
            url = r.get("link_prod", "")
            print(f"  [{i:03d}] {title:<60}  R$ {price}  {comm}%  {url[:50]}")
        print(f"\n{stats['total']} registros seriam processados.")
        return stats

    conn = await asyncpg.connect(database_url)
    try:
        for i, r in enumerate(records, 1):
            try:
                title = (r.get("nome") or "")[:500] or None
                url = (r.get("link_prod") or "").strip()
                ml_code = (r.get("Codigo_ML") or "").strip() or None
                price = parse_price(r.get("preco", "") or "")
                comm = parse_commission(r.get("ganhos", "") or "")
                rating = parse_rating(r.get("avaliacao", "") or "")
                sold = parse_sold_count(r.get("vendidos", "") or "")
                badge_raw = (r.get("badge") or "").strip() or None

                notes_parts = []
                if badge_raw:
                    notes_parts.append(f"Badge: {badge_raw}")
                if rating is not None:
                    notes_parts.append(f"Avaliacao: {rating}")
                if sold is not None:
                    notes_parts.append(f"Vendidos: {sold}")
                notes = " | ".join(notes_parts) if notes_parts else None

                if not url:
                    stats["skipped"] += 1
                    if verbose:
                        print(f"  [{i:03d}] SKIP -- sem link_prod")
                    continue

                # Upsert por affiliate_url
                existing = await conn.fetchrow(
                    "SELECT id FROM affiliate_products WHERE affiliate_url = $1",
                    url,
                )

                now = datetime.now(timezone.utc)
                if existing:
                    await conn.execute(
                        """UPDATE affiliate_products SET
                            ml_code = COALESCE($1, ml_code),
                            title = COALESCE($2, title),
                            price = COALESCE($3, price),
                            commission_pct = COALESCE($4, commission_pct),
                            notes = COALESCE($5, notes),
                            is_active = true,
                            updated_at = $6
                        WHERE affiliate_url = $7""",
                        ml_code, title, price, comm, notes, now, url,
                    )
                    stats["updated"] += 1
                    if verbose:
                        print(f"  [{i:03d}] UPD  {(title or '')[:50]}")
                else:
                    await conn.execute(
                        """INSERT INTO affiliate_products
                            (id, ml_code, affiliate_url, title, price,
                             commission_pct, notes, is_active, created_at, updated_at)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,true,$8,$8)""",
                        str(uuid4()), ml_code, url, title, price,
                        comm, notes, now,
                    )
                    stats["inserted"] += 1
                    if verbose:
                        print(f"  [{i:03d}] NEW  {(title or '')[:50]}")

            except Exception as e:
                stats["errors"] += 1
                print(f"  [{i:03d}] ERRO: {e}", file=sys.stderr)

    finally:
        await conn.close()

    return stats


# ── main ──────────────────────────────────────────────────────────────────────
def find_latest_json(directory: Path) -> Path | None:
    files = sorted(directory.glob("afiliados_ml_*.json"), reverse=True)
    return files[0] if files else None


def main():
    parser = argparse.ArgumentParser(
        description="Importa afiliados_ml_*.json -> affiliate_products BD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python import.py                        # importa JSON mais recente
  python import.py --file afiliados_ml_2026-05-24.json
  python import.py --dry-run              # simula sem escrever
  python import.py --verbose              # log detalhado
""",
    )
    parser.add_argument("--file", type=str, help="Caminho especifico do JSON")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem escrever no BD")
    parser.add_argument("--verbose", action="store_true", help="Log detalhado por produto")
    args = parser.parse_args()

    # resolve JSON file
    if args.file:
        json_path = Path(args.file)
        if not json_path.is_absolute():
            json_path = SCRIPT_DIR / json_path
    else:
        json_path = find_latest_json(SCRIPT_DIR)

    if not json_path or not json_path.exists():
        print(f"JSON nao encontrado: {json_path}")
        print("   Use --file para especificar ou gere um JSON com ml_extract.js")
        sys.exit(1)

    print(f"JSON: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        print("ERRO: JSON raiz deve ser array [...]")
        sys.exit(1)

    print(f"{len(records)} registros no JSON")

    # resolve DATABASE_URL
    env = load_env()
    database_url = os.environ.get("DATABASE_URL") or env.get("DATABASE_URL")

    if not database_url:
        print("ERRO: DATABASE_URL nao encontrada.")
        print("   Defina no backend/.env ou exporte DATABASE_URL=...")
        sys.exit(1)

    # asyncpg nao aceita 'postgresql+asyncpg://' — converte para 'postgresql://'
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    # run
    stats = asyncio.run(
        import_to_db(records, database_url, dry_run=args.dry_run, verbose=args.verbose)
    )

    # summary
    if not args.dry_run:
        print(f"\n{'='*50}")
        print(f"  Total:       {stats['total']}")
        print(f"  Inseridos:   {stats['inserted']}")
        print(f"  Atualizados: {stats['updated']}")
        print(f"  Pulados:     {stats['skipped']}")
        print(f"  Erros:       {stats['errors']}")
        print(f"{'='*50}")

        if stats["errors"] == 0:
            print("Import concluido sem erros.")
        else:
            print(f"{stats['errors']} erro(s) -- verifique o log acima.")
            sys.exit(1)


if __name__ == "__main__":
    main()
