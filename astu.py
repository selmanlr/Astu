import sqlite3
import csv
import os
import re
from datetime import datetime
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

# ================= CONFIGURATION =================
TOKEN = "8687801959:AAHf9hw-gpgkIqxseUE3aA2o4jGeaTYOTGo"
ADMIN_ID = 8891900780
CHANNEL_URL = "https://t.me/astutechteam"
ADMIN_USERNAME = "@Selman_Ali"
DB_NAME = "astu_quantum_2059.db"

# States
LANG, NAME, ASTU_ID, PHONE, YEAR, CLUB, SKILL, CONFIRM, BROADCAST_MSG = range(9)

# ================= 2059 CYBERPUNK WEB DASHBOARD =================
app_web = Flask(__name__)

@app_web.route('/')
def home():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM members WHERE status='Approved'")
    approved = c.fetchone()[0]
    conn.close()
    return f"""
    <html>
    <head><title>ASTU Nexus 2059</title></head>
    <body style="background:#0a0b10; color:#00ffcc; font-family:monospace; text-align:center; padding-top:100px;">
        <h1>🛸 ASTU QUANTUM NEXUS [2059 OS]</h1>
        <p style="color:#8892b0;">System Status: <span style="color:#00ff00;">ONLINE & ENCRYPTED</span></p>
        <div style="border:1px solid #00ffcc; display:inline-block; padding:20px; border-radius:10px; background:#11131f;">
            <h2>📊 Total Nodes (Students): {total}</h2>
            <h3>✅ Verified (Approved): {approved}</h3>
        </div>
        <p style="margin-top:40px; color:#555;">Engineered by Selman Ali @ ASTU</p>
    </body>
    </html>
    """

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ================= SQLITE3 QUANTUM DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members (
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
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def check_id_owner(astu_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE UPPER(astu_id)=UPPER(?)", (astu_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def save_member(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('''INSERT OR REPLACE INTO members 
        (user_id, username, full_name, astu_id, phone, year, club, skill, status, reg_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data['user_id'], data['username'], data['name'], data['astu_id'],
         data['phone'], data['year'], data['club'], data['skill'], "Pending ⏳", now))
    conn.commit()
    conn.close()

def set_status_or_delete(user_id, action):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if action == "approve":
        c.execute("UPDATE members SET status='Approved ✅' WHERE user_id=?", (user_id,))
    elif action == "reject":
        c.execute("DELETE FROM members WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

init_db()

# ================= MULTI-LANGUAGE MATRIX =================
TEXTS = {
    'en': {
        'dash': "🛸 **ASTU NEXUS PORTAL [v2059]** ⚡\n━━━━━━━━━━━━━━━━━━━━\nWelcome to Adama Science & Technology University's Smart Club Ecosystem.\n\nSelect an action below:",
        'reg_btn': "🚀 Initialize Registration",
        'chan_btn': "🌐 ASTU Tech Hub",
        'sup_btn': "👨‍💻 Contact Architect",
        'step1': "🛸 **[██░░░░░░░░] 20%**\n\n👤 Enter your **Full Name**:",
        'step2': "🛸 **[████░░░░░░] 40%**\n\n🆔 Enter your **ASTU ID** (e.g., `UGR/43400/19`):",
        'err_id': "⚠️ **Syntax Error!** Invalid ASTU ID format.\nUse: `UGR/43400/19` or `PGR/1234/19`:",
        'taken_id': "🚨 **IDENTITY CONFLICT DETECTED!**\n\nID `{id}` is already registered to **{name}**!\nPlease enter your own valid ASTU ID:",
        'step3': "🛸 **[██████░░░░] 60%**\n\n📱 Tap the button below to sync your **Phone Number**, or type it (`09...`):",
        'share_ph': "📲 Sync Phone Number (1-Tap)",
        'err_ph': "❌ Invalid frequency! Enter a valid Ethiopian phone number:",
        'step4': "🛸 **[████████░░] 80%**\n\n🎓 Select your **Academic Batch**:",
        'step5': "🛸 **[█████████░] 90%**\n\n🎯 Select your target **ASTU Tech Division (Club)**:",
        'step6': "🛸 **[██████████] 99%**\n\n⚡ Select or type your **Primary Specialty / Skill**:",
        'review': "🧬 **QUANTUM DIGITAL PASS PREVIEW** 🧬\n━━━━━━━━━━━━━━━━━━━━\n👤 **Name:** {name}\n🆔 **ID:** `{astu_id}`\n📱 **Phone:** `{phone}`\n🎓 **Batch:** {year}\n🎯 **Division:** {club}\n⚡ **Specialty:** {skill}\n━━━━━━━━━━━━━━━━━━━━\nConfirm transmission to Admin?",
        'confirm_btn': "✅ Transmit Application",
        'cancel_btn': "🔄 Reset Data",
        'done': "🎉 **TRANSMISSION COMPLETE!** 🚀\n━━━━━━━━━━━━━━━━━━━━\nYour Digital Pass has been sent to Admin **{admin}** for neural verification.\nYou will receive a live alert once approved!",
    },
    'am': {
        'dash': "🛸 **የASTU ዲጂታል ክለቦች ማዕከል [2059]** ⚡\n━━━━━━━━━━━━━━━━━━━━\nእንኳን ወደ አዳማ ሳይንስና ቴክኖሎጂ ዩኒቨርሲቲ ዘመናዊ የክለቦች ሲስተም በደህና መጡ!\n\nከታች ያለውን በተን ይምረጡ፦",
        'reg_btn': "🚀 ምዝገባ ጀምር (Register)",
        'chan_btn': "🌐 የASTU Tech ቻናል",
        'sup_btn': "👨‍💻 አድሚኑን አነጋግር",
        'step1': "🛸 **[██░░░░░░░░] 20%**\n\n👤 እባክዎ **ሙሉ ስምዎን** ይጻፉ፦",
        'step2': "🛸 **[████░░░░░░] 40%**\n\n🆔 የ**ASTU መታወቂያ ቁጥርዎን** ያስገቡ (ምሳሌ፦ `UGR/43400/19`)፦",
        'err_id': "⚠️ **የተሳሳተ የID አጻጻፍ!**\nእባክዎ በትክክል ይጻፉ (ምሳሌ፦ `UGR/43400/19`)፦",
        'taken_id': "🚨 **ይህ መታወቂያ ቁጥር ተይዟል!**\n\nይህ ID (`{id}`) ቀድሞ በ **{name}** ስም ተመዝግቧል! የሌላ ሰው ID መጠቀም አይቻልም። እባክዎ የራስዎን ID ያስገቡ፦",
        'step3': "🛸 **[██████░░░░] 60%**\n\n📱 ከታች ያለውን በተን በመጫን ወይም በመጻፍ **ስልክ ቁጥርዎን** ያስገቡ፦",
        'share_ph': "📲 ስልክ ቁጥሬን በራስ-ሰር ላክ",
        'err_ph': "❌ የተሳሳተ ስልክ ቁጥር! እባክዎ ትክክለኛ ቁጥር ያስገቡ፦",
        'step4': "🛸 **[████████░░] 80%**\n\n🎓 **ስንተኛ ዓመት (Batch)** ተማሪ ነዎት?",
        'step5': "🛸 **[█████████░] 90%**\n\n🎯 መግባት የሚፈልጉትን **የASTU ክለብ** ይምረጡ፦",
        'step6': "🛸 **[██████████] 99%**\n\n⚡ ያለዎትን **ልዩ ችሎታ (Skill)** ከታች ይምረጡ ወይም በእጅዎ ይጻፉ፦",
        'review': "🧬 **የዲጂታል መታወቂያ ቅድመ-እይታ** 🧬\n━━━━━━━━━━━━━━━━━━━━\n👤 **ስም፦** {name}\n🆔 **ID፦** `{astu_id}`\n📱 **ስልክ፦** `{phone}`\n🎓 **ዓመት፦** {year}\n🎯 **ክለብ፦** {club}\n⚡ **ችሎታ፦** {skill}\n━━━━━━━━━━━━━━━━━━━━\nመረጃው ትክክል ነው? ወደ አድሚኑ ይላክ?",
        'confirm_btn': "✅ አረጋግጥና ላክ (Submit)",
        'cancel_btn': "🔄 እንደገና ጀምር",
        'done': "🎉 **ምዝገባዎ በተሳካ ሁኔታ ተልኳል!** 🚀\n━━━━━━━━━━━━━━━━━━━━\nዲጂታል መረጃዎ ለአድሚን **{admin}** ደርሷል። ልክ Approve ሲደረግልዎ እዚሁ ቦት ላይ መልዕክት ይደርስዎታል!",
    },
    'om': {
        'dash': "🛸 **Wiirtuu Kilaboota Dijitaalaa ASTU [2059]** ⚡\n━━━━━━━━━━━━━━━━━━━━\nBaga gara sirna ammayyaa kilaboota ASTU nagaan dhuftan!",
        'reg_btn': "🚀 Galmee Jalqabi",
        'chan_btn': "🌐 Chaanaalii ASTU Tech",
        'sup_btn': "👨‍💻 Admin Quunnami",
        'step1': "🛸 **[██░░░░░░░░] 20%**\n\n👤 **Maqaa Guutuu** keessan barreessaa:",
        'step2': "🛸 **[████░░░░░░] 40%**\n\n🆔 **ID ASTU** keessan galchaa (Fkn: `UGR/43400/19`):",
        'err_id': "⚠️ **ID Dogoggoraa!** Fkn: `UGR/43400/19`:",
        'taken_id': "🚨 **ID KUN QABAMEERA!**\n\nID `{id}` duraan maqaa **{name}** jedhuun galmaa'eera! Maaloo ID keessan qofa galchaa:",
        'step3': "🛸 **[██████░░░░] 60%**\n\n📱 **Lakkoofsa Bilbilaa** keessan ergaa:",
        'share_ph': "📲 Lakkoofsa Koo Ergi",
        'err_ph': "❌ Lakkoofsi bilbilaa sirrii miti!",
        'step4': "🛸 **[████████░░] 80%**\n\n🎓 Barataa **Waggaa Meegaffaa** ti?",
        'step5': "🛸 **[█████████░] 90%**\n\n🎯 **Kilabii** barbaaddan filadhaa:",
        'step6': "🛸 **[██████████] 99%**\n\n⚡ **Dandeettii (Skill)** keessan filadhaa ykn barreessaa:",
        'review': "🧬 **MIRKANEESSA ODEEFFANNOO** 🧬\n━━━━━━━━━━━━━━━━━━━━\n👤 **Maqaa:** {name}\n🆔 **ID:** `{astu_id}`\n📱 **Bilbila:** `{phone}`\n🎓 **Waggaa:** {year}\n🎯 **Kilabii:** {club}\n⚡ **Dandeettii:** {skill}\n━━━━━━━━━━━━━━━━━━━━\nOdeeffannoon sirriidhaa?",
        'confirm_btn': "✅ Eeyyee, Ergi",
        'cancel_btn': "🔄 Haqi",
        'done': "🎉 **GALMEEN MILKAA'EERA!** 🚀\nOdeeffannoon keessan Admin **{admin}** bira gaheera!",
    },
    'ti': {
        'dash': "🛸 **ዲጂታል ማእከል ክለባት ASTU [2059]** ⚡\n━━━━━━━━━━━━━━━━━━━━\nእንቋዕ ናብ ዘመናዊ ሲስተም ክለባት ASTU ብደሓን መጻእኩም!",
        'reg_btn': "🚀 ምዝገባ ጀምር",
        'chan_btn': "🌐 ቻናል ASTU Tech",
        'sup_btn': "👨‍💻 ንኣድሚን ኣዘራርብ",
        'step1': "🛸 **[██░░░░░░░░] 20%**\n\n👤 **ምሉእ ሽምኩም** ጸሓፉ፦",
        'step2': "🛸 **[████░░░░░░] 40%**\n\n🆔 **ናይ ASTU ID** የእትዉ (ምሳሌ፦ `UGR/43400/19`)፦",
        'err_id': "⚠️ **ጌጋ ID!** ብትኽክል ጸሓፉ (`UGR/43400/19`)፦",
        'taken_id': "🚨 **እዚ ID ተታሒዙ እዩ!**\n\nእዚ ID (`{id}`) ኣቐዲሙ ብ **{name}** ተመዝጊቡ ኣሎ! ናይ ባዕልኹም ID የእትዉ፦",
        'step3': "🛸 **[██████░░░░] 60%**\n\n📱 **ቁጽሪ ስልክኹም** ስደዱ፦",
        'share_ph': "📲 ቁጽሪ ስልከይ ስደድ",
        'err_ph': "❌ ጌጋ ቁጽሪ ስልኪ!",
        'step4': "🛸 **[████████░░] 80%**\n\n🎓 **ክንደይ ዓመት** ተምሃራይ ኢኹም?",
        'step5': "🛸 **[█████████░] 90%**\n\n🎯 ክትኣትውዎ እትደልዩ **ክለብ** ምረጹ፦",
        'step6': "🛸 **[██████████] 99%**\n\n⚡ ዘለኩም **ክእለት (Skill)** ምረጹ ወይ ጸሓፉ፦",
        'review': "🧬 **ምርግጋጽ ሓበሬታ** 🧬\n━━━━━━━━━━━━━━━━━━━━\n👤 **ሽም፦** {name}\n🆔 **ID፦** `{astu_id}`\n📱 **ስልኪ፦** `{phone}`\n🎓 **ዓመት፦** {year}\n🎯 **ክለብ፦** {club}\n⚡ **ክእለት፦** {skill}\n━━━━━━━━━━━━━━━━━━━━\nናብ ኣድሚን ክለኣኽ ድዩ?",
        'confirm_btn': "✅ እወ ስደድ",
        'cancel_btn': "🔄 ካብ መጀመርታ",
        'done': "🎉 **ምዝገባኹም ተዛዚሙ!** 🚀\nናብ ኣድሚን **{admin}** ተላኢኹ ኣሎ!",
    }
}

CLUBS = [
    "💻 CSEC ASTU (Algorithms & Dev)",
    "🤖 AI, Robotics & Autonomous Sys",
    "🛡️ Cyber Security & Ethical Hacking",
    "🚀 Space Science & Aerospace (ESSS)",
    "💡 Quantum Innovation & Startups",
    "🎨 CGI, UI/UX & Digital Media"
]

SKILLS = [
    ["🐍 Python / AI", "🌐 Web / Full-Stack"],
    ["📱 Mobile App Dev", "🎨 Graphic / UI Design"],
    ["🛡️ Cyber / Networking", "🎬 Video Editing / 3D"],
    ["🚀 Beginner (Ready to Learn!)"]
]

# ================= STUDENT FLOW HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(user.id)

    # 1. ተማሪው ቀድሞ ከተመዘገበ Digital ID Card ያሳየዋል!
    if existing:
        kb = [
            [InlineKeyboardButton("🌐 ASTU Tech Channel", url=CHANNEL_URL)],
            [InlineKeyboardButton("👨‍💻 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
        ]
        if user.id == ADMIN_ID:
            kb.insert(0, [InlineKeyboardButton("👑 Open Quantum Admin Panel", callback_data="open_admin")])

        card = (
            f"🪪 **ASTU QUANTUM ID CARD [2059]**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👋 **ሰላም {existing['full_name']}! ቀድሞውኑ ተመዝግበዋል!**\n\n"
            f"🆔 **ID:** `{existing['astu_id']}`\n"
            f"🎯 **Division:** {existing['club']}\n"
            f"🎓 **Batch:** {existing['year']}\n"
            f"⚡ **Specialty:** {existing['skill']}\n"
            f"📡 **Status:** **{existing['status']}**\n"
            f"🕒 **Synced:** `{existing['reg_date']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ *ድጋሚ መመዝገብ አይቻልም። ማስተካከያ ካለዎት አድሚኑን ያነጋግሩ።*"
        )
        await update.message.reply_text(card, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'),
         InlineKeyboardButton("🇪🇹 አማርኛ", callback_data='lang_am')],
        [InlineKeyboardButton("🌳 Afaan Oromoo", callback_data='lang_om'),
         InlineKeyboardButton("🌾 ትግርኛ", callback_data='lang_ti')]
    ]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 Open Quantum Admin Panel", callback_data="open_admin")])

    await update.message.reply_text(
        "🛸 **ASTU QUANTUM NEXUS [2059 OS]** ⚡\n━━━━━━━━━━━━━━━━━━━━\nSelect Neural Interface Language / ቋንቋ ይምረጡ፦",
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

    kb = [
        [InlineKeyboardButton(t['reg_btn'], callback_data='init_reg')],
        [InlineKeyboardButton(t['chan_btn'], url=CHANNEL_URL),
         InlineKeyboardButton(t['sup_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    if update.effective_user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("👑 Quantum Admin Panel", callback_data="open_admin")])

    await query.edit_message_text(t['dash'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return LANG

async def init_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if get_user(update.effective_user.id):
        await query.edit_message_text("✅ ቀድሞውኑ ተመዝግበዋል! /start የሚለውን ይጫኑ።")
        return ConversationHandler.END

    lang = context.user_data.get('lang', 'am')
    await query.edit_message_text(TEXTS[lang]['step1'], parse_mode="Markdown")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip().title()
    lang = context.user_data.get('lang', 'am')
    await update.message.reply_text(TEXTS[lang]['step2'], parse_mode="Markdown")
    return ASTU_ID

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    astu_id = update.message.text.strip().upper()
    lang = context.user_data.get('lang', 'am')

    # Smart Regex: accepts UGR/43400/19, PGR/1234/18, etc.
    if not re.match(r"^(UGR|PGR|BSC|MSC)/\d{3,6}/\d{2}$", astu_id):
        await update.message.reply_text(TEXTS[lang]['err_id'], parse_mode="Markdown")
        return ASTU_ID

    # 2. Check if ID is already taken and mention the student's name!
    owner = check_id_owner(astu_id)
    if owner:
        msg = TEXTS[lang]['taken_id'].format(id=astu_id, name=owner['full_name'])
        await update.message.reply_text(msg, parse_mode="Markdown")
        return ASTU_ID

    context.user_data['astu_id'] = astu_id
    kb = [[KeyboardButton(TEXTS[lang]['share_ph'], request_contact=True)]]
    await update.message.reply_text(
        TEXTS[lang]['step3'],
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
    temp = await update.message.reply_text("⚡ Syncing...", reply_markup=ReplyKeyboardRemove())
    await temp.delete()

    years = [
        [InlineKeyboardButton("1️⃣ 1st Year (Freshman)", callback_data="yr_1st Year"),
         InlineKeyboardButton("2️⃣ 2nd Year (Sophomore)", callback_data="yr_2nd Year")],
        [InlineKeyboardButton("3️⃣ 3rd Year", callback_data="yr_3rd Year"),
         InlineKeyboardButton("4️⃣ 4th Year", callback_data="yr_4th Year")],
        [InlineKeyboardButton("5️⃣ 5th Year (GC 🎓)", callback_data="yr_5th Year")]
    ]
    await update.message.reply_text(TEXTS[lang]['step4'], reply_markup=InlineKeyboardMarkup(years), parse_mode="Markdown")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['year'] = query.data.replace("yr_", "")
    lang = context.user_data.get('lang', 'am')

    kb = [[InlineKeyboardButton(c, callback_data=f"cl_{i}")] for i, c in enumerate(CLUBS)]
    await query.edit_message_text(TEXTS[lang]['step5'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return CLUB

async def get_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("cl_", ""))
    context.user_data['club'] = CLUBS[idx]
    lang = context.user_data.get('lang', 'am')

    kb = [[InlineKeyboardButton(s, callback_data=f"sk_{s}") for s in row] for row in SKILLS]
    await query.edit_message_text(TEXTS[lang]['step6'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
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
    preview_txt = TEXTS[lang]['review'].format(
        name=d['name'], astu_id=d['astu_id'], phone=d['phone'],
        year=d['year'], club=d['club'], skill=d['skill']
    )
    kb = [
        [InlineKeyboardButton(TEXTS[lang]['confirm_btn'], callback_data="conf_yes")],
        [InlineKeyboardButton(TEXTS[lang]['cancel_btn'], callback_data="conf_no")]
    ]
    await send_func(preview_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
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
    d['username'] = f"@{user.username}" if user.username else "No_Username"

    # Double check ID right before saving
    if check_id_owner(d['astu_id']):
        await query.edit_message_text("🚨 ይህ ID አሁን በሌላ ሰው ተይዟል! /start ብለው እንደገና ይሞክሩ።")
        return ConversationHandler.END

    save_member(d)

    kb = [
        [InlineKeyboardButton(TEXTS[lang]['chan_btn'], url=CHANNEL_URL)],
        [InlineKeyboardButton(TEXTS[lang]['sup_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    await query.edit_message_text(
        TEXTS[lang]['done'].format(admin=ADMIN_USERNAME),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

    # Send Quantum Alert to Admin Selman
    admin_alert = (
        f"🛸 **INCOMING ASTU NEXUS APPLICATION** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Student:** {d['name']}\n"
        f"🆔 **ASTU ID:** `{d['astu_id']}`\n"
        f"📱 **Phone:** `{d['phone']}`\n"
        f"🎓 **Batch:** {d['year']}\n"
        f"🎯 **Club:** {d['club']}\n"
        f"⚡ **Specialty:** {d['skill']}\n"
        f"🔗 **TG:** {d['username']} (`{user.id}`)\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    adm_kb = [[
        InlineKeyboardButton("✅ Approve Member", callback_data=f"adm_app_{user.id}"),
        InlineKeyboardButton("🗑️ Reject & Erase", callback_data=f"adm_rej_{user.id}")
    ]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_alert, reply_markup=InlineKeyboardMarkup(adm_kb), parse_mode="Markdown")
    return ConversationHandler.END

# ================= 2059 ADMIN COMMAND CENTER =================
async def render_admin_dashboard(send_func):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM members WHERE status LIKE 'Approved%'")
    app_cnt = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM members WHERE status LIKE 'Pending%'")
    pend_cnt = c.fetchone()[0]

    c.execute("SELECT club, COUNT(*) FROM members GROUP BY club")
    club_stats = "\n".join([f"  ▫️ {row[0]}: `{row[1]}`" for row in c.fetchall()]) or "  ▫️ No data yet"
    conn.close()

    dash_txt = (
        f"👑 **SELMAN'S QUANTUM ADMIN CONSOLE [2059]** 🛸\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Total Active Database:** `{total}`\n"
        f"✅ **Verified (Approved):** `{app_cnt}`\n"
        f"⏳ **Awaiting Action:** `{pend_cnt}`\n\n"
        f"📈 **Division Breakdown:**\n{club_stats}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    kb = [
        [InlineKeyboardButton("📥 Export CSV/Excel", callback_data="adm_export"),
         InlineKeyboardButton("📋 View Recent 10", callback_data="adm_list")],
        [InlineKeyboardButton("📢 Broadcast to All Members", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="open_admin")]
    ]
    await send_func(dash_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ **Access Denied:** Quantum signature mismatch.")
        return ConversationHandler.END
    await render_admin_dashboard(update.message.reply_text)
    return ConversationHandler.END

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id != ADMIN_ID:
        await query.answer("⛔ Unauthorized!", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data == "open_admin":
        await render_admin_dashboard(query.edit_message_text)

    elif data == "adm_export":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM members")
        rows = c.fetchall()
        conn.close()

        csv_path = "ASTU_Quantum_Members.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["User_ID", "Username", "Full_Name", "ASTU_ID", "Phone", "Year", "Club", "Skill", "Status", "Date"])
            writer.writerows(rows)

        await context.bot.send_document(
            chat_id=ADMIN_ID,
            document=open(csv_path, 'rb'),
            filename="ASTU_Members_2059.csv",
            caption="📊 **Quantum Database Export Complete!** (Rejected users are excluded).",
            parse_mode="Markdown"
        )

    elif data == "adm_list":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT full_name, astu_id, club, status FROM members ORDER BY rowid DESC LIMIT 10")
        rows = c.fetchall()
        conn.close()

        if not rows:
            txt = "📭 Database is currently empty."
        else:
            txt = "📋 **Last 10 Registered Students:**\n━━━━━━━━━━━━━━━━━━━━\n"
            for r in rows:
                txt += f"👤 **{r[0]}** (`{r[1]}`)\n   🎯 {r[2]} | {r[3]}\n\n"
        kb = [[InlineKeyboardButton("🔙 Back to Console", callback_data="open_admin")]]
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("adm_app_"):
        uid = int(data.split("_")[2])
        user_info = get_user(uid)
        if not user_info:
            await query.edit_message_text("⚠️ User no longer exists in DB.")
            return

        set_status_or_delete(uid, "approve")
        try:
            pass_card = (
                f"🎉 **APPLICATION APPROVED!** 🎉\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Welcome aboard, **{user_info['full_name']}**!\n"
                f"Your membership for **{user_info['club']}** has been officially verified by Admin {ADMIN_USERNAME}.\n\n"
                f"🆔 **ID:** `{user_info['astu_id']}`\n"
                f"📡 **Access Level:** `AUTHORIZED ✅`\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            kb = [[InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_URL)]]
            await context.bot.send_message(chat_id=uid, text=pass_card, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception:
            pass
        await query.edit_message_text(query.message.text + "\n\n✅ **VERIFIED & APPROVED BY SELMAN**", parse_mode="Markdown")

    elif data.startswith("adm_rej_"):
        uid = int(data.split("_")[2])
        # 3. ሙሉ በሙሉ ከዳታቤዝ ይሰረዛል!
        set_status_or_delete(uid, "reject")
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"🚨 **Application Update**\nYour ASTU Club registration was **declined** and erased from the database.\n\nIf you entered incorrect info, click /start to apply again, or contact {ADMIN_USERNAME}.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text(query.message.text + "\n\n🗑️ **REJECTED & ERASED FROM DATABASE**", parse_mode="Markdown")

# Broadcast Handler for Admin
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    await query.edit_message_text(
        "📢 **QUANTUM BROADCAST SYSTEM**\n\nለተመዘገቡት ተማሪዎች ሁሉ የሚላከውን መልዕክት ይጻፉ (ለማቋረጥ /cancel ይበሉ)፦",
        parse_mode="Markdown"
    )
    return BROADCAST_MSG

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM members")
    users = c.fetchall()
    conn.close()

    sent = 0
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u[0],
                text=f"📢 **ASTU TECH ANNOUNCEMENT** ⚡\n━━━━━━━━━━━━━━━━━━━━\n{msg}\n━━━━━━━━━━━━━━━━━━━━\n*From Admin {ADMIN_USERNAME}*",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(f"✅ ማስታወቂያው ለ `{sent}` ተማሪዎች በተሳካ ሁኔታ ተልኳል! /admin", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Process terminated. Press /start to initialize.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    # Global Admin & Approval Callbacks (ይህ ከConversation ውጪ ስለሆነ ምንጊዜም 100% ይሰራል!)
    app.add_handler(CommandHandler('admin', admin_cmd))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern='^(open_admin|adm_export|adm_list|adm_app_|adm_rej_)'))

    # Broadcast Conversation
    bcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern='^adm_broadcast$')],
        states={BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)]},
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
        per_message=False
    )
    app.add_handler(bcast_conv)

    # Student Registration Conversation
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG: [
                CallbackQueryHandler(select_language, pattern='^lang_'),
                CallbackQueryHandler(init_registration, pattern='^init_reg$')
            ],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASTU_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            PHONE: [MessageHandler((filters.CONTACT | filters.TEXT) & ~filters.COMMAND, get_phone)],
            YEAR: [CallbackQueryHandler(get_year, pattern='^yr_')],
            CLUB: [CallbackQueryHandler(get_club, pattern='^cl_')],
            SKILL: [
                CallbackQueryHandler(get_skill_btn, pattern='^sk_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_skill_text)
            ],
            CONFIRM: [CallbackQueryHandler(confirm_registration, pattern='^conf_')]
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start), CommandHandler('admin', admin_cmd)],
        per_message=False
    )
    app.add_handler(reg_conv)

    print("🛸 ASTU Quantum Bot 2059 is Online!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    keep_alive()
    main()
