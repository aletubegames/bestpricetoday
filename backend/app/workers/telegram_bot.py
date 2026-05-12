"""Telegram bot for BestPriceToday."""
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from app.core.config import settings
from app.services.search import search_all
from app.core.logging import logger


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍️ *BestPriceToday Bot*\n\n"
        "Me manda o nome do produto e eu encontro o menor preço em todas as lojas!\n\n"
        "Exemplo:\n`Nike Air Force tamanho 42`\n`iPhone 15 128GB`\n`Notebook i7`",
        parse_mode="Markdown"
    )


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query or len(query) < 2:
        return

    msg = await update.message.reply_text(f"🔍 Buscando *{query}*...", parse_mode="Markdown")

    try:
        result = await search_all(query=query, limit=5)

        if not result.offers:
            await msg.edit_text("❌ Nenhum resultado encontrado.")
            return

        text = f"🛍️ *{query}*\n_{result.total} ofertas em {result.took_ms}ms_\n\n"
        buttons = []

        for i, offer in enumerate(result.offers[:5], 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏷️"
            free = "✅ Frete grátis" if offer.shipping_free else f"🚚 +R${offer.shipping_price:.0f}"
            coupon = f"\n🎟️ Cupom: `{offer.coupon_code}`" if offer.coupon_code else ""
            economy = f"\n💰 Economia: R${offer.economy:.2f}" if offer.economy > 0 else ""

            text += (
                f"{emoji} *{offer.provider.value.upper()}*\n"
                f"💵 R${offer.final_price:.2f} {free}{coupon}{economy}\n"
                f"📦 {offer.title[:50]}...\n"
                f"⭐ Score: {offer.score:.0f}/100\n\n"
            )
            buttons.append([InlineKeyboardButton(
                f"{emoji} Comprar na {offer.provider.value.title()} — R${offer.final_price:.2f}",
                url=offer.affiliate_url
            )])

        await msg.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Telegram search error: {e}")
        await msg.edit_text("❌ Erro ao buscar. Tente novamente.")


def run_bot():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

    logger.info("Telegram bot started")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
