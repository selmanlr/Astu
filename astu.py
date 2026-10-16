import sqlite3
import csv
import os
import re
import urllib.parse
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineQueryResultArticle, InputTextMessageContent
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, InlineQueryHandler, filters, ContextTypes
)

# ================= መሰረታዊ መረጃዎች (CONFIGURATION) =================
TOKEN = "8687801959:AAHf9hw-gpgkIqxseUE3aA2o4jGeaTYOTGo"
ADMIN_ID = 8891900780
CHANNEL_URL = "https://t.me/astutechteam"
ADMIN_USERNAME = "@Selman_Ali"
DB_NAME = "astu_portal.db"

LANG, NAME, ASTU_ID, PHONE, CLUB, SKILL, CONFIRM, BROADCAST_MSG = range(8)

# ================= የዌብሳይት መቆጣጠሪያ (FLASK WEB PORTAL) =================
app_web = Flask(__name__)

@app_web.route('/')
def home():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM members ORDER BY rowid DESC")
    rows = c.fetchall()
    conn.close()

    trs = "".join([
        f"<tr><td>{r['full_name']}</td><td><code>{r['astu_id']}</code></td>"
        f"<td>{r['year']}</td><td>{r['club']}</td><td>{r['status']}</td></tr>"
        for r in rows
    ])
    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>የASTU ክለቦች ዳታቤዝ</title>
        <style>
            body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; padding: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e293b; border-radius: 8px; overflow: hidden; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #334155; }}
            th {{ background: #3b82f6; color: white; }}
            code {{ background: #0f172a; padding: 3px 6px; border-radius: 4px; color: #38bdf8; }}
        </style>
    </head>
    <body>
        <h2>🏛 የASTU ክለቦች የተመዝጋቢዎች ዝርዝር ({len(rows)} ተማሪዎች)</h2>
        <table>
            <tr><th>ሙሉ ስም</th><th>መታወቂያ (ID)</th><th>ዓመት</th><th>ክለብ</th><th>ሁኔታ (Status)</th></tr>
            {trs or '<tr><td colspan="5">እስካሁን የተመዘገበ ተማሪ የለም።</td></tr>'}
        </table>
    </body>
    </html>
    """

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app_web.run(host='0.0.0.0', port=port), daemon=True).start()

# ================= የዳታቤዝ ሲስተም (SQLITE3) =================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS members (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            astu_id TEXT UNIQUE,
            phone TEXT,
            year TEXT,
            club TEXT,
            skill TEXT,
            status TEXT,
            reg_date TEXT
        )''')

def get_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM members WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

def check_id_owner(astu_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM members WHERE UPPER(astu_id)=UPPER(?)", (astu_id,)).fetchone()
        return dict(row) if row else None

def save_member(d):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''INSERT OR REPLACE INTO members VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (d['user_id'], d['username'], d['name'], d['astu_id'], d['phone'], d['year'], d['club'], d['skill'], "በانتظار (Pending) ⏳", now))

def update_db_status(user_id, action):
    with sqlite3.connect(DB_NAME) as conn:
        if action == "approve":
            conn.execute("UPDATE members SET status='ጸድቋል (Approved) ✅' WHERE user_id=?", (user_id,))
        elif action == "reject":
            conn.execute("DELETE FROM members WHERE user_id=?", (user_id,))

# ከID ላይ የትምህርት ዓመትን በራስ-ሰር የሚያውቅ ፈንክሽን
def detect_batch_from_id(astu_id: str) -> str:
    batch_num = int(astu_id.split('/')[-1])
    mapping = {
        19: "1ኛ ዓመት (Freshman)",
        18: "2ኛ ዓመት",
        17: "3ኛ ዓመት",
        16: "4ኛ ዓመት",
        15: "5ኛ ዓመት (GC)"
    }
    return mapping.get(batch_num, f"የ {batch_num} ባች")

# የQR Code መታወቂያ ካርድ መስሪያ
def generate_id_card_url(name, astu_id, club, year):
    qr_data = urllib.parse.quote(f"ASTU VERIFIED MEMBER\nስም: {name}\nID: {astu_id}\nክለብ: {club}\nዓመት: {year}\nያጸደቀው: {ADMIN_USERNAME}")
    return f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&ecc=H&margin=20&color=0f172a&bgcolor=38bdf8&data={qr_data}"

init_db()

# ================= የቋንቋዎች መዝገብ =================
TEXTS = {
    'am': {
        'home': "🏛 **የASTU ክለቦች መመዝገቢያ**\n━━━━━━━━━━━━━━━━━━━━\nእንኳን ወደ አዳማ ሳይንስና ቴክኖሎጂ ዩኒቨርሲቲ ዘመናዊ የክለቦች መመዝገቢያ በደህና መጡ።",
        'reg_btn': "📝 ለክለብ ተመዝገብ",
        'chan_btn': "📢 ቻናላችንን ተቀላቀል",
        'sup_btn': "💬 እርዳታ (Admin)",
        'ask_name': "👤 **ደረጃ 1/4፦** እባክዎ **ሙሉ ስምዎን** ይጻፉ፦",
        'ask_id': "🆔 **ደረጃ 2/4፦** የ**ASTU መታወቂያ ቁጥርዎን** ያስገቡ (ምሳሌ፦ `UGR/43400/19`)\n*(ስንተኛ ዓመት እንደሆኑ ቦቱ ከID-ዎ ላይ ራሱ ያውቀዋል)*፦",
        'err_id': "❌ **የተሳሳተ አጻጻፍ!** እባክዎ በትክክል ይጻፉ (ምሳሌ፦ `UGR/43400/19`)፦",
        'taken_id': "⚠️ **ይህ መታወቂያ ቁጥር ተይዟል!**\nይህ ID (`{id}`) ቀድሞ በ **{name}** ስም ተመዝግቧል! እባክዎ የራስዎን ትክክለኛ ID ያስገቡ፦",
        'ask_ph': "📱 **ደረጃ 3/4፦** የትምህርት ዓመት፦ **{year}** ✅\n\nአሁን ከታች ያለውን በተን በመጫን ወይም በመጻፍ **ስልክ ቁጥርዎን** ያስገቡ፦",
        'share_ph': "📲 ስልክ ቁጥሬን ላክ",
        'err_ph': "❌ የተሳሳተ ስልክ ቁጥር! እባክዎ ትክክለኛ ቁጥር ያስገቡ፦",
        'ask_club': "🎯 **ደረጃ 4/4፦** መግባት የሚፈልጉትን **ክለብ** ይምረጡ፦",
        'ask_skill': "⚡ ያለዎትን **ልዩ ችሎታ (Skill)** ከታች ይምረጡ ወይም በእጅዎ ይጻፉ፦",
        'review': "📋 **መረጃዎን ያረጋግጡ**\n━━━━━━━━━━━━━━━━━━━━\n👤 **ስም፦** {name}\n🆔 **መታወቂያ፦** `{astu_id}`\n🎓 **ዓመት፦** {year}\n📱 **ስልክ፦** `{phone}`\n🎯 **ክለብ፦** {club}\n⚡ **ችሎታ፦** {skill}\n━━━━━━━━━━━━━━━━━━━━\nመረጃው ትክክል ነው? ወደ አድሚኑ ይላክ?",
        'sub_btn': "✅ አረጋግጥና ላክ",
        'edit_btn': "🔄 እንደገና ጀምር",
        'done': "✅ **ምዝገባዎ በተሳካ ሁኔታ ተልኳል!**\n\nአድሚኑ ({admin}) ሲያጸድቅልዎ **ባለ QR Code የአባልነት መታወቂያ ካርድ** እዚሁ ይላክልዎታል!"
    },
    'en': {
        'home': "🏛 **ASTU Club Portal**\n━━━━━━━━━━━━━━━━━━━━\nWelcome to Adama Science & Technology University's official club registration system.",
        'reg_btn': "📝 Apply for a Club",
        'chan_btn': "📢 Official Channel",
        'sup_btn': "💬 Support",
        'ask_name': "👤 **Step 1/4:** Enter your **Full Name**:",
        'ask_id': "🆔 **Step 2/4:** Enter your **ASTU ID** (e.g., `UGR/43400/19`):",
        'err_id': "❌ **Invalid Format!** Use `UGR/43400/19`:",
        'taken_id': "⚠️ **ID Already Taken!**\nThe ID `{id}` belongs to **{name}**. Please enter your own ASTU ID:",
        'ask_ph': "📱 **Step 3/4:** Detected Year: **{year}** ✅\n\nShare your **Phone Number** using the button below, or type it:",
        'share_ph': "📲 Share My Phone Number",
        'err_ph': "❌ Invalid phone number!",
        'ask_club': "🎯 **Step 4/4:** Select the **ASTU Club** you want to join:",
        'ask_skill': "⚡ Select your **Primary Skill** (or type it):",
        'review': "📋 **Review Your Application**\n━━━━━━━━━━━━━━━━━━━━\n👤 **Name:** {name}\n🆔 **ID:** `{astu_id}`\n🎓 **Year:** {year}\n📱 **Phone:** `{phone}`\n🎯 **Club:** {club}\n⚡ **Skill:** {skill}\n━━━━━━━━━━━━━━━━━━━━\nSubmit application?",
        'sub_btn': "✅ Submit Application",
        'edit_btn': "🔄 Start Over",
        'done': "✅ **Application Submitted!**\n\nAdmin {admin} will review it and send your **QR Membership Card** soon!"
    },
    'om': {
        'home': "🏛 **Galmee Kilaboota ASTU**\n━━━━━━━━━━━━━━━━━━━━\nBaga gara sirna galmee kilaboota ASTU nagaan dhuftan.",
        'reg_btn': "📝 Kilabiitti Galmaa'i",
        'chan_btn': "📢 Chaanaalii Keenya",
        'sup_btn': "💬 Gargaarsa",
        'ask_name': "👤 **Sadarkaa 1/4:** **Maqaa Guutuu** keessan barreessaa:",
        'ask_id': "🆔 **Sadarkaa 2/4:** **ID ASTU** galchaa (Fkn: `UGR/43400/19`):",
        'err_id': "❌ **ID Dogoggoraa!** Fkn: `UGR/43400/19`:",
        'taken_id': "⚠️ **ID kun qabameera!**\nID `{id}` maqaa **{name}** jedhuun galmaa'eera! ID keessan galchaa:",
        'ask_ph': "📱 **Sadarkaa 3/4:** Waggaa: **{year}** ✅\n\n**Lakkoofsa Bilbilaa** keessan ergaa:",
        'share_ph': "📲 Lakkoofsa Bilbilaa Ergi",
        'err_ph': "❌ Lakkoofsi bilbilaa sirrii miti!",
        'ask_club': "🎯 **Sadarkaa 4/4:** **Kilabii** barbaaddan filadhaa:",
        'ask_skill': "⚡ **Dandeettii (Skill)** keessan filadhaa ykn barreessaa:",
        'review': "📋 **Odeeffannoo Mirkaneessaa**\n━━━━━━━━━━━━━━━━━━━━\n👤 **Maqaa:** {name}\n🆔 **ID:** `{astu_id}`\n🎓 **Waggaa:** {year}\n📱 **Bilbila:** `{phone}`\n🎯 **Kilabii:** {club}\n⚡ **Dandeettii:** {skill}\n━━━━━━━━━━━━━━━━━━━━",
        'sub_btn': "✅ Ergi",
        'edit_btn': "🔄 Haqi",
        'done': "✅ **Galmeen Milkaa'eera!** Yemmuu Admin ({admin}) mirkaneessu Waraqaa Eenyummaa QR isiniif ergama!"
    },
    'ti': {
        'home': "🏛 **መመዝገቢ ክለባት ASTU**\n━━━━━━━━━━━━━━━━━━━━\nእንቋዕ ናብ መመዝገቢ ክለባት ASTU ብደሓን መጻእኩም።",
        'reg_btn': "📝 ንክለብ ተመዝገብ",
        'chan_btn': "📢 ቻናልና ተጸንበሩ",
        'sup_btn': "💬 ሓገዝ (Admin)",
        'ask_name': "👤 **ደረጃ 1/4፦** **ምሉእ ሽምኩም** ጸሓፉ፦",
        'ask_id': "🆔 **ደረጃ 2/4፦** **ናይ ASTU ID** የእትዉ (ምሳሌ፦ `UGR/43400/19`)፦",
        'err_id': "❌ **ጌጋ ID!** ብትኽክል ጸሓፉ (`UGR/43400/19`)፦",
        'taken_id': "⚠️ **እዚ ID ተታሒዙ እዩ!**\nእዚ ID (`{id}`) ኣቐዲሙ ብ **{name}** ተመዝጊቡ ኣሎ! ናይ ባዕልኹም ID የእትዉ፦",
        'ask_ph': "📱 **ደረጃ 3/4፦** ዓመት፦ **{year}** ✅\n\n**ቁጽሪ ስልክኹም** ስደዱ፦",
        'share_ph': "📲 ቁጽሪ ስልከይ ስደድ",
        'err_ph': "❌ ጌጋ ቁጽሪ ስልኪ!",
        'ask_club': "🎯 **ደረጃ 4/4፦** ክትኣትውዎ እትደልዩ **ክለብ** ምረጹ፦",
        'ask_skill': "⚡ ዘለኩም **ክእለት (Skill)** ምረጹ ወይ ጸሓፉ፦",
        'review': "📋 **ሓበሬታ ኣረጋግጹ**\n━━━━━━━━━━━━━━━━━━━━\n👤 **ሽም፦** {name}\n🆔 **ID፦** `{astu_id}`\n🎓 **ዓመት፦** {year}\n📱 **ስልኪ፦** `{phone}`\n🎯 **ክለብ፦** {club}\n⚡ **ክእለት፦** {skill}\n━━━━━━━━━━━━━━━━━━━━",
        'sub_btn': "✅ ኣረጋግጽን ስደድን",
        'edit_btn': "🔄 ካብ መጀመርታ",
        'done': "✅ **ምዝገባኹም ተዛዚሙ!** ኣድሚን ({admin}) ምስ ኣጽደቖ QR ID ክለኣኸልኩም እዩ!"
    }
}

CLUBS = [
    "💻 CSEC ASTU (ፕሮግራሚንግና ሶፍትዌር)",
    "🤖 AI & Robotics (ሮቦቲክስና አርቲፊሻል ኢንተליጀንስ)",
    "🛡️ Cyber Security (ሳይበር ሴኩሪቲ)",
    "🚀 Space Science (ስፔስ ሳይንስና አስትሮኖሚ)",
    "💡 Innovation & Startup (ፈጠራና ኢንተርፕረነርሺፕ)",
    "🎨 Media & Digital Arts (ሚዲያና ዲጂታል አርት)"
]

SKILLS = [
    ["🐍 Python / AI", "🌐 Web Development"],
    ["📱 Mobile Apps", "🎨 ግራፊክስ ዲዛይን"],
    ["🛡️ Cyber Security", "🎬 ቪዲዮ ኤዲቲንግ"],
    ["🚀 ጀማሪ ነኝ (ለመማር ዝግጁ!)"]
]

# ================= የተማሪዎች መመዝገቢያ ሂደት =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(user.id)

    if existing:
        kb = [
            [InlineKeyboardButton("🪪 የQR መታወቂያ ካርዴን አውርድ", callback_data="get_my_qr")],
            [InlineKeyboardButton("📢 ቻናላችንን ተቀላቀል", url=CHANNEL_URL),
             InlineKeyboardButton("💬 አድሚኑን አነጋግር", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
        ]
        if user.id == ADMIN_ID:
            kb.insert(0, [InlineKeyboardButton("👑 የአድሚን መቆጣጠሪያ ክፈት", callback_data="open_admin")])

        msg = (
            f"👋 **ሰላም {existing['full_name']}! ቀድሞውኑ ተመዝግበዋል!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **መታወቂያ፦** `{existing['astu_id']}`\n"
            f"🎓 **ዓመት፦** {existing['year']}\n"
            f"🎯 **ክለብ፦** {existing['club']}\n"
            f"📊 **ሁኔታ፦** **{existing['status']}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ *ድጋሚ መመዝገብ አይቻልም። ከታች ያለውን በተን በመጫን የQR መታወቂያዎን ማውረድ ይችላሉ።*"
        )
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return ConversationHandler.END

    kb = [
        [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data='lang_am'),
         InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
        [InlineKeyboardButton("🌳 Afaan Oromoo", callback_data='lang_om'),
         InlineKeyboardButton("🌾 ትግርኛ", callback_data='lang_ti')]
    ]
    if user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("👑 የአድሚን መቆጣጠሪያ ክፈት (Admin)", callback_data="open_admin")])

    await update.message.reply_text(
        "🏛 **እንኳን ወደ ASTU ክለቦች መመዝገቢያ በደህና መጡ!**\nእባክዎ የሚፈልጉትን ቋንቋ ይምረጡ / Select Language፦",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )
    return LANG

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    t = TEXTS[lang]

    kb = [
        [InlineKeyboardButton(t['reg_btn'], callback_data='init_reg')],
        [InlineKeyboardButton(t['chan_btn'], url=CHANNEL_URL),
         InlineKeyboardButton(t['sup_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    if update.effective_user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("👑 የአድሚን መቆጣጠሪያ (Admin)", callback_data="open_admin")])

    await query.edit_message_text(t['home'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return LANG

async def init_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if get_user(update.effective_user.id):
        await query.edit_message_text("✅ ቀድሞውኑ ተመዝግበዋል! /start የሚለውን ይጫኑ።")
        return ConversationHandler.END

    lang = context.user_data.get('lang', 'am')
    await query.edit_message_text(TEXTS[lang]['ask_name'], parse_mode="Markdown")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip().title()
    lang = context.user_data.get('lang', 'am')
    await update.message.reply_text(TEXTS[lang]['ask_id'], parse_mode="Markdown")
    return ASTU_ID

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    astu_id = update.message.text.strip().upper()
    lang = context.user_data.get('lang', 'am')

    if not re.match(r"^(UGR|PGR|BSC|MSC)/\d{3,6}/\d{2}$", astu_id):
        await update.message.reply_text(TEXTS[lang]['err_id'], parse_mode="Markdown")
        return ASTU_ID

    owner = check_id_owner(astu_id)
    if owner:
        await update.message.reply_text(
            TEXTS[lang]['taken_id'].format(id=astu_id, name=owner['full_name']),
            parse_mode="Markdown"
        )
        return ASTU_ID

    detected_year = detect_batch_from_id(astu_id)
    context.user_data['astu_id'] = astu_id
    context.user_data['year'] = detected_year

    kb = [[KeyboardButton(TEXTS[lang]['share_ph'], request_contact=True)]]
    await update.message.reply_text(
        TEXTS[lang]['ask_ph'].format(year=detected_year),
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'am')
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip().replace(" ", "")
        if not re.match(r"^(\+?251|0)(9|7)\d{8}$", phone):
            await update.message.reply_text(TEXTS[lang]['err_ph'])
            return PHONE

    context.user_data['phone'] = phone
    temp = await update.message.reply_text("🔄...", reply_markup=ReplyKeyboardRemove())
    await temp.delete()

    kb = [[InlineKeyboardButton(c, callback_data=f"cl_{i}")] for i, c in enumerate(CLUBS)]
    await update.message.reply_text(TEXTS[lang]['ask_club'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return CLUB

async def get_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['club'] = CLUBS[int(query.data.replace("cl_", ""))]
    lang = context.user_data.get('lang', 'am')

    kb = [[InlineKeyboardButton(s, callback_data=f"sk_{s}") for s in row] for row in SKILLS]
    await query.edit_message_text(TEXTS[lang]['ask_skill'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return SKILL

async def get_skill_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['skill'] = query.data.replace("sk_", "")
    return await show_preview(query.edit_message_text, context)

async def get_skill_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['skill'] = update.message.text.strip()
    return await show_preview(update.message.reply_text, context)

async def show_preview(send_func, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'am')
    d = context.user_data
    kb = [
        [InlineKeyboardButton(TEXTS[lang]['sub_btn'], callback_data="conf_yes")],
        [InlineKeyboardButton(TEXTS[lang]['edit_btn'], callback_data="conf_no")]
    ]
    await send_func(TEXTS[lang]['review'].format(**d), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return CONFIRM

async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'am')

    if query.data == "conf_no":
        await query.edit_message_text("🔄 ምዝገባው ተሰርዟል። እንደገና ለመጀመር /start ይበሉ።")
        return ConversationHandler.END

    user = update.effective_user
    d = context.user_data
    d['user_id'] = user.id
    d['username'] = f"@{user.username}" if user.username else "የለውም"

    if check_id_owner(d['astu_id']):
        await query.edit_message_text("⚠️ ይህ ID አሁን በሌላ ሰው ተይዟል! /start ብለው እንደገና ይሞክሩ።")
        return ConversationHandler.END

    save_member(d)

    kb = [
        [InlineKeyboardButton("🪪 የQR መታወቂያ ካርዴን አውርድ", callback_data="get_my_qr")],
        [InlineKeyboardButton(TEXTS[lang]['chan_btn'], url=CHANNEL_URL),
         InlineKeyboardButton(TEXTS[lang]['sup_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    await query.edit_message_text(TEXTS[lang]['done'].format(admin=ADMIN_USERNAME), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    # ለአድሚን (ሰልማን) የሚላክ መልዕክት በአማርኛ
    admin_alert = (
        f"🔔 **አዲስ የተማሪ ምዝገባ ጥያቄ!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **ሙሉ ስም፦** {d['name']}\n"
        f"🆔 **መታወቂያ፦** `{d['astu_id']}`\n"
        f"🎓 **ዓመት፦** {d['year']}\n"
        f"📱 **ስልክ፦** `{d['phone']}`\n"
        f"🎯 **ክለብ፦** {d['club']}\n"
        f"⚡ **ችሎታ፦** {d['skill']}\n"
        f"🔗 **ቴሌግራም፦** {d['username']} (`{user.id}`)"
    )
    adm_kb = [[
        InlineKeyboardButton("✅ አጽድቅና QR ላክ (Approve)", callback_data=f"adm_app_{user.id}"),
        InlineKeyboardButton("🗑️ ውድቅ አድርግና ሰርዝ (Reject)", callback_data=f"adm_rej_{user.id}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_alert, reply_markup=InlineKeyboardMarkup(adm_kb), parse_mode="Markdown")
    return ConversationHandler.END

# ================= የQR ካርድ እና የፍለጋ ሲስተም =================
async def send_qr_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🪪 የQR መታወቂያ ካርድዎ እየተዘጋጀ ነው...")
    u = get_user(update.effective_user.id)
    if not u:
        await query.message.reply_text("❌ መዝገብ ላይ አልተገኙም! /start ብለው ይመዝገቡ።")
        return

    qr_url = generate_id_card_url(u['full_name'], u['astu_id'], u['club'], u['year'])
    caption = (
        f"🪪 **የASTU ክለቦች ዲጂታል መታወቂያ**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **ስም፦** {u['full_name']}\n"
        f"🆔 **መታወቂያ፦** `{u['astu_id']}`\n"
        f"🎓 **ዓመት፦** {u['year']}\n"
        f"🎯 **ክለብ፦** {u['club']}\n"
        f"📊 **ሁኔታ፦** **{u['status']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*አባልነቱን ለማረጋገጥ QR ኮዱን ስካን ያድርጉ።*"
    )
    await context.bot.send_photo(chat_id=u['user_id'], photo=qr_url, caption=caption, parse_mode="Markdown")

async def inline_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if update.effective_user.id != ADMIN_ID or not query:
        return

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM members WHERE full_name LIKE ? OR astu_id LIKE ? LIMIT 10",
            (f"%{query}%", f"%{query}%")
        ).fetchall()

    results = []
    for r in rows:
        results.append(InlineQueryResultArticle(
            id=str(r['user_id']),
            title=f"{r['full_name']} ({r['astu_id']})",
            description=f"{r['club']} | {r['status']}",
            input_message_content=InputTextMessageContent(
                f"👤 **ተማሪ፦** {r['full_name']}\n🆔 **ID፦** `{r['astu_id']}`\n📱 **ስልክ፦** `{r['phone']}`\n🎯 **ክለብ፦** {r['club']}\n📊 **ሁኔታ፦** {r['status']}",
                parse_mode="Markdown"
            )
        ))
    await update.inline_query.answer(results, cache_time=1)

# ================= የአድሚን መቆጣጠሪያ (ADMIN DASHBOARD በአማርኛ) =================
async def show_admin_panel(send_func):
    with sqlite3.connect(DB_NAME) as conn:
        total = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        app_cnt = conn.execute("SELECT COUNT(*) FROM members WHERE status LIKE '%Approved%'").fetchone()[0]
        pend_cnt = conn.execute("SELECT COUNT(*) FROM members WHERE status LIKE '%Pending%'").fetchone()[0]
        clubs = conn.execute("SELECT club, COUNT(*) FROM members GROUP BY club").fetchall()

    c_stats = "\n".join([f"▫️ {c[0]}: `{c[1]}`" for c in clubs]) or "▫️ እስካሁን የተመዘገበ የለም"
    txt = (
        f"👑 **የአድሚን ሰልማን መቆጣጠሪያ ({ADMIN_USERNAME})**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **ጠቅላላ ተመዝጋቢ፦** `{total}`\n"
        f"✅ **የጸደቀላቸው፦** `{app_cnt}`\n"
        f"⏳ **በመጠባበቅ ላይ፦** `{pend_cnt}`\n\n"
        f"📈 **በየክለቡ ያሉ ተማሪዎች ብዛት፦**\n{c_stats}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *(ውድቅ የተደረጉ ተማሪዎች ከመዝገብ ላይ በራስ-ሰር ተሰርዘዋል)*"
    )
    kb = [
        [InlineKeyboardButton("📥 በExcel (CSV) አውርድ", callback_data="adm_export"),
         InlineKeyboardButton("📋 የመጨረሻዎቹን 10 እይ", callback_data="adm_list")],
        [InlineKeyboardButton("📢 ለሁሉም ተማሪ መልዕክት ላክ", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔄 አድስ (Refresh)", callback_data="open_admin")]
    ]
    await send_func(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await show_admin_panel(update.message.reply_text)
    return ConversationHandler.END

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("⛔ ይህ ለአድሚኑ ብቻ የተፈቀደ ነው!", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data == "open_admin":
        await show_admin_panel(query.edit_message_text)

    elif data == "adm_export":
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT * FROM members").fetchall()
        csv_file = "ASTU_Club_Members.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(["User_ID", "Username", "ሙሉ ስም", "ASTU_ID", "ስልክ", "ዓመት", "ክለብ", "ችሎታ", "ሁኔታ", "ቀን"])
            w.writerows(rows)
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(csv_file, 'rb'), caption="📊 **የተመዘገቡት ተማሪዎች ዝርዝር (Excel/CSV)**", parse_mode="Markdown")

    elif data == "adm_list":
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT full_name, astu_id, club, status FROM members ORDER BY rowid DESC LIMIT 10").fetchall()
        txt = "📋 **በቅርብ የተመዘገቡ 10 ተማሪዎች፦**\n━━━━━━━━━━━━━━━━━━━━\n" + ("\n".join([f"👤 **{r[0]}** (`{r[1]}`)\n   🎯 {r[2]} — {r[3]}" for r in rows]) if rows else "መዝገቡ ባዶ ነው።")
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ኋላ ተመለስ", callback_data="open_admin")]]), parse_mode="Markdown")

    elif data.startswith("adm_app_"):
        uid = int(data.split("_")[2])
        u = get_user(uid)
        if not u:
            await query.edit_message_text("⚠️ ይህ ተማሪ በዳታቤዝ ውስጥ የለም።")
            return

        update_db_status(uid, "approve")
        qr_url = generate_id_card_url(u['full_name'], u['astu_id'], u['club'], u['year'])
        caption = (
            f"🎉 **እንኳን ደስ አለዎት {u['full_name']}!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"ለ **{u['club']}** ያቀረቡት የአባልነት ጥያቄ በአድሚን {ADMIN_USERNAME} **ጸድቋል (Approved)!**\n\n"
            f"🆔 **መታወቂያ፦** `{u['astu_id']}`\n"
            f"🎓 **ዓመት፦** {u['year']}\n"
            f"📊 **ሁኔታ፦** `ህጋዊ አባል ✅`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"ይህ የእርስዎ ዲጂታል የQR መታወቂያ ካርድ ነው!"
        )
        try:
            await context.bot.send_photo(
                chat_id=uid, photo=qr_url, caption=caption,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 ቻናላችንን ይቀላቀሉ", url=CHANNEL_URL)]]),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(query.message.text + "\n\n✅ **ጸድቋል! (የQR መታወቂያ ተልኮለታል)**", parse_mode="Markdown")

    elif data.startswith("adm_rej_"):
        uid = int(data.split("_")[2])
        update_db_status(uid, "reject")
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"❌ **የምዝገባ መልዕክት**\nለASTU ክለብ ያደረጉት ምዝገባ ውድቅ ተደርጓል (ከመዝገብም ተሰርዟል)። የተሳሳተ መረጃ አስገብተው ከነበረ /start ብለው እንደገና በትክክል መመዝገብ ይችላሉ፣ ወይም {ADMIN_USERNAME} ያነጋግሩ።"
            )
        except Exception:
            pass
        await query.edit_message_text(query.message.text + "\n\n🗑️ **ውድቅ ተደርጓል (ከዳታቤዝ ተሰርዟል)**", parse_mode="Markdown")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    await query.edit_message_text("📢 **ለተመዘገቡት ተማሪዎች ሁሉ የሚላከውን ማስታወቂያ ይጻፉ** (ለማቋረጥ /cancel ይበሉ)፦")
    return BROADCAST_MSG

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB_NAME) as conn:
        users = conn.execute("SELECT user_id FROM members").fetchall()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u[0], text=f"📢 **የASTU ክለቦች ማስታወቂያ**\n━━━━━━━━━━━━━━━━━━━━\n{update.message.text}\n━━━━━━━━━━━━━━━━━━━━\n*ከአድሚን {ADMIN_USERNAME}*", parse_mode="Markdown")
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ ማስታወቂያው ለ `{sent}` ተማሪዎች በተሳካ ሁኔታ ተልኳል!", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ምዝገባው ተቋርጧል። እንደገና ለመጀመር /start ይበሉ።", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('admin', admin_cmd))
    app.add_handler(CallbackQueryHandler(send_qr_card, pattern='^get_my_qr$'))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern='^(open_admin|adm_export|adm_list|adm_app_|adm_rej_)'))
    app.add_handler(InlineQueryHandler(inline_search))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern='^adm_broadcast$')],
        states={BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)]},
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG: [
                CallbackQueryHandler(select_language, pattern='^lang_'),
                CallbackQueryHandler(init_registration, pattern='^init_reg$')
            ],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASTU_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            PHONE: [MessageHandler((filters.CONTACT | filters.TEXT) & ~filters.COMMAND, get_phone)],
            CLUB: [CallbackQueryHandler(get_club, pattern='^cl_')],
            SKILL: [
                CallbackQueryHandler(get_skill_btn, pattern='^sk_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_skill_text)
            ],
            CONFIRM: [CallbackQueryHandler(confirm_registration, pattern='^conf_')]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start), CommandHandler('admin', admin_cmd)]
    ))

    print("🚀 ASTU Smart Portal Running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    keep_alive()
    main()
