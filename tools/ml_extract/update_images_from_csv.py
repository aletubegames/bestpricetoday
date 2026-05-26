#!/usr/bin/env python3
"""Generate SQL updates for image_url from a CSV produced by generate_artifact.py

Usage examples:
  # dry-run, generate SQL preview for first 20 rows
  python update_images_from_csv.py --csv afiliados_ml_.../import_candidates_backfill.csv --limit 20 --dry-run --out updates_preview.sql

  # apply updates (will connect to DB using DATABASE_URL from backend/.env)
  python update_images_from_csv.py --csv ... --limit 20 --apply
"""
import argparse
import csv
import json
import os
import sys
from typing import List, Dict

BASE = os.path.dirname(__file__)

def esc(s: str) -> str:
    if s is None:
        return ''
    return str(s).replace("'", "''")

def read_csv(path: str, limit: int = None, offset: int = 0) -> List[Dict[str,str]]:
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            if i < offset:
                continue
            rows.append(r)
            if limit and len(rows) >= limit:
                break
    return rows

async def apply_updates(updates: List[Dict[str,str]], database_url: str, verbose: bool=False):
    import asyncio
    import asyncpg
    import ssl

    async def create_connection(url: str):
        last_exc = None
        ctx = ssl.create_default_context()
        for attempt in range(3):
            try:
                return await asyncpg.connect(url, ssl=ctx)
            except Exception as e:
                last_exc = e
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
        for attempt in range(3):
            try:
                return await asyncpg.connect(url)
            except Exception as e:
                last_exc = e
                if attempt < 2:
                    await asyncio.sleep(2 * (attempt + 1))
        raise last_exc

    conn = await create_connection(database_url)
    results = []
    try:
        for u in updates:
            affiliate_url = u['affiliate_url']
            image_url = u['image_url']
            try:
                await conn.execute(
                    "UPDATE affiliate_products SET image_url = $1, updated_at = now() WHERE affiliate_url = $2",
                    image_url, affiliate_url,
                )
                results.append({'affiliate_url': affiliate_url, 'image_url': image_url, 'status': 'updated'})
                if verbose:
                    print(f"UPDATED {affiliate_url}")
            except Exception as e:
                results.append({'affiliate_url': affiliate_url, 'image_url': image_url, 'status': 'error', 'error': str(e)})
                print(f"ERROR updating {affiliate_url}: {e}", file=sys.stderr)
    finally:
        try:
            await conn.close()
        except Exception:
            pass
    return results

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--limit', type=int, default=None)
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--out', default=os.path.join(BASE, 'updates_preview.sql'))
    p.add_argument('--apply', action='store_true')
    p.add_argument('--verbose', action='store_true')
    args = p.parse_args()

    csv_path = os.path.abspath(args.csv)
    if not os.path.exists(csv_path):
        print('CSV not found:', csv_path, file=sys.stderr)
        sys.exit(2)

    rows = read_csv(csv_path, limit=args.limit, offset=args.offset)
    updates = []
    for r in rows:
        img = (r.get('image_url') or '').strip()
        affiliate_url = (r.get('affiliate_url') or r.get('affiliate_url').strip() if r.get('affiliate_url') else '').strip()
        if not affiliate_url:
            # try ml_code fallback
            affiliate_url = (r.get('ml_code') or '').strip()
        if not img:
            continue
        updates.append({'affiliate_url': affiliate_url, 'image_url': img})

    if not updates:
        print('Nenhuma atualização encontrada nas linhas lidas.')
        print(f'Rows read: {len(rows)}')
        sys.exit(0)

    # dry-run: write SQL preview
    if args.dry_run or not args.apply:
        out_path = os.path.abspath(args.out)
        with open(out_path, 'w', encoding='utf-8') as f:
            for u in updates:
                a = esc(u['affiliate_url'])
                im = esc(u['image_url'])
                sql = f"UPDATE affiliate_products SET image_url = '{im}', updated_at = now() WHERE affiliate_url = '{a}';\n"
                f.write(sql)
        summary = {
            'csv': csv_path,
            'rows_read': len(rows),
            'updates_found': len(updates),
            'out_sql': out_path,
        }
        summary_path = os.path.join(BASE, 'updates_preview_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print('Wrote SQL preview to', out_path)
        print('Wrote summary to', summary_path)
        print('updates_found=', len(updates))
        return

    # if we get here, apply=True
    # read DATABASE_URL from backend/.env or environment
    repo_root = os.path.abspath(os.path.join(BASE, '..', '..'))
    env_path = os.path.join(repo_root, 'backend', '.env')

    database_url = os.environ.get('DATABASE_URL')
    if not database_url and os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('DATABASE_URL='):
                    database_url = line.strip().split('=',1)[1]
                    break

    if not database_url:
        print('DATABASE_URL not found in backend/.env or environment; set DATABASE_URL env var or put it in backend/.env', file=sys.stderr)
        sys.exit(2)

    # Normalize SQLAlchemy-style DSN (postgresql+asyncpg://) to asyncpg-acceptable form (postgresql://)
    if database_url.startswith('postgresql+asyncpg://'):
        database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://', 1)

    import asyncio
    results = asyncio.run(apply_updates(updates, database_url, verbose=args.verbose))
    # write log
    log_path = os.path.join(BASE, 'updates_applied.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    summary_path = os.path.join(BASE, 'updates_apply_summary.json')
    summary = {'attempted': len(results), 'updated': sum(1 for r in results if r.get('status')=='updated'), 'errors': sum(1 for r in results if r.get('status')!='updated')}
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print('Applied updates:', summary)

if __name__ == '__main__':
    main()
