"""
Conversion Tracker — fecha o loop clique → conversão.

Fluxo:
  1. Cron job ou endpoint manual chama poll_all_conversions()
  2. Para cada plataforma, busca orders recentes via API
  3. Tenta vincular order ao click_id via tracking_id
  4. Salva na tabela conversion_events (evita duplicatas via external_order_id)
"""
from __future__ import annotations
import hashlib, hmac, time, httpx
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.logging import logger
from app.models.models import ConversionEvent, ClickEvent


async def _sign_top(method: str, params: dict, app_key: str, app_secret: str) -> dict:
    """Sign AliExpress TOP request."""
    ts = str(int(time.time() * 1000))
    all_params = {"app_key": app_key, "sign_method": "sha256", "timestamp": ts, "method": method, **params}
    msg = "".join(f"{k}{v}" for k, v in sorted(all_params.items()))
    sig = hmac.new(app_secret.encode(), msg.encode(), hashlib.sha256).hexdigest().upper()
    all_params["sign"] = sig
    return all_params


async def _find_click_by_tracking(db: AsyncSession, tracking_id: str, provider: str) -> Optional[str]:
    """Try to find the click_id that originated this conversion."""
    since = datetime.utcnow() - timedelta(days=30)
    r = await db.execute(
        select(ClickEvent.id)
        .where(ClickEvent.provider == provider)
        .where(ClickEvent.clicked_at >= since)
        .order_by(ClickEvent.clicked_at.desc())
        .limit(1)
    )
    row = r.scalar()
    return str(row) if row else None


async def _save_conversion(
    db: AsyncSession,
    external_order_id: str,
    provider: str,
    product_title: str,
    sale_price: float,
    commission_rate: float,
    commission_value: float,
    status: str,
    click_id: Optional[str] = None,
) -> bool:
    """Save conversion if not already saved (idempotent via external_order_id check)."""
    r = await db.execute(
        select(ConversionEvent).where(ConversionEvent.external_order_id == external_order_id)
    )
    if r.scalar():
        return False  # already saved

    conv = ConversionEvent(
        click_id=click_id,
        external_order_id=external_order_id,
        provider=provider,
        product_title=product_title,
        sale_price=sale_price,
        commission_rate=commission_rate,
        commission_value=commission_value,
        status=status,
    )
    db.add(conv)
    await db.commit()
    return True


async def poll_aliexpress_orders(db: AsyncSession, since_hours: int = 2) -> list[dict]:
    """Poll AliExpress affiliate orders via aliexpress.affiliate.order.list.by.index."""
    if not settings.ALIEXPRESS_APP_KEY or not settings.ALIEXPRESS_APP_SECRET:
        return []

    now = datetime.utcnow()
    since = now - timedelta(hours=since_hours)
    fmt = "%Y-%m-%d %H:%M:%S"

    params = {
        "start_time": since.strftime(fmt),
        "end_time": now.strftime(fmt),
        "page_no": "1",
        "page_size": "50",
    }
    if settings.ALIEXPRESS_TRACKING_ID:
        params["tracking_id"] = settings.ALIEXPRESS_TRACKING_ID

    signed = await _sign_top(
        "aliexpress.affiliate.order.list.by.index", params,
        settings.ALIEXPRESS_APP_KEY, settings.ALIEXPRESS_APP_SECRET
    )

    saved = []
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post("https://api-sg.aliexpress.com/sync", data=signed)
            data = r.json()

        resp = data.get("aliexpress_affiliate_order_list_by_index_response", {}).get("resp_result", {})
        if resp.get("resp_code") != 200:
            logger.warning(f"AliExpress orders: {resp.get('resp_msg')}")
            return []

        orders = resp.get("result", {}).get("orders", {}).get("order", [])
        for order in orders:
            order_id = str(order.get("order_id", ""))
            status_raw = order.get("order_status", "")
            if "Completed" in status_raw or "Confirmed" in status_raw:
                status = "confirmed"
            elif "refund" in status_raw.lower():
                status = "rejected"
            else:
                status = "pending"

            sale_price = float(order.get("order_amount", 0) or 0)
            commission = float(order.get("estimated_paid_commission", 0) or 0)
            commission_rate_str = str(order.get("commission_rate", "0") or "0").replace("%", "")
            commission_rate = float(commission_rate_str or 0)
            title = (order.get("product_name", "") or "")[:200]

            click_id = await _find_click_by_tracking(db, settings.ALIEXPRESS_TRACKING_ID or "", "aliexpress")
            ok = await _save_conversion(
                db, f"ali_{order_id}", "aliexpress", title,
                sale_price, commission_rate, commission, status, click_id
            )
            if ok:
                saved.append({"order_id": order_id, "status": status, "commission": commission})
    except Exception as e:
        logger.error(f"AliExpress order polling failed: {e}")

    return saved


async def poll_lomadee_orders(db: AsyncSession, since_hours: int = 2) -> list[dict]:
    """Poll Lomadee commission report."""
    if not settings.LOMADEE_API_KEY or not settings.LOMADEE_SOURCE_ID:
        return []

    now = datetime.utcnow()
    since = now - timedelta(hours=since_hours)

    saved = []
    try:
        url = f"https://api.lomadee.com/v3/{settings.LOMADEE_SOURCE_ID}/report/commission"
        params = {
            "startDate": since.strftime("%Y-%m-%d"),
            "endDate": now.strftime("%Y-%m-%d"),
            "token": settings.LOMADEE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params)
            data = r.json()

        commissions = data.get("commissions", []) or []
        for item in commissions:
            order_id = str(item.get("orderId", item.get("id", "")))
            if not order_id:
                continue
            sale_price = float(item.get("saleValue", 0) or 0)
            commission_value = float(item.get("commissionValue", 0) or 0)
            commission_rate = (commission_value / sale_price * 100) if sale_price else 0
            title = (item.get("productName", item.get("offerName", "")) or "")[:200]
            status_raw = str(item.get("status", "pending")).lower()
            status = (
                "confirmed" if "approv" in status_raw or "paid" in status_raw else
                "rejected" if "reject" in status_raw or "cancel" in status_raw else
                "pending"
            )

            click_id = await _find_click_by_tracking(db, "", "lomadee")
            ok = await _save_conversion(
                db, f"lom_{order_id}", "lomadee", title,
                sale_price, commission_rate, commission_value, status, click_id
            )
            if ok:
                saved.append({"order_id": order_id, "status": status, "commission": commission_value})
    except Exception as e:
        logger.error(f"Lomadee commission polling failed: {e}")

    return saved


async def handle_ml_webhook(data: dict, db: AsyncSession) -> dict:
    """
    ML sends: { resource: "/orders/123456789", user_id: 123, topic: "orders" }
    Then we call GET /orders/{id} to get the full order.
    """
    topic = data.get("topic", "")
    resource = data.get("resource", "")

    if topic not in ("orders", "merchant_orders"):
        return {"ok": True, "skipped": True}

    order_id = resource.split("/")[-1]
    token = settings.MERCADOLIVRE_ACCESS_TOKEN
    if not token:
        return {"ok": False, "error": "no token"}

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"https://api.mercadolibre.com/orders/{order_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code != 200:
                return {"ok": False, "error": f"ML API {r.status_code}"}
            order = r.json()

        total = float(order.get("total_amount", 0) or 0)
        status_raw = order.get("status", "")
        status = (
            "confirmed" if status_raw in ("paid", "approved") else
            "rejected" if status_raw in ("cancelled", "refunded") else
            "pending"
        )

        items = order.get("order_items", [])
        title = items[0].get("item", {}).get("title", "ML Order") if items else "ML Order"

        commission_rate = 4.0
        commission_value = total * 0.04

        click_id = await _find_click_by_tracking(db, str(order_id), "mercadolivre")
        await _save_conversion(
            db, f"ml_{order_id}", "mercadolivre", title[:200],
            total, commission_rate, commission_value, status, click_id
        )

        return {"ok": True}
    except Exception as e:
        logger.error(f"ML webhook handler error: {e}")
        return {"ok": False, "error": str(e)}


async def poll_all_conversions(db: AsyncSession) -> dict:
    """Run all polling tasks and return summary."""
    results: dict[str, list] = {"aliexpress": [], "lomadee": []}
    tasks = [
        ("aliexpress", poll_aliexpress_orders(db)),
        ("lomadee", poll_lomadee_orders(db)),
    ]
    for name, coro in tasks:
        try:
            results[name] = await coro
        except Exception as e:
            logger.error(f"Conversion poll {name}: {e}")

    total_new = sum(len(v) for v in results.values())
    logger.info(f"Conversion poll complete: {total_new} new conversions")
    return {k: len(v) for k, v in results.items()}
