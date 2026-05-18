"""BestPriceToday Telegram Bot
Usuario manda produto → busca ofertas → retorna com links afiliados rastreados
"""
import asyncio
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from app.services.search import search_all
from app.core.config import settings
from app.core.logging import logger


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍️ *BestPriceToday*\n\n"
        "Me manda o nome do produto e eu busco o menor preço em todas as lojas com link de afiliado rastreado!\n\n"
        "Exemplos:\n"
        "• `iPhone 16 Pro 256GB`\n"
        "• `Nike Air Force 42`\n"
        "• `RTX 4070 Super`\n"
        "• `Notebook Dell i7`\n\n"
        "🔍 Use /alertas para criar alertas de preço",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query or len(query) < 2:
        return

    msg = await update.message.reply_text(f"🔍 Buscando *{query}*...", parse_mode="Markdown")

    try:
        result = await search_all(query=query, limit=5)

        if not result.offers:
            await msg.edit_text(
                f"😕 Nenhum resultado para *{query}*\n\nTente outro termo.",
                parse_mode="Markdown"
            )
            return

        lines = [f"🛍️ *{query}*", f"_{result.total} {'oferta' if result.total == 1 else 'ofertas'} · {result.took_ms}ms_\n"]
        buttons = []

        PROVIDER_EMOJI = {
            "mercadolivre": "🟡", "amazon": "📦", "shopee": "🟠",
            "kabum": "🟢", "aliexpress": "🔴", "lomadee": "🟣", "awin": "🔵",
        }

        for i, offer in enumerate(result.offers[:5]):
            emoji = PROVIDER_EMOJI.get(offer.provider, "🏪")
            rank = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]

            price_str = f"R$ {offer.final_price:,.2f}".replace(",", ".") if offer.final_price and offer.final_price > 0.02 else "Preço indisponível"
            free_ship = "✅ Frete grátis" if offer.shipping_free else ""
            discount = f"🔥 -{offer.discount_percent:.0f}%" if offer.discount_percent >= 3 and not offer.is_fake_discount else ""
            economy = f"💰 Economize R$ {offer.economy:.2f}" if offer.economy > 0.5 else ""

            parts = [p for p in [price_str, free_ship, discount, economy] if p]

            lines.append(
                f"{rank} {emoji} *{offer.provider.upper()}*\n"
                f"{' · '.join(parts)}\n"
                f"📦 _{offer.title[:60]}..._\n"
                f"⭐ Score: {offer.score:.0f}/100\n"
            )

            if offer.affiliate_url:
                provider_name = offer.provider.replace("mercadolivre", "Mercado Livre").title()
                buttons.append([InlineKeyboardButton(
                    f"{rank} {price_str} — {provider_name}",
                    url=offer.affiliate_url
                )])

        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None

        await msg.edit_text(
            text[:4096],
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

        # Auto-share exceptional deals to channel
        channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "")
        if result.offers and result.offers[0].score >= 85 and channel_id:
            asyncio.create_task(auto_share_to_channel(result.offers[0], query))

    except Exception as e:
        logger.error(f"BestPriceToday bot error: {e}")
        await msg.edit_text("❌ Erro ao buscar. Tente novamente em instantes.")


async def auto_share_to_channel(offer, query: str):
    """Share an exceptional deal to the channel."""
    try:
        from app.workers.channel_broadcaster import post_offer_to_channel
        await post_offer_to_channel(offer.__dict__ if hasattr(offer, '__dict__') else offer)
    except Exception as e:
        logger.warning(f"auto_share_to_channel error: {e}")


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔍 Buscando top ofertas do dia...", parse_mode="Markdown")
    try:
        queries = ["smartphone", "notebook", "fone bluetooth", "smartwatch", "smart tv"]
        lines = ["🏆 *TOP OFERTAS DO DIA*\n"]
        buttons = []
        found = 0
        import httpx
        API_URL = os.getenv("API_URL", "https://alessandro2090-bestpricetoday-api.hf.space")
        PROVIDER_EMOJI = {
            "mercadolivre": "🟡", "amazon": "📦", "shopee": "🟠",
            "kabum": "🟢", "aliexpress": "🔴", "lomadee": "🟣", "awin": "🔵",
        }
        for query in queries:
            if found >= 5:
                break
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(f"{API_URL}/api/v1/search", params={"q": query, "limit": 1})
                offers = r.json().get("offers", [])
                if not offers:
                    continue
                offer = offers[0]
                if not offer.get("affiliate_url") or offer.get("final_price", 0) < 20:
                    continue
                emoji = PROVIDER_EMOJI.get(offer.get("provider", ""), "🏪")
                rank = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][found]
                price = offer.get("final_price", 0)
                discount = offer.get("discount_percent", 0)
                title = (offer.get("title") or "")[:60]
                price_str = f"R$ {price:,.2f}".replace(",", ".")
                disc_str = f" 🔥-{discount:.0f}%" if discount >= 5 and not offer.get("is_fake_discount") else ""
                lines.append(f"{rank} {emoji} *{offer.get('provider','').upper()}* — {price_str}{disc_str}")
                lines.append(f"   _{title}..._\n")
                if offer.get("affiliate_url"):
                    buttons.append([InlineKeyboardButton(f"{rank} {price_str} — {query.title()}", url=offer["affiliate_url"])])
                found += 1
        if not found:
            await msg.edit_text("😕 Nenhuma oferta encontrada agora.")
            return
        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup(buttons) if buttons else None
        await msg.edit_text(text[:4096], parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"cmd_top error: {e}")
        await msg.edit_text("❌ Erro ao buscar. Tente novamente.")


async def cmd_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "")
    channel_link = channel_id if channel_id.startswith("@") else "@BestPriceTodayBR"
    await update.message.reply_text(
        f"📣 *Canal BestPriceToday*\n\n"
        f"Receba ofertas automaticamente todo dia!\n\n"
        f"👉 Entre no canal: {channel_link}\n\n"
        f"🛍️ Postamos as melhores ofertas com:\n"
        f"• Descontos reais verificados\n"
        f"• Frete grátis quando disponível\n"
        f"• Links afiliados diretos\n\n"
        f"🌐 bestpricetoday.vercel.app",
        parse_mode="Markdown"
    )


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instrui o usuário a criar alertas via site, passando o telegram_id."""
    telegram_id = str(update.effective_user.id)
    await update.message.reply_text(
        "🔔 *Alertas de Preço*\n\n"
        "Acesse o site para criar alertas. Seus alertas serão vinculados ao seu Telegram:\n\n"
        f"🌐 https://bestpricetoday.vercel.app/alertas\n\n"
        "Quando o preço cair, você receberá uma notificação aqui mesmo! 🎉\n\n"
        f"_Seu ID Telegram: `{telegram_id}`_",
        parse_mode="Markdown"
    )


async def start_bot_polling():
    """Run bot polling in background — for cloud deployment."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, bot disabled")
        return

    application = (
        ApplicationBuilder()
        .token(token)
        .build()
    )
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("alertas", cmd_alertas))
    application.add_handler(CommandHandler("top", cmd_top))
    application.add_handler(CommandHandler("canal", cmd_canal))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

    logger.info("Starting Telegram bot polling (cloud mode)...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def run():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("canal", cmd_canal))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

    logger.info("BestPriceToday Telegram bot started")
    app.run_polling()


if __name__ == "__main__":
    run()
