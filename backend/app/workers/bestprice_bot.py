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

    except Exception as e:
        logger.error(f"BestPriceToday bot error: {e}")
        await msg.edit_text("❌ Erro ao buscar. Tente novamente em instantes.")


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔔 *Alertas de Preço*\n\n"
        "Em breve você poderá criar alertas e receber notificação quando o preço cair!\n\n"
        "Por enquanto, acesse:\n"
        f"🌐 https://bestpricetoday.vercel.app",
        parse_mode="Markdown"
    )


def run():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

    logger.info("BestPriceToday Telegram bot started")
    app.run_polling()


if __name__ == "__main__":
    run()
