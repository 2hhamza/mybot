import os
import asyncio
import logging
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.environ.get("TOKEN")  # Must be set in Render's environment variables
PORT = 8080  # Render's required port

# Conversation states
CHOOSE_SINS, CUSTOM_SIN = range(2)

# ======================
# Bot Handlers
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("الذنوب المعتادة", callback_data="common_sins")],
        [InlineKeyboardButton("ذنب مخصص", callback_data="custom_sin")]
    ]
    await update.message.reply_text(
        "مرحبا! أنا بوت الاستغفار. اختر نوع الذنب الذي تريد الاستغفار عنه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_SINS

async def handle_common_sins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("الغيبة", callback_data="الغيبة")],
        [InlineKeyboardButton("النميمة", callback_data="النميمة")],
        [InlineKeyboardButton("السب والشتم", callback_data="السب والشتم")]
    ]
    await query.edit_message_text(
        text="اختر من الذنوب الشائعة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CUSTOM_SIN

async def handle_custom_sin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("اكتب الذنب الذي تريد الاستغفار عنه:")
    return CUSTOM_SIN

async def handle_sin_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sin = update.message.text
    await update.message.reply_text(
        f"استغفر الله العظيم من ذنب {sin} وأتوب إليه ✨\n"
        "اضغط /start للعودة إلى القائمة الرئيسية"
    )
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "common_sins":
        await handle_common_sins(update, context)
    elif query.data == "custom_sin":
        await handle_custom_sin(update, context)
    else:
        await handle_sin_selection(update, context)

# ==================
# Web Server Setup
# ==================

async def health_check(request):
    return web.Response(text="Bot is running!")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")
    return runner

# ==============
# Bot Setup
# ==============

async def setup_bot():
    application = Application.builder().token(TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_SINS: [CallbackQueryHandler(button_handler)],
            CUSTOM_SIN: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sin_selection)
            ]
        },
        fallbacks=[],
        per_message=True  # Required for proper callback handling
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Initialize bot
    await application.initialize()
    await application.start()
    logger.info("Bot started polling for updates")
    return application

# ==============
# Main Function
# ==============

async def main():
    web_runner = await run_web_server()
    bot_app = await setup_bot()

    try:
        # Keep both services running
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await bot_app.stop()
        await bot_app.shutdown()
        await web_runner.cleanup()
        logger.info("Services stopped gracefully")

if __name__ == "__main__":
    asyncio.run(main())
