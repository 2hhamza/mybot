import sqlite3
import re
import asyncio
from datetime import datetime, timedelta
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

# ------ تعريف حالات المحادثة ------
(
    START,
    MAIN_MENU,
    SET_TYPE,
    SET_TIME,
    MANAGE_ALERTS
) = range(5)

# ------ أنواع الرسائل ------
MESSAGE_TYPES = {
    "الحوقلة": "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ🤍",
    "الاستغفار": "أَسْتَغْفِرُ اللَّهَ العَظِيمَ الَّذِي لَا إِلَهَ إِلَّا هُوَ الحَيُّ القَيُّومُ وَأَتُوبُ إِلَيْهِ. 🌿",
    "الصلاة على النبي": "اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ. ﷺ🌺",
    "الصلاة الإبراهيمية": "اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ، كَمَا صَلَّيْتَ عَلَى إِبْرَاهِيمَ وَعَلَى آلِ إِبْرَاهِيمَ، وَبَارِكْ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ، كَمَا بَارَكْتَ عَلَى إِبْرَاهِيمَ وَعَلَى آلِ إِبْرَاهِيمَ، فِي العَالَمِينَ إِنَّكَ حَمِيدٌ مَجِيدٌ☘️",
    "التسبيح": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ العَظِيمِ✨",
    "دعاء يونس": "لَا إِلَٰهَ إِلَّا أَنتَ سُبْحَانَكَ إِنِّي كُنتُ مِنَ الظَّالِمِينَ🌊"
}

# ------ قاعدة البيانات ------
conn = sqlite3.connect('subscribers.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS alerts
             (user_id INTEGER, alert_type TEXT, interval INTEGER, next_send TEXT, 
              PRIMARY KEY (user_id, alert_type))''')
conn.commit()

# ------ الرسائل الثابتة ------
INTRODUCTION = """🌺 مرحبًا في بوت مُنبِه المُسلِم 🌺

هذا البوت صدقة جارية نرجو من الله القبول،
كل ما نريده هو الدعاء لنا بظهر الغيب 🤍"""

# ------ لوحات المفاتيح التفاعلية ------
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة تنبيه جديد", callback_data='add_alert')],
        [InlineKeyboardButton("📋 قائمة تنبيهاتي", callback_data='my_alerts')]
    ])

def type_selection_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("الحوقلة 🤍", callback_data='type_الحوقلة'),
         InlineKeyboardButton("الاستغفار 🌿", callback_data='type_الاستغفار')],
        [InlineKeyboardButton("الصلاة على النبي 🌺", callback_data='type_الصلاة على النبي'),
         InlineKeyboardButton("الصلاة الإبراهيمية ☘️", callback_data='type_الصلاة الإبراهيمية')],
        [InlineKeyboardButton("التسبيح ✨", callback_data='type_التسبيح'),
         InlineKeyboardButton("دعاء يونس 🌊", callback_data='type_دعاء يونس')]
    ])

def time_selection_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("١٥ دقيقة ⏰", callback_data='time_15'),
         InlineKeyboardButton("٣٠ دقيقة 🕑", callback_data='time_30')],
        [InlineKeyboardButton("١ ساعة 🕐", callback_data='time_60'),
         InlineKeyboardButton("٢ ساعة 🕝", callback_data='time_120')],
        [InlineKeyboardButton("مخصص ⚙️", callback_data='custom_time')]
    ])

def settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔕 إلغاء جميع التنبيهات", callback_data='unsubscribe_all')]
    ])

# ------ 핸لدير الأساسية ------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        INTRODUCTION,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ابدأ الاستخدام", callback_data='start_using')]
        ])
    )
    return START

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "القائمة الرئيسية:",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU

async def add_new_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 اختر نوع التذكير:",
        reply_markup=type_selection_keyboard()
    )
    return SET_TYPE

async def handle_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    alert_type = query.data.split('_')[1]
    context.user_data['alert_type'] = alert_type
    await query.edit_message_text(
        "⏳ اختر الفترة الزمنية:",
        reply_markup=time_selection_keyboard()
    )
    return SET_TIME

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'custom_time':
        await query.edit_message_text("⌨️ الرجاء إدخال المدة بالدقائق (مثال: 45)")
        return SET_TIME
    
    time_map = {'time_15': 15, 'time_30': 30, 'time_60': 60, 'time_120': 120}
    interval = time_map[query.data]
    user_id = query.from_user.id
    alert_type = context.user_data['alert_type']
    
    next_time = datetime.now() + timedelta(minutes=interval)
    c.execute('''INSERT OR REPLACE INTO alerts VALUES (?, ?, ?, ?)''',
              (user_id, alert_type, interval, next_time.isoformat()))
    conn.commit()
    
    await query.edit_message_text(
        f"✅ تم تعيين تنبيه {alert_type} كل {interval} دقيقة!\n📩 أول تذكير:\n{MESSAGE_TYPES[alert_type]}"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def handle_custom_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if not re.match(r'^\d+$', user_input):
        await update.message.reply_text("❌ الرجاء إدخال أرقام فقط")
        return SET_TIME
    
    interval = int(user_input)
    user_id = update.message.from_user.id
    alert_type = context.user_data['alert_type']
    
    next_time = datetime.now() + timedelta(minutes=interval)
    c.execute('''INSERT OR REPLACE INTO alerts VALUES (?, ?, ?, ?)''',
              (user_id, alert_type, interval, next_time.isoformat()))
    conn.commit()
    
    await update.message.reply_text(
        f"✅ تم تعيين تنبيه {alert_type} كل {interval} دقيقة!\n📩 أول تذكير:\n{MESSAGE_TYPES[alert_type]}"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def show_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    alerts = c.execute('''SELECT alert_type, interval FROM alerts WHERE user_id = ?''', (user_id,)).fetchall()
    
    if not alerts:
        await query.edit_message_text("⚠️ لم تقم بإضافة أي تنبيهات بعد\nارسل /start واضف تنبيهك المفضل")
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton(f"{alert[0]} - كل {alert[1]} دقيقة", callback_data=f"edit_{alert[0]}")] for alert in alerts]
    await query.edit_message_text(
        "🔔 تنبيهاتك الحالية، اضغط على التنبيه لحذفه",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MANAGE_ALERTS

async def delete_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    alert_type = query.data.split('_')[1]
    user_id = query.from_user.id
    
    c.execute('''DELETE FROM alerts WHERE user_id = ? AND alert_type = ?''', (user_id, alert_type))
    conn.commit()
    
    await query.edit_message_text(
        f"✅ تم حذف تنبيهات {alert_type} بنجاح",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU

async def unsubscribe_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    c.execute('''DELETE FROM alerts WHERE user_id = ?''', (user_id,))
    conn.commit()
    
    await query.edit_message_text(
        "تم إزالة جميع التنبيهات بنجاح ✅\nلإضافة تنبيهات جديدة، ارسل /start"
    )
    return ConversationHandler.END

# ------ الأوامر النصية ------
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "القائمة الرئيسية:",
        reply_markup=main_menu_keyboard()
    )
    return MAIN_MENU

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_alerts(update, context)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ الإعدادات:",
        reply_markup=settings_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 الدعم الفني:\n\nللإبلاغ عن مشكلة أو استفسار، تواصل مع المطور: @Muslim_2H_supportbot"
    )

# ------ المهمة الدورية ------
async def send_alerts(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    alerts = c.execute('''SELECT user_id, alert_type, interval FROM alerts WHERE next_send <= ?''', 
                     (now.isoformat(),)).fetchall()
    
    for alert in alerts:
        user_id, alert_type, interval = alert
        next_time = now + timedelta(minutes=interval)
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=MESSAGE_TYPES[alert_type]
            )
            c.execute('''UPDATE alerts SET next_send = ? WHERE user_id = ? AND alert_type = ?''',
                     (next_time.isoformat(), user_id, alert_type))
            conn.commit()
            
        except Exception as e:
            print(f"Error: {e}")

# ------ تشغيل خادم ويب بسيط ------
async def handle_health_check(request):
    return web.Response(text="🤖 البوت يعمل بنجاح!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=8080)
    await site.start()
    print("🌐 خادم الويب يعمل على المنفذ 8080")

# ------ الدالة الرئيسية ------
async def main():
    TOKEN = "7543964180:AAHPhEJ8TOcENqsM-FXqkFUJaUhNrBbV8r8"
    app = (
        Application.builder()
        .token(TOKEN)
        .arbitrary_callback_data(True)  # إصلاح تحذير per_message
        .build()
    )
    
    # ------ إعداد ال Handlers ------
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START: [CallbackQueryHandler(handle_main_menu, pattern='^start_using$')],
            MAIN_MENU: [
                CallbackQueryHandler(add_new_alert, pattern='^add_alert$'),
                CallbackQueryHandler(show_alerts, pattern='^my_alerts$'),
            ],
            SET_TYPE: [CallbackQueryHandler(handle_type_selection, pattern='^type_')],
            SET_TIME: [
                CallbackQueryHandler(handle_time_selection, pattern='^(time_15|time_30|time_60|time_120|custom_time)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_time)
            ],
            MANAGE_ALERTS: [CallbackQueryHandler(delete_alert, pattern='^edit_')]
        },
        fallbacks=[],
        allow_reentry=True
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(unsubscribe_all, pattern='^unsubscribe_all$'))
    
    # ------ تفعيل المهام الدورية ------
    job_queue = app.job_queue
    app.job_queue.run_repeating(send_alerts, interval=30, first=10)
    
    # ------ حذف Webhook السابق ------
    await app.bot.delete_webhook()
    
    # ------ تشغيل الخادم والبوت معًا ------
    await asyncio.gather(
        start_web_server(),
        app.run_polling()
    )

if __name__ == '__main__':
    asyncio.run(main())
