"""
Conversion Tracker — fecha o loop clique → conversão.

Fluxo:
  1. Cron job ou endpoint manual chama poll_all_conversions()
  2. Para cada plataforma, busca orders recentes via API
  3. Tenta vincular order ao click_id via matching por provider/tempo
  4. Salva na tabela conversion_events (evita duplicatas via external_order_id)
  5. Falhas vão para ConversionRetryQueue (até 3 tentativas)
"""
from __future__ import annotations
import hashlib, hmac, time, httpx
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.config import settings
from app.core.logging import logger
from app.models.models import ConversionEvent, ClickEvent, ConversionRetryQueue


async def _sign_top(method: str, params: dict, app_key: str, app_secret: str) -> dict:
    """Sign AliExpress TOP request."""
    ts = str(int(time.time() * 1000))
    all_params = {"app_key": app_key, "sign_method": "sha256", "timestamp": ts, "method": method, **params}
    msg = "".join(f"{k}{v}" for k, v in sorted(all_params.items()))
    sig = hmac.new(app_secret.encode(), msg.encode(), hashlib.sha256).hexdigest().upper()
    all_params["sign"] = sig
    return all_params


async def _find_matching_click(db: AsyncSession, provider: str, product_title: str = None) -> Optional[str]:
    """
    Find best matching click for this conversion.
    Strategy: most recent click from same provider within 30 days.
    Future: fuzzy match product_title.
    """
    since = datetime.utcnow() - timedelta(days=30)
    q = select(ClickEvent.id).where(
        and_(
            ClickEvent.provider == provider,
            ClickEvent.clicked_at >= since,
        )
    ).order_by(ClickEvent.clicked_at.desc()).limit(1)
    r = await db.execute(q)
    row = r.scalar()
    return str(row) if row else None


# Keep old name as alias for backward compat
_find_click_by_tracking = _find_matching_click


async def _save_conversion_safe(
    db: AsyncSession,
    external_order_id: str,
    provider: str,
    product_title: Optional[str],
    sale_price: float,
    commission_rate: float,
    commission_value: float,
    status: str,
    click_id: Optional[str] = None,
) -> bool:
    """Save conversion. On failure, add to retry queue."""
    try:
        # Check duplicate
        r = await db.execute(select(ConversionEvent).where(
            ConversionEvent.external_order_id == external_order_id
        ))
        if r.scalar():
            return False  # already saved

        conv = ConversionEvent(
            external_order_id=external_order_id,
            click_id=click_id,
            provider=provider,
            product_title=product_title[:200] if product_title else None,
            sale_price=sale_price,
            commission_rate=commission_rate,
            commission_value=commission_value,
            status=status,
        )
        db.add(conv)
        await db.commit()
        logger.info(f"Conversion saved: {provider} order={external_order_id} commission={commission_value:.2f} status={status}")
        return True
    except Exception as e:
        logger.error(f"Failed to save conversion {external_order_id}: {type(e).__name__}")
        # Add to retry queue
        try:
            await db.rollback()
            retry = ConversionRetryQueue(
                provider=provider,
                external_order_id=external_order_id,
                payload={
                    "external_order_id": external_order_id,
                    "provider": provider,
                    "product_title": product_title,
                    "sale_price": sale_price,
                    "commission_rate": commission_rate,
                    "commission_value": commission_value,
                    "status": status,
                    "click_id": click_id,
                },
                error=str(e)[:500],
            )
            db.add(retry)
            await db.commit()
        except Exception:
            pass
        return False


# Backward-compat alias used by old code paths
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
    return await _save_conversion_safe(
        db, external_order_id, provider, product_title,
        sale_price, commission_rate, commission_value, status, click_id
    )


async def process_retry_queue(db: AsyncSession) -> int:
    """Process pending items in retry queue. Called hourly."""
    r = await db.execute(
        select(ConversionRetryQueue).where(
            and_(
                ConversionRetryQueue.resolved == False,
                ConversionRetryQueue.attempts < ConversionRetryQueue.max_attempts,
            )
        ).limit(20)
    )
    items = r.scalars().all()
    processed = 0
    for item in items:
        try:
            p = item.payload
            success = await _save_conversion_safe(
                db, p["external_order_id"], p["provider"], p.get("product_title"),
                p.get("sale_price", 0), p.get("commission_rate", 0),
                p.get("commission_value", 0), p.get("status", "pending"),
                p.get("click_id"),
            )
            item.attempts += 1
            item.last_attempt_at = datetime.utcnow()
            item.resolved = success
            if not success:
                item.error = "retry failed"
            await db.commit()
            if success:
                processed += 1
        except Exception as e:
            item.attempts += 1
            item.error = str(e)[:500]
            await db.commit()
    return processed


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

            click_id = await _find_matching_click(db, "aliexpress", title)
            ok = await _save_conversion_safe(
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

            click_id = await _find_matching_click(db, "lomadee", title)
            ok = await _save_conversion_safe(
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

        commission_rate = None
        commission_value = None

        click_id = await _find_matching_click(db, "mercadolivre", title[:200])
        await _save_conversion_safe(
            db, f"ml_{order_id}", "mercadolivre", title[:200],
            total, commission_rate, commission_value, status, click_id
        )

        return {"ok": True}
    except Exception as e:
        logger.error(f"ML webhook handler error: {e}")
        return {"ok": False, "error": str(e)}


async def poll_all_conversions(db: AsyncSession) -> dict:
    """Run all polling with detailed logging."""
    start = datetime.utcnow()
    results = {}

    logger.info(f"[ConversionPoll] Starting at {start.strftime('%H:%M:%S')}")

    for name, coro_fn in [("aliexpress", poll_aliexpress_orders), ("lomadee", poll_lomadee_orders), ("shopee", poll_shopee_conversions)]:
        try:
            saved = await coro_fn(db)
            results[name] = {"saved": len(saved), "items": saved}
            logger.info(f"[ConversionPoll] {name}: {len(saved)} new conversions")
        except Exception as e:
            results[name] = {"saved": 0, "error": str(e)}
            logger.error(f"[ConversionPoll] {name} failed: {e}")

    # Process retry queue
    retried = await process_retry_queue(db)
    results["retried"] = retried

    elapsed = (datetime.utcnow() - start).total_seconds()
    logger.info(f"[ConversionPoll] Done in {elapsed:.1f}s — {sum(r.get('saved', 0) if isinstance(r, dict) else 0 for r in results.values())} total new")

    return {k: (v.get("saved", v) if isinstance(v, dict) else v) for k, v in results.items()}


# ─── Shopee conversion polling ────────────────────────────────────────────────

async def poll_shopee_conversions(db: AsyncSession, since_hours: int = 2) -> list[dict]:
    """
    Busca conversões da Shopee via GraphQL Affiliate API.
    Retorna lista de conversões novas salvas.
    """
    import hashlib, time, httpx, json

    app_id = settings.SHOPEE_APP_ID
    secret = settings.SHOPEE_SECRET
    if not app_id or not secret:
        return []

    now = datetime.utcnow()
    since = now - timedelta(hours=since_hours)

    query = """
    {
      conversionReport(
        purchaseTimeStart: %d
        purchaseTimeEnd: %d
        conversionStatus: ALL
        limit: 50
      ) {
        nodes {
          clickTime
          purchaseTime
          conversionStatus
          estimatedTotalCommission
          orders {
            orderId
            orderStatus
            items {
              itemId
              itemName
              actualAmount
              itemTotalCommission
              itemSellerCommissionRate
              fraudStatus
            }
          }
        }
        pageInfo { hasNextPage }
      }
    }
    """ % (int(since.timestamp()), int(now.timestamp()))

    body = json.dumps({"query": query})
    ts = int(time.time())
    sig = hashlib.sha256(f"{app_id}{ts}{body}{secret}".encode()).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={app_id},Timestamp={ts},Signature={sig}",
    }

    saved = []
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://open-api.affiliate.shopee.com.br/graphql",
                content=body, headers=headers
            )
        d = r.json()
        errors = d.get("errors", [])
        if errors:
            logger.warning(f"Shopee conversion API: {errors[0].get('message','')}")
            return []

        nodes = d.get("data", {}).get("conversionReport", {}).get("nodes", []) or []
        for node in nodes:
            status_raw = node.get("conversionStatus", "")
            status = "confirmed" if "COMPLETED" in status_raw else \
                     "rejected"  if "CANCELLED" in status_raw else "pending"

            commission_total = float(node.get("estimatedTotalCommission", 0) or 0)
            orders = node.get("orders", []) or []

            for order in orders:
                order_id = str(order.get("orderId", ""))
                if not order_id:
                    continue

                items = order.get("items", []) or []
                for item in items:
                    if item.get("fraudStatus") == "FRAUDULENT":
                        continue

                    external_id = f"shopee_{order_id}_{item.get('itemId','')}"
                    sale_price = float(item.get("actualAmount", 0) or 0)
                    commission_value = float(item.get("itemTotalCommission", 0) or 0)
                    commission_rate = float(item.get("itemSellerCommissionRate", 0) or 0)
                    title = str(item.get("itemName", ""))[:200]

                    click_id = await _find_matching_click(db, "shopee", title)
                    ok = await _save_conversion_safe(
                        db, external_id, "shopee", title,
                        sale_price, commission_rate, commission_value, status, click_id
                    )
                    if ok:
                        saved.append({"order_id": order_id, "status": status,
                                      "commission": commission_value})
                        logger.info(f"Shopee: salvo order={order_id} item={title[:40]} "
                                    f"comissão=R${commission_value:.2f}")
    except Exception as e:
        logger.error(f"Shopee conversion polling failed: {type(e).__name__}")

    return saved
