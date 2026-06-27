from fastapi import APIRouter, Depends
from sqlalchemy import func, select, distinct, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from app.models.models import Product, Search, Offer
from app.db.session import get_db

router = APIRouter()


@router.get("/stats")
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    """Public stats endpoint — no auth required."""
    try:
        # Total products in DB
        total_products_result = await db.execute(
            select(func.count()).select_from(Product)
        )
        total_products = total_products_result.scalar() or 0

        # Distinct providers with offers
        providers_result = await db.execute(
            select(func.count(distinct(Offer.provider)))
        )
        platforms = providers_result.scalar() or 0

        # Weekly searches (last 7 days)
        since = datetime.now(timezone.utc) - timedelta(days=7)
        weekly_result = await db.execute(
            select(func.count())
            .select_from(Search)
            .where(Search.created_at >= since)
        )
        weekly_searches = weekly_result.scalar() or 0

        # Daily searches for last 7 days (for chart)
        daily_result = await db.execute(
            select(
                func.date(Search.created_at).label("day"),
                func.count().label("cnt"),
            )
            .where(Search.created_at >= since)
            .group_by(func.date(Search.created_at))
            .order_by(func.date(Search.created_at))
        )
        daily_rows = daily_result.fetchall()

        # Build daily array with Portuguese day labels
        day_names = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"]
        daily_data = []
        for i in range(7):
            d = datetime.now(timezone.utc).date() - timedelta(days=6 - i)
            label = day_names[d.weekday()]
            # weekday(): Monday=0, Sunday=6 — our Dom=0, Seg=1...
            # Python weekday: Mon=0, Sun=6. We want Dom=0, Seg=1...Ter=2...Sab=6
            # Map: 6(Sun)→0, 0(Mon)→1, 1(Tue)→2, 2(Wed)→3, 3(Thu)→4, 4(Fri)→5, 5(Sat)→6
            py_weekday = d.weekday()
            mapped = (py_weekday + 1) % 7  # Sun(6)→0, Mon(0)→1, ...
            day_label = day_names[mapped]
            # Find matching row
            match = next((r for r in daily_rows if str(r.day) == str(d)), None)
            daily_data.append({
                "day": day_label,
                "value": match.cnt if match else 0,
            })

        return {
            "total_products": total_products,
            "weekly_searches": weekly_searches,
            "platforms": platforms,
            "daily_searches": daily_data,
        }
    except Exception:
        # Fallback: return zeros if DB access fails
        return {
            "total_products": 0,
            "weekly_searches": 0,
            "platforms": 0,
            "daily_searches": [],
        }
