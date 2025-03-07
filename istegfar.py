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
PORT = 8080  # Required for Render web service

# Conversation states
START, CHOOSE_SINS, CUSTOM_SIN = range(3)

# ======================
# Telegram Bot Handlers
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initial command to start the bot"""
    keyboard = [
        [InlineKeyboardButton("الذنوب المعتادة", callback_data="common_sins")],
        [InlineKeyboardButton("ذنب مخصص", callback_data="custom_sin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "مرحبا! أنا بوت الاستغفار. اختر نوع الذنب الذي تريد الاستغفار عنه:",
        reply_markup=reply_markup
    )
    return CHOOSE_SINS

async def handle_common_sins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle common sins selection"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("الغيبة", callback_data="الغيبة")],
        [InlineKeyboardButton("النميمة", callback_data="النميمة")],
        [InlineKeyboardButton("السب والشتم", callback_data="السب والشتم")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="اختر من الذنوب الشائعة:",
        reply_markup=reply_markup
    )
    return CUSTOM_SIN

async def handle_custom_sin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom sin input"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("اكتب الذنب الذي تريد الاستغفار عنه:")
    return CUSTOM_SIN

async def handle_sin_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle final sin selection/input"""
    sin = update.message.text
    await update.message.reply_text(f"استغفر الله العظيم من ذنب {sin} وأتوب إليه ✨\n"
                                    "اضغط /start للعودة إلى القائمة الرئيسية")
    return ConversationHandler.END

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
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

async def web_handler(request):
    """Basic web handler to keep Render alive"""
    return web.Response(text="Bot is running!")

async def start_web_server():
    """Start a simple web server"""
    server = web.Application()
    server.router.add_get("/", web_handler)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, port=PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")
    
    # Keep server running indefinitely
    while True:
        await asyncio.sleep(3600)

# ==============
# Main Function
# ==============

async def main():
    """Main async function to run both bot and web server"""
    # Create bot application
    app = Application.builder().token(TOKEN).build()

    # Setup conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_SINS: [CallbackQueryHandler(button)],
            CUSTOM_SIN: [
                CallbackQueryHandler(button),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sin_selection)
            ]
        },
        fallbacks=[],
        per_message=False
    )

    # Register handlers
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button))

    # Start both bot and web server
    await asyncio.gather(
        app.run_polling(),
        start_web_server()
    )

if __name__ == "__main__":
    asyncio.run(main())
