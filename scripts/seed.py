#!/usr/bin/env python3
"""Seed database with test data."""
import asyncio
from app.db.session import AsyncSessionLocal, init_db
from app.models.models import Coupon, ProviderEnum
from datetime import datetime, timedelta


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        coupons = [
            Coupon(
                provider=ProviderEnum.mercadolivre,
                code="MELI10",
                description="10% de desconto no Mercado Livre",
                discount_type="percent",
                discount_value=10,
                min_purchase=100,
                valid_until=datetime.utcnow() + timedelta(days=30),
            ),
            Coupon(
                provider=ProviderEnum.shopee,
                code="SHOPEE15",
                description="15% off na Shopee",
                discount_type="percent",
                discount_value=15,
                min_purchase=50,
                valid_until=datetime.utcnow() + timedelta(days=15),
            ),
        ]
        db.add_all(coupons)
        await db.commit()
        print("✅ Seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
