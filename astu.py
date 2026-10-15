 import csv
import os
import re
from threading import Thread
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

# ================= FLASK KEEP-ALIVE FOR RENDER =================
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "🚀 ASTU Bot is Alive and Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ================= CONFIGURATION =================
TOKEN = "8687801959:AAHf9hw-gpgkIqxseUE3aA2o4jGeaTYOTGo"
ADMIN_ID = 8891900780
CHANNEL_URL = "https://t.me/astutechteam"
ADMIN_USERNAME = "@Selman_Ali"
DB_FILE = "astu_club_members.csv"

LANG, NAME, ASTU_ID, PHONE, YEAR, CLUB, MOTIVATION = range(7)

# ================= MULTI-LANGUAGE DICTIONARY =================
TEXTS = {
    'en': {
        'welcome': "🏛 **Welcome to ASTU Clubs Portal (2027 Edition)** 🚀\n\nJoin the brightest minds at Adama Science & Technology University!",
        'join_btn': "📝 Register for a Club",
        'channel_btn': "📢 Join ASTU Tech Channel",
        'help_btn': "💬 Contact Support",
        'ask_name': "👤 Please enter your **Full Name**:",
        'ask_id': "🆔 Enter your **ASTU ID** (Format: `UGR/43400/19`):",
        'invalid_id': "❌ **Invalid ID Format!**\nPlease use the proper ASTU format (e.g., `UGR/43400/19`).",
        'ask_phone': "📱 Share your **Phone Number** using the button below, or type it (`09...` or `07...`):",
        'share_phone': "📲 Share My Phone Number",
        'invalid_phone': "❌ Invalid phone number! Please enter a valid Ethiopian number.",
        'ask_year': "🎓 Select your **Academic Year**:",
        'ask_club': "🎯 Choose the **ASTU Club** you want to join:",
        'ask_mot': "💡 Briefly tell us your **skills or why you want to join** (1-2 sentences):",
        'success': "✅ **Registration Submitted Successfully!** 🎉\n\nYour application has been sent to our admin for review. Meanwhile, join our official channel!",
    },
    'am': {
        'welcome': "🏛 **እንኳን ወደ ASTU ክለቦች መመዝገቢያ በደህና መጡ (2027)** 🚀\n\nየአዳማ ሳይንስና ቴክኖሎጂ ዩኒቨርሲቲ የቴክኖሎጂና ፈጠራ ቤተሰብን ይቀላቀሉ!",
        'join_btn': "📝 ለክለብ ለመመዝገብ",
        'channel_btn': "📢 ቻናላችንን ይቀላቀሉ",
        'help_btn': "💬 እርዳታ ለማግኘት (Admin)",
        'ask_name': "👤 እባክዎ **ሙሉ ስምዎን** ያስገቡ፦",
        'ask_id': "🆔 የ**ASTU መታወቂያ ቁጥርዎን** ያስገቡ (ለምሳሌ፦ `UGR/43400/19`)፦",
        'invalid_id': "❌ **የተሳሳተ ID አጻጻፍ!**\nእባክዎ ትክክለኛውን የASTU ፎርማት ይጠቀሙ (ምሳሌ፦ `UGR/43400/19`)።",
        'ask_phone': "📱 ከታች ያለውን በተን በመጫን ወይም በመጻፍ **ስልክ ቁጥርዎን** ያስገቡ፦",
        'share_phone': "📲 ስልክ ቁጥሬን ላክ",
        'invalid_phone': "❌ የተሳሳተ ስልክ ቁጥር! እባክዎ ትክክለኛ ቁጥር ያስገቡ።",
        'ask_year': "🎓 **ስንተኛ ዓመት** ተማሪ ነዎት?",
        'ask_club': "🎯 መግባት የሚፈልጉትን **ክለብ** ይምረጡ፦",
        'ask_mot': "💡 ያለዎትን ልዩ ችሎታ ወይም ክለቡን ለምን መቀላቀል እንደፈለጉ በአጭሩ ይጻፉልን፦",
        'success': "✅ **ምዝገባዎ በተሳካ ሁኔታ ተጠናቋል!** 🎉\n\nመረጃዎ ለአድሚኑ ተልኳል። እስከዚያው ግን ቻናላችንን ይቀላቀሉ!",
    },
    'om': {
        'welcome': "🏛 **Baga Gara Galmee Kilaboota ASTU Nagaan Dhuftan (2027)** 🚀\n\nHawaasa teeknooloojii fi kalaqaa ASTUtti makamaa!",
        'join_btn': "📝 Kilabiitti Galmaa'uuf",
        'channel_btn': "📢 Chaanaalii Keenya",
        'help_btn': "💬 Gargaarsaaf (Admin)",
        'ask_name': "👤 Maaloo **Maqaa Guutuu** keessan galchaa:",
        'ask_id': "🆔 **Waraqaa Eenyummaa ASTU (ID)** galchaa (Fkn: `UGR/43400/19`):",
        'invalid_id': "❌ **ID Dogoggoraa!**\nMaaloo haala sirriin barreessaa (Fkn: `UGR/43400/19`).",
        'ask_phone': "📱 **Lakkoofsa Bilbilaa** keessan qoodaa ykn barreessaa:",
        'share_phone': "📲 Lakkoofsa Bilbilaa Ergi",
        'invalid_phone': "❌ Lakkoofsi bilbilaa sirrii miti!",
        'ask_year': "🎓 Barataa **Waggaa Meegaffaa** ti?",
        'ask_club': "🎯 **Kilabii** itti makamuu barbaaddan filadhaa:",
        'ask_mot': "💡 Dandeettii qabdan ykn sababa kilabicha filattaniif gabaabinaan barreessaa:",
        'success': "✅ **Galmeen Keessan Milkaa'eera!** 🎉\n\nOdeeffannoon keessan Admin bira gaheera. Chaanaalii keenyaatti makamaa!",
    },
    'ti': {
        'welcome': "🏛 **እንቋዕ ናብ መመዝገቢ ክለባት ASTU ብደሓን መጻእኩም (2027)** 🚀\n\nናይ ቴክኖሎጂን ምህዞን ስድራቤት ኩኑ!",
        'join_btn': "📝 ንክለብ ንምምዝጋብ",
        'channel_btn': "📢 ቻናልና ተጸንበሩ",
        'help_btn': "💬 ሓገዝ ንምርካብ (Admin)",
        'ask_name': "👤 ብኽብረትኩም **ምሉእ ሽምኩም** የእትዉ፦",
        'ask_id': "🆔 ናይ **ASTU መንነት ቁጽሪ (ID)** የእትዉ (ንኣብነት፦ `UGR/43400/19`)፦",
        'invalid_id': "❌ **ጌጋ ኣጸሓሕፋ ID!**\nብኽብረትኩም ብትኽክል ጸሓፉ (ንኣብነት፦ `UGR/43400/19`)።",
        'ask_phone': "📱 **ቁጽሪ ስልክኹም** ኣብ ታሕቲ ዘሎ መጠወቒ ብምጥዋቕ ወይ ብምጽሓፍ ስደዱ፦",
        'share_phone': "📲 ቁጽሪ ስልከይ ስደድ",
        'invalid_phone': "❌ ጌጋ ቁጽሪ ስልኪ!",
        'ask_year': "🎓 **ክንደይ ዓመት** ተምሃራይ ኢኹም?",
        'ask_club': "🎯 ክትኣትውዎ እትደልዩ **ክለብ** ምረጹ፦",
        'ask_mot': "💡 ዘለኩም ክእለት ወይ ንምንታይ ክትኣትዉ ከም ዝደለኹም ብሓጺሩ ጸሓፉልና፦",
        'success': "✅ **ምዝገባኹም ብዓወት ተዛዚሙ ኣሎ!** 🎉\n\nሓበሬታኹም ናብ ኣድሚን ተላኢኹ ኣሎ። ቻናልና ተጸንበሩ!",
    }
}

CLUBS = [
    "💻 CSEC ASTU (Competitive Programming)",
    "🤖 AI & Robotics Club",
    "🛡️ Cyber Security Club",
    "🚀 Space Science & Astronomy (ESSS)",
    "💡 Innovation & Entrepreneurship",
    "🎨 Media & Digital Arts Club"
]

if not os.path.exists(DB_FILE):
    with open(DB_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["User_ID", "Username", "Full_Name", "ASTU_ID", "Phone", "Year", "Club", "Motivation"])

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'),
         InlineKeyboardButton("🇪🇹 አማርኛ", callback_data='lang_am')],
        [InlineKeyboardButton("🌳 Afaan Oromoo", callback_data='lang_om'),
         InlineKeyboardButton("🌾 ትግርኛ", callback_data='lang_ti')]
    ]
    await update.message.reply_text(
        "🌟 **Welcome to ASTU Smart Portal!**\nPlease select your language / እባክዎ ቋንቋ ይምረጡ፦",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return LANG

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    t = TEXTS[lang]

    keyboard = [
        [InlineKeyboardButton(t['join_btn'], callback_data='start_reg')],
        [InlineKeyboardButton(t['channel_btn'], url=CHANNEL_URL)],
        [InlineKeyboardButton(t['help_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    await query.edit_message_text(t['welcome'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return LANG

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'en')
    await query.edit_message_text(TEXTS[lang]['ask_name'], parse_mode="Markdown")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    lang = context.user_data.get('lang', 'en')
    await update.message.reply_text(TEXTS[lang]['ask_id'], parse_mode="Markdown")
    return ASTU_ID

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    astu_id = update.message.text.strip().upper()
    lang = context.user_data.get('lang', 'en')

    if not re.match(r"^(UGR|PGR|BSC)/\d{4,6}/\d{2}$", astu_id):
        await update.message.reply_text(TEXTS[lang]['invalid_id'], parse_mode="Markdown")
        return ASTU_ID

    context.user_data['astu_id'] = astu_id
    kb = [[KeyboardButton(TEXTS[lang]['share_phone'], request_contact=True)]]
    await update.message.reply_text(
        TEXTS[lang]['ask_phone'],
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
        if not re.match(r"^(\+251|0)(9|7)\d{8}$", phone):
            await update.message.reply_text(TEXTS[lang]['invalid_phone'])
            return PHONE

    context.user_data['phone'] = phone
    msg = await update.message.reply_text("🔄...", reply_markup=ReplyKeyboardRemove())
    await msg.delete()

    years = ["1st Year (Freshman)", "2nd Year", "3rd Year", "4th Year", "5th Year (GC)"]
    keyboard = [[InlineKeyboardButton(y, callback_data=f"yr_{y}")] for y in years]
    await update.message.reply_text(TEXTS[lang]['ask_year'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['year'] = query.data.replace("yr_", "")
    lang = context.user_data.get('lang', 'en')

    keyboard = [[InlineKeyboardButton(c, callback_data=f"club_{i}")] for i, c in enumerate(CLUBS)]
    await query.edit_message_text(TEXTS[lang]['ask_club'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CLUB

async def get_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    club_idx = int(query.data.replace("club_", ""))
    context.user_data['club'] = CLUBS[club_idx]
    lang = context.user_data.get('lang', 'en')

    await query.edit_message_text(TEXTS[lang]['ask_mot'], parse_mode="Markdown")
    return MOTIVATION

async def get_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['motivation'] = update.message.text.strip()
    lang = context.user_data.get('lang', 'en')
    user = update.effective_user
    data = context.user_data

    with open(DB_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([user.id, f"@{user.username}", data['name'], data['astu_id'], data['phone'], data['year'], data['club'], data['motivation']])

    keyboard = [
        [InlineKeyboardButton(TEXTS[lang]['channel_btn'], url=CHANNEL_URL)],
        [InlineKeyboardButton(TEXTS[lang]['help_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    await update.message.reply_text(TEXTS[lang]['success'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    admin_msg = (
        f"🔔 **NEW ASTU CLUB REGISTRATION!** 🔔\n\n"
        f"👤 **Name:** {data['name']}\n"
        f"🆔 **ID:** `{data['astu_id']}`\n"
        f"📱 **Phone:** `{data['phone']}`\n"
        f"🎓 **Year:** {data['year']}\n"
        f"🎯 **Club:** {data['club']}\n"
        f"💡 **Skill/Note:** {data['motivation']}\n"
        f"🔗 **Telegram:** @{user.username or 'No_Username'} (`{user.id}`)"
    )
    admin_kb = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"adm_app_{user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_{user.id}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")
    return ConversationHandler.END

# ================= ADMIN PANEL & ACTIONS =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        total = sum(1 for row in f) - 1

    kb = [[InlineKeyboardButton("📥 Download Excel/CSV Data", callback_data="adm_export")]]
    await update.message.reply_text(
        f"👑 **Welcome Admin Selman!**\n\n📊 **Total Registered Students:** `{total}`\n\nUse the button below to export all student data.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "adm_export":
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(DB_FILE, 'rb'), filename="ASTU_Club_Members.csv", caption="📊 Here is the updated registration list!")
    
    elif data.startswith("adm_app_"):
        student_id = int(data.split("_")[2])
        await context.bot.send_message(
            chat_id=student_id,
            text=f"🎉 **Congratulations!**\nYour ASTU Club application has been **APPROVED** by the Admin! Welcome aboard! 🚀\n\nJoin our channel for updates: {CHANNEL_URL}",
            parse_mode="Markdown"
        )
        await query.edit_message_text(query.message.text + "\n\n✅ **STATUS: APPROVED BY SELMAN**", parse_mode="Markdown")

    elif data.startswith("adm_rej_"):
        student_id = int(data.split("_")[2])
        await context.bot.send_message(
            chat_id=student_id,
            text=f"ℹ️ Thank you for applying to ASTU Clubs. Unfortunately, we couldn't approve your application at this time. Contact {ADMIN_USERNAME} if you have questions."
        )
        await query.edit_message_text(query.message.text + "\n\n❌ **STATUS: REJECTED**", parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled. Type /start to begin again.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG: [
                CallbackQueryHandler(select_language, pattern='^lang_'),
                CallbackQueryHandler(start_registration, pattern='^start_reg$')
            ],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASTU_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            PHONE: [MessageHandler((filters.CONTACT | filters.TEXT) & ~filters.COMMAND, get_phone)],
            YEAR: [CallbackQueryHandler(get_year, pattern='^yr_')],
            CLUB: [CallbackQueryHandler(get_club, pattern='^club_')],
            MOTIVATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_motivation)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('admin', admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern='^adm_'))

    print("🚀 ASTU Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    keep_alive()
    main()
