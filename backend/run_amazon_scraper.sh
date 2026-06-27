#!/bin/bash
# run_amazon_scraper.sh — Cron diário do scraper Amazon
#
# Marca produtos Amazon antigos como inativos, roda o scraper (que reativa
# os que encontrar), e reporta stats. Roda às 3am (antes do ML scraper às 4am).
#
# Uso manual:
#   /home/alessandro/backend/run_amazon_scraper.sh
#   /home/alessandro/backend/run_amazon_scraper.sh --queries "iphone 16,notebook dell"

cd /home/alessandro/backend
source venv/bin/activate

echo "=== Amazon Scraper Cron — $(date) ==="

# 1. Marca produtos Amazon antigos como inativos
#    (o scraper reativa os que encontrar — produtos fora de estoque somem)
python3 -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.models import AffiliateProduct
from sqlalchemy import update, func

async def deactivate():
    async with AsyncSessionLocal() as db:
        r = await db.execute(
            update(AffiliateProduct)
            .where(
                AffiliateProduct.is_active == True,
                func.lower(AffiliateProduct.notes).like('%amazon_scraper%')
            )
            .values(is_active=False)
        )
        await db.commit()
        print(f'Produtos Amazon desativados: {r.rowcount}')

asyncio.run(deactivate())
"

# 2. Roda o scraper (reativa produtos encontrados)
if [ -n "$1" ] && [ "$1" = "--queries" ]; then
    shift
    python -m app.workers.amazon_scraper --queries "$1" >> amazon_scraper.log 2>&1
else
    python -m app.workers.amazon_scraper >> amazon_scraper.log 2>&1
fi

# 3. Reporta stats
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
