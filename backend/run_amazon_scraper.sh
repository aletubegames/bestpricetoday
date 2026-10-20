#!/bin/bash
# run_amazon_scraper.sh — Cron diário do scraper Amazon
#
# O scraper só desativa produtos antigos depois de abrir o navegador e
# coletar pelo menos uma oferta. Assim uma falha de Playwright não zera o catálogo.
#
# Uso manual:
#   /home/alessandro/backend/run_amazon_scraper.sh
#   /home/alessandro/backend/run_amazon_scraper.sh --queries "iphone 16,notebook dell"

set -euo pipefail

cd /home/alessandro/backend
source venv/bin/activate

# Impede duas execuções do scraper Amazon ao mesmo tempo.
exec 9>/home/alessandro/backend/.amazon_scraper.lock
if ! flock -n 9; then
    echo "Amazon scraper já está rodando; encerrando esta execução."
    exit 0
fi

echo "=== Amazon Scraper Cron — $(date) ==="

set +e
if [ "${1:-}" = "--queries" ]; then
    shift
    if [ "$#" -eq 0 ]; then
        echo "--queries requer uma lista separada por vírgulas." >&2
        exit 2
    fi
    python -m app.workers.amazon_scraper --queries "$1" >> amazon_scraper.log 2>&1
else
    python -m app.workers.amazon_scraper >> amazon_scraper.log 2>&1
fi
scraper_status=$?
set -e

if [ "$scraper_status" -ne 0 ]; then
    echo "Amazon scraper falhou (exit=$scraper_status); catálogo anterior preservado."
    exit "$scraper_status"
fi

python3 -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.models import AffiliateProduct
from sqlalchemy import select, func

async def stats():
    async with AsyncSessionLocal() as db:
        r = await db.execute(
            select(func.count(AffiliateProduct.id)).where(
                AffiliateProduct.is_active == True,
                func.lower(AffiliateProduct.notes).like('%amazon_scraper%')
            )
        )
        amazon = r.scalar()
        r2 = await db.execute(
            select(func.count(AffiliateProduct.id)).where(AffiliateProduct.is_active == True)
        )
        total = r2.scalar()
        print(f'Produtos Amazon ativos: {amazon}')
        print(f'Total produtos ativos: {total}')

asyncio.run(stats())
"

echo "=== Concluído — $(date) ==="
