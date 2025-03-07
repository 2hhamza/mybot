import os
import asyncio
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

# Configuration
TOKEN = os.environ.get("TOKEN")
PORT = 8080  # Render's required port

# Conversation states
START, CHOOSE_SINS, CUSTOM_SIN = range(3)

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
    return web.Response(text="Bot is operational!")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=PORT)
    await site.start()
    print(f"🌐 Web server ready on port {PORT}")
    return runner

# ==============
# Main Setup
# ==============

async def setup_bot():
    application = Application.builder().token(TOKEN).build()

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
        per_message=True  # Critical fix for callback tracking
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    await application.initialize()
    await application.start()
    print("🤖 Bot is now polling for updates")
    return application

# ==============
# Main Function
# ==============

async def main():
    web_runner = await run_web_server()
    bot_app = await setup_bot()
    
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await bot_app.stop()
        await web_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
