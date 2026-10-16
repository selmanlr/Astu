import sqlite3
import csv
import os
import re
import html
import urllib.parse
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
ADMIN_USERNAME = "@Selman_Ali"
CHANNEL_URL = "https://t.me/astutechteam"
DB_NAME = "astu_v2.db"

LANG, NAME, ASTU_ID, PHONE, CLUB, SKILL, CONFIRM, BROADCAST_MSG = range(8)

def is_admin(user) -> bool:
    if not user:
        return False
    if user.id == ADMIN_ID:
        return True
    if user.username and user.username.lower() == ADMIN_USERNAME.replace("@", "").lower():
        return True
    return False

# ================= LIVE WEB PORTAL =================
app_web = Flask(__name__)

@app_web.route('/')
def home():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM members ORDER BY rowid DESC").fetchall()
    trs = "".join([
        f"<tr><td>{html.escape(r['full_name'])}</td><td><code>{r['astu_id']}</code></td>"
        f"<td>{r['year']}</td><td>{r['club']}</td><td>{r['status']}</td></tr>" for r in rows
    ])
    return f"""
    <html><head><meta charset="utf-8"><title>ASTU Portal</title>
    <style>
        body {{ font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 25px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #2563eb; }} code {{ color: #38bdf8; }}
    </style></head><body>
    <h2>🏛 ASTU Club Registry ({len(rows)} Active Members)</h2>
    <table><tr><th>Full Name</th><th>ASTU ID</th><th>Year</th><th>Club</th><th>Status</th></tr>
    {trs or '<tr><td colspan="5">No members yet.</td></tr>'}</table></body></html>
    """

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app_web.run(host='0.0.0.0', port=port), daemon=True).start()

# ================= DATABASE ENGINE =================
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
            lang TEXT,
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
        conn.execute('''INSERT OR REPLACE INTO members VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (d['user_id'], d['username'], d['name'], d['astu_id'], d['phone'],
             d['year'], d['club'], d['skill'], d['lang'], "Pending", now))

def update_db_status(user_id, action):
    with sqlite3.connect(DB_NAME) as conn:
        if action == "approve":
            conn.execute("UPDATE members SET status='Approved' WHERE user_id=?", (user_id,))
        elif action == "reject":
            conn.execute("DELETE FROM members WHERE user_id=?", (user_id,))

def generate_qr_url(name, astu_id, club, year):
    data = urllib.parse.quote(f"ASTU VERIFIED MEMBER\nName: {name}\nID: {astu_id}\nClub: {club}\nBatch: {year}\nAdmin: {ADMIN_USERNAME}")
    return f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&ecc=H&margin=20&color=0f172a&bgcolor=38bdf8&data={data}"

init_db()

# ================= STRICT 100% SEPARATED LANGUAGE PACKS =================
LANGUAGES = {
    'en': {
        'home': "🏛 <b>ASTU Club Registration Portal</b>\n━━━━━━━━━━━━━━━━━━━━\nWelcome to Adama Science & Technology University's official club system.",
        'reg_btn': "📝 Register for a Club",
        'chan_btn': "📢 Official Channel",
        'sup_btn': "💬 Contact Support",
        'qr_btn': "🪪 Download QR ID Card",
        'already_reg': (
            "👋 <b>Hello {name}, you are already registered!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🆔 <b>ID:</b> <code>{astu_id}</code>\n"
            "🎓 <b>Year:</b> {year}\n"
            "🎯 <b>Club:</b> {club}\n"
            "📊 <b>Status:</b> <b>{status}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ <i>Duplicate registration is not allowed. For changes, contact {admin}.</i>"
        ),
        'status_map': {'Pending': 'Pending Review ⏳', 'Approved': 'Approved ✅'},
        'batch_map': {19: "1st Year (Freshman)", 18: "2nd Year", 17: "3rd Year", 16: "4th Year", 15: "5th Year (GC)"},
        'batch_def': "Batch of '{num}",
        'ask_name': "👤 <b>Step 1/4:</b> Please enter your <b>Full Name</b>:",
        'ask_id': "🆔 <b>Step 2/4:</b> Enter your <b>ASTU ID</b> (e.g., <code>UGR/43400/19</code>):",
        'err_id': "❌ <b>Invalid ID Format!</b>\nPlease follow the proper ASTU format (e.g., <code>UGR/43400/19</code>):",
        'taken_id': "⚠️ <b>ID Already Registered!</b>\nThe ID <code>{id}</code> belongs to <b>{name}</b>. Please enter your own valid ASTU ID:",
        'ask_ph': "📱 <b>Step 3/4:</b> Detected Year: <b>{year}</b> ✅\n\nPlease share your <b>Phone Number</b> using the button below, or type it:",
        'share_ph': "📲 Share My Phone Number",
        'err_ph': "❌ Invalid phone number! Please enter a valid number (<code>09...</code> or <code>07...</code>):",
        'ask_club': "🎯 <b>Step 4/4:</b> Choose the <b>ASTU Club</b> you want to join:",
        'clubs': [
            "💻 CSEC ASTU (Competitive Programming)",
            "🤖 AI & Robotics Club",
            "🛡️ Cyber Security Club",
            "🚀 Space Science & Astronomy (ESSS)",
            "💡 Innovation & Entrepreneurship",
            "🎨 Media & Digital Arts Club"
        ],
        'ask_skill': "⚡ Select your <b>Primary Skill</b> below, or type it directly:",
        'skills': [
            ["🐍 Python / AI", "🌐 Web Development"],
            ["📱 Mobile Apps", "🎨 Graphic / UI Design"],
            ["🛡️ Cyber Security", "🎬 Video Editing"],
            ["🚀 Beginner (Ready to Learn)"]
        ],
        'review': (
            "📋 <b>Confirm Your Details</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Full Name:</b> {name}\n"
            "🆔 <b>ASTU ID:</b> <code>{astu_id}</code>\n"
            "🎓 <b>Academic Year:</b> {year}\n"
            "📱 <b>Phone:</b> <code>{phone}</code>\n"
            "🎯 <b>Selected Club:</b> {club}\n"
            "⚡ <b>Skill:</b> {skill}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Would you like to submit your application?"
        ),
        'sub_btn': "✅ Submit Application",
        'cancel_btn': "🔄 Start Over",
        'cancelled': "🔄 Registration cancelled. Press /start to begin again.",
        'done': "✅ <b>Application Submitted Successfully!</b>\n\nYour registration has been sent to Admin {admin}. You will receive your <b>Digital QR ID Card</b> once approved!",
        'qr_caption': (
            "🪪 <b>ASTU DIGITAL MEMBERSHIP PASS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Name:</b> {name}\n"
            "🆔 <b>ID:</b> <code>{astu_id}</code>\n"
            "🎓 <b>Year:</b> {year}\n"
            "🎯 <b>Club:</b> {club}\n"
            "📊 <b>Status:</b> <b>{status}</b>"
        ),
        'app_msg': "🎉 <b>CONGRATULATIONS {name}!</b>\n━━━━━━━━━━━━━━━━━━━━\nYour application for <b>{club}</b> has been <b>APPROVED</b> by Admin {admin}!\nHere is your official Digital QR Membership Pass.",
        'rej_msg': "❌ <b>Application Declined</b>\nYour club registration was rejected and removed from our database. You may press /start to apply again with valid details, or contact {admin}."
    },

    'am': {
        'home': "🏛 <b>የASTU ክለቦች መመዝገቢያ ፖርታል</b>\n━━━━━━━━━━━━━━━━━━━━\nእንኳን ወደ አዳማ ሳይንስና ቴክኖሎጂ ዩኒቨርሲቲ ዘመናዊ የክለቦች መመዝገቢያ በደህና መጡ።",
        'reg_btn': "📝 ለክለብ ተመዝገብ",
        'chan_btn': "📢 ቻናላችንን ይቀላቀሉ",
        'sup_btn': "💬 እርዳታ ለማግኘት",
        'qr_btn': "🪪 የQR መታወቂያ ካርዴን አውርድ",
        'already_reg': (
            "👋 <b>ሰላም {name}፣ ቀድሞውኑ ተመዝግበዋል!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🆔 <b>መታወቂያ፦</b> <code>{astu_id}</code>\n"
            "🎓 <b>ዓመት፦</b> {year}\n"
            "🎯 <b>ክለብ፦</b> {club}\n"
            "📊 <b>ሁኔታ፦</b> <b>{status}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ <i>ድጋሚ መመዝገብ አይቻልም። ማስተካከያ ካለዎት {admin} ያነጋግሩ።</i>"
        ),
        'status_map': {'Pending': 'በመጠባበቅ ላይ ⏳', 'Approved': 'ጸድቋል ✅'},
        'batch_map': {19: "1ኛ ዓመት (Freshman)", 18: "2ኛ ዓመት", 17: "3ኛ ዓመት", 16: "4ኛ ዓመት", 15: "5ኛ ዓመት (GC)"},
        'batch_def': "የ {num} ባች",
        'ask_name': "👤 <b>ደረጃ 1/4፦</b> እባክዎ <b>ሙሉ ስምዎን</b> ይጻፉ፦",
        'ask_id': "🆔 <b>ደረጃ 2/4፦</b> የ<b>ASTU መታወቂያ ቁጥርዎን</b> ያስገቡ (ለምሳሌ፦ <code>UGR/43400/19</code>)፦",
        'err_id': "❌ <b>የተሳሳተ የID አጻጻፍ!</b>\nእባክዎ ትክክለኛውን የASTU ፎርማት ይጠቀሙ (ለምሳሌ፦ <code>UGR/43400/19</code>)፦",
        'taken_id': "⚠️ <b>ይህ መታወቂያ ቁጥር ተይዟል!</b>\nይህ ID (<code>{id}</code>) ቀድሞ በ <b>{name}</b> ስም ተመዝግቧል! እባክዎ የራስዎን ትክክለኛ ID ያስገቡ፦",
        'ask_ph': "📱 <b>ደረጃ 3/4፦</b> የትምህርት ዓመት፦ <b>{year}</b> ✅\n\nከታች ያለውን በተን በመጫን ወይም በመጻፍ <b>ስልክ ቁጥርዎን</b> ያስገቡ፦",
        'share_ph': "📲 ስልክ ቁጥሬን ላክ",
        'err_ph': "❌ የተሳሳተ ስልክ ቁጥር! እባክዎ ትክክለኛ ስልክ ቁጥር ያስገቡ (<code>09...</code> ወይም <code>07...</code>)፦",
        'ask_club': "🎯 <b>ደረጃ 4/4፦</b> መግባት የሚፈልጉትን <b>የASTU ክለብ</b> ይምረጡ፦",
        'clubs': [
            "💻 CSEC ASTU (ፕሮግራሚንግና ሶፍትዌር)",
            "🤖 AI & Robotics (ሮቦቲክስና AI ክለብ)",
            "🛡️ Cyber Security (ሳይበር ሴኩሪቲ ክለብ)",
            "🚀 Space Science (ስፔስ ሳይንስና አስትሮኖሚ)",
            "💡 Innovation (ፈጠራና ኢንተርፕረነርሺፕ)",
            "🎨 Digital Arts (ሚዲያና ዲጂታል አርት)"
        ],
        'ask_skill': "⚡ ያለዎትን <b>ልዩ ችሎታ</b> ከታች ይምረጡ ወይም በእጅዎ ይጻፉ፦",
        'skills': [
            ["🐍 ፓይተን / AI", "🌐 ዌብሳይት ግንባታ"],
            ["📱 ሞባይል አፕሊኬሽን", "🎨 ግራፊክስ ዲዛይን"],
            ["🛡️ ሳይበር ሴኩሪቲ", "🎬 ቪዲዮ ኤዲቲንግ"],
            ["🚀 ጀማሪ ነኝ (ለመማር ዝግጁ)"]
        ],
        'review': (
            "📋 <b>መረጃዎን ያረጋግጡ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>ሙሉ ስም፦</b> {name}\n"
            "🆔 <b>መታወቂያ፦</b> <code>{astu_id}</code>\n"
            "🎓 <b>የትምህርት ዓመት፦</b> {year}\n"
            "📱 <b>ስልክ ቁጥር፦</b> <code>{phone}</code>\n"
            "🎯 <b>የተመረጠው ክለብ፦</b> {club}\n"
            "⚡ <b>ልዩ ችሎታ፦</b> {skill}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "መረጃው ትክክል ነው? ወደ አድሚኑ ይላክ?"
        ),
        'sub_btn': "✅ አረጋግጥና ላክ",
        'cancel_btn': "🔄 እንደገና ጀምር",
        'cancelled': "🔄 ምዝገባው ተቋርጧል። እንደገና ለመጀመር /start ይበሉ።",
        'done': "✅ <b>ምዝገባዎ በተሳካ ሁኔታ ተልኳል!</b>\n\nመረጃዎ ለአድሚን {admin} ደርሷል። ልክ ሲጸድቅልዎ <b>የዲጂታል QR መታወቂያ ካርድ</b> እዚሁ ይላክልዎታል!",
        'qr_caption': (
            "🪪 <b>የASTU ክለቦች ዲጂታል መታወቂያ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>ስም፦</b> {name}\n"
            "🆔 <b>መታወቂያ፦</b> <code>{astu_id}</code>\n"
            "🎓 <b>ዓመት፦</b> {year}\n"
            "🎯 <b>ክለብ፦</b> {club}\n"
            "📊 <b>ሁኔታ፦</b> <b>{status}</b>"
        ),
        'app_msg': "🎉 <b>እንኳን ደስ አለዎት {name}!</b>\n━━━━━━━━━━━━━━━━━━━━\nለ <b>{club}</b> ያቀረቡት የአባልነት ጥያቄ በአድሚን {admin} <b>ጸድቋል!</b>\nይህ የእርስዎ ህጋዊ የQR መታወቂያ ካርድ ነው።",
        'rej_msg': "❌ <b>የምዝገባ ማሳወቂያ</b>\nለASTU ክለብ ያደረጉት ምዝገባ ውድቅ ተደርጓል (ከመዝገብም ተሰርዟል)። በትክክለኛ መረጃ እንደገና ለመመዝገብ /start ይበሉ፣ ወይም {admin} ያነጋግሩ።"
    },

    'om': {
        'home': "🏛 <b>Wiirtuu Galmee Kilaboota ASTU</b>\n━━━━━━━━━━━━━━━━━━━━\nBaga gara sirna galmee kilaboota Yuunivarsiitii Saayinsii fi Teeknooloojii Adaamaa nagaan dhuftan.",
        'reg_btn': "📝 Kilabiitti Galmaa'i",
        'chan_btn': "📢 Chaanaalii Keenya",
        'sup_btn': "💬 Gargaarsa Argachuuf",
        'qr_btn': "🪪 Waraqaa Eenyummaa QR Buufadhu",
        'already_reg': (
            "👋 <b>Akkam {name}, duraan galmooftaniittu!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🆔 <b>ID:</b> <code>{astu_id}</code>\n"
            "🎓 <b>Waggaa:</b> {year}\n"
            "🎯 <b>Kilabii:</b> {club}\n"
            "📊 <b>Haala:</b> <b>{status}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ <i>Irra deebi'anii galmaa'uun hin danda'amu. Jijjiiramaaf {admin} quunnamaa.</i>"
        ),
        'status_map': {'Pending': 'Eegumsa Irra ⏳', 'Approved': 'Mirkanaa\'eera ✅'},
        'batch_map': {19: "Waggaa 1ffaa (Freshman)", 18: "Waggaa 2ffaa", 17: "Waggaa 3ffaa", 16: "Waggaa 4ffaa", 15: "Waggaa 5ffaa (GC)"},
        'batch_def': "Bara '{num}",
        'ask_name': "👤 <b>Sadarkaa 1/4:</b> Maaloo <b>Maqaa Guutuu</b> keessan barreessaa:",
        'ask_id': "🆔 <b>Sadarkaa 2/4:</b> <b>Waraqaa Eenyummaa ASTU (ID)</b> galchaa (Fkn: <code>UGR/43400/19</code>):",
        'err_id': "❌ <b>ID Dogoggoraa!</b>\nMaaloo haala sirriin barreessaa (Fkn: <code>UGR/43400/19</code>):",
        'taken_id': "⚠️ <b>ID kun duraan qabameera!</b>\nID <code>{id}</code> maqaa <b>{name}</b> jedhuun galmaa'eera. Maaloo ID keessan qofa galchaa:",
        'ask_ph': "📱 <b>Sadarkaa 3/4:</b> Waggaa Barnootaa: <b>{year}</b> ✅\n\nabbaa furtuu gadii tuquun ykn barreessuun <b>Lakkoofsa Bilbilaa</b> keessan ergaa:",
        'share_ph': "📲 Lakkoofsa Bilbilaa Koo Ergi",
        'err_ph': "❌ Lakkoofsi bilbilaa sirrii miti! Maaloo lakkoofsa sirrii galchaa (<code>09...</code> ykn <code>07...</code>):",
        'ask_club': "🎯 <b>Sadarkaa 4/4:</b> <b>Kilabii ASTU</b> itti makamuu barbaaddan filadhaa:",
        'clubs': [
            "💻 CSEC ASTU (Piroogiraamiingii fi Sooftiweerii)",
            "🤖 Kilabii AI fi Roobootiksii",
            "🛡️ Kilabii Saayibar Sekyuuriitii",
            "🚀 Saayinsii Hawaa fi Astroonoomii (ESSS)",
            "💡 Kalaqaa fi Intarpiraanarshiippii",
            "🎨 Miidiyaa fi Ogummaa Dijitaalaa"
        ],
        'ask_skill': "⚡ <b>Dandeettii Addaa (Skill)</b> qabdan filadhaa ykn barreessaa:",
        'skills': [
            ["🐍 Python / AI", "🌐 Web Development"],
            ["📱 Appii Moobaayilaa", "🎨 Giraafiksii fi Dizaayinii"],
            ["🛡️ Saayibar Sekyuuriitii", "🎬 Viidiyoo Gulaaluu"],
            ["🚀 Jalqabaa (Barachuuf Qophii)"]
        ],
        'review': (
            "📋 <b>Odeeffannoo Keessan Mirkaneessaa</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Maqaa Guutuu:</b> {name}\n"
            "🆔 <b>ID ASTU:</b> <code>{astu_id}</code>\n"
            "🎓 <b>Waggaa:</b> {year}\n"
            "📱 <b>Bilbila:</b> <code>{phone}</code>\n"
            "🎯 <b>Kilabii:</b> {club}\n"
            "⚡ <b>Dandeettii:</b> {skill}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Odeeffannoon kun sirriidhaa? Ergamuu?"
        ),
        'sub_btn': "✅ Mirkaneessiitii Ergi",
        'cancel_btn': "🔄 Irra Deebi'i",
        'cancelled': "🔄 Galmeen haqameera. Jalqabuuf /start tuqaa.",
        'done': "✅ <b>Galmeen Keessan Milkaa'inaan Ergameera!</b>\n\nYemmuu Admin {admin} mirkaneessu <b>Waraqaa Eenyummaa QR</b> isiniif ergama!",
        'qr_caption': (
            "🪪 <b>WARAQAA EENYUMMAA KILABOOTA ASTU</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>Maqaa:</b> {name}\n"
            "🆔 <b>ID:</b> <code>{astu_id}</code>\n"
            "🎓 <b>Waggaa:</b> {year}\n"
            "🎯 <b>Kilabii:</b> {club}\n"
            "📊 <b>Haala:</b> <b>{status}</b>"
        ),
        'app_msg': "🎉 <b>BAGA GAMMADDAN {name}!</b>\n━━━━━━━━━━━━━━━━━━━━\nIyyanni miseensummaa <b>{club}</b> Admin {admin} biratti <b>MIRKANAA'EERA!</b>\nKun Waraqaa Eenyummaa QR keessani.",
        'rej_msg': "❌ <b>Beeksisa Galmee</b>\nGalmeen kilabii keessan fudhatama hin argatin hafee haqameera. Odeeffannoo sirriin galmaa'uuf /start tuqaa, ykn {admin} quunnamaa."
    },

    'ti': {
        'home': "🏛 <b>መመዝገቢ ክለባት ASTU</b>\n━━━━━━━━━━━━━━━━━━━━\nእንቋዕ ናብ ወግዓዊ መመዝገቢ ክለባት ዩኒቨርሲቲ ሳይንስን ቴክኖሎጂን ኣዳማ ብደሓን መጻእኩም።",
        'reg_btn': "📝 ንክለብ ተመዝገብ",
        'chan_btn': "📢 ቻናልና ተጸንበሩ",
        'sup_btn': "💬 ሓገዝ ንምርካብ",
        'qr_btn': "🪪 ናይ QR መንነት ካርድ ኣውርድ",
        'already_reg': (
            "👋 <b>ሰላም {name}፣ ኣቐዲምኩም ተመዝጊብኩም ኢኹም!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🆔 <b>መንነት (ID)፦</b> <code>{astu_id}</code>\n"
            "🎓 <b>ዓመት፦</b> {year}\n"
            "🎯 <b>ክለብ፦</b> {club}\n"
            "📊 <b>ኩነታት፦</b> <b>{status}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ <i>ደጊምካ ምምዝጋብ ኣይከኣልን። ምስትኽኻል እንተሃልዩኩም ን {admin} ኣዘራርቡ።</i>"
        ),
        'status_map': {'Pending': 'ኣብ ምጽባይ ⏳', 'Approved': 'ጸዲቑ ✅'},
        'batch_map': {19: "1ይ ዓመት (Freshman)", 18: "2ይ ዓመት", 17: "3ይ ዓመት", 16: "4ይ ዓመት", 15: "5ይ ዓመት (GC)"},
        'batch_def': "ናይ '{num} ተምሃራይ",
        'ask_name': "👤 <b>ደረጃ 1/4፦</b> ብኽብረትኩም <b>ምሉእ ሽምኩም</b> ጸሓፉ፦",
        'ask_id': "🆔 <b>ደረጃ 2/4፦</b> ናይ <b>ASTU መንነት ቁጽሪ (ID)</b> የእትዉ (ንኣብነት፦ <code>UGR/43400/19</code>)፦",
        'err_id': "❌ <b>ጌጋ ኣጸሓሕፋ ID!</b>\nብኽብረትኩም ብትኽክል ጸሓፉ (ንኣብነት፦ <code>UGR/43400/19</code>)፦",
        'taken_id': "⚠️ <b>እዚ መንነት ቁጽሪ ተታሒዙ እዩ!</b>\nእዚ ID (<code>{id}</code>) ኣቐዲሙ ብ <b>{name}</b> ተመዝጊቡ ኣሎ! ብኽብረትኩም ናይ ባዕልኹም ID የእትዉ፦",
        'ask_ph': "📱 <b>ደረጃ 3/4፦</b> ናይ ትምህርቲ ዓመት፦ <b>{year}</b> ✅\n\nኣብ ታሕቲ ዘሎ መጠወቒ ብምጥዋቕ ወይ ብምጽሓፍ <b>ቁጽሪ ስልክኹም</b> ስደዱ፦",
        'share_ph': "📲 ቁጽሪ ስልከይ ስደድ",
        'err_ph': "❌ ጌጋ ቁጽሪ ስልኪ! ብኽብረትኩም ትኽክለኛ ቁጽሪ የእትዉ (<code>09...</code> ወይ <code>07...</code>)፦",
        'ask_club': "🎯 <b>ደረጃ 4/4፦</b> ክትኣትውዎ እትደልዩ <b>ክለብ</b> ምረጹ፦",
        'clubs': [
            "💻 CSEC ASTU (ፕሮግራሚንግን ሶፍትዌርን)",
            "🤖 AI & Robotics (ሮቦቲክስን AI ክለብ)",
            "🛡️ Cyber Security (ሳይበር ሴኩሪቲ ክለብ)",
            "🚀 Space Science (ስፔስ ሳይንስን ኣስትሮኖሚን)",
            "💡 Innovation (ምህዞን ኢንተርፕረነርሺፕን)",
            "🎨 Digital Arts (ሚዲያን ዲጂታል ኣርትን)"
        ],
        'ask_skill': "⚡ ዘለኩም <b>ፍሉይ ክእለት</b> ምረጹ ወይ ብኢድኩም ጸሓፉ፦",
        'skills': [
            ["🐍 ፓይተን / AI", "🌐 ዌብሳይት ምስራሕ"],
            ["📱 ሞባይል ኣፕሊኬሽን", "🎨 ግራፊክስ ዲዛይን"],
            ["🛡️ ሳይበር ሴኩሪቲ", "🎬 ቪዲዮ ኤዲቲንግ"],
            ["🚀 ጀማሪ እየ (ንምምሃር ድሉው)"]
        ],
        'review': (
            "📋 <b>ሓበሬታኹም ኣረጋግጹ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>ምሉእ ሽም፦</b> {name}\n"
            "🆔 <b>መንነት (ID)፦</b> <code>{astu_id}</code>\n"
            "🎓 <b>ዓመት፦</b> {year}\n"
            "📱 <b>ስልኪ፦</b> <code>{phone}</code>\n"
            "🎯 <b>ክለብ፦</b> {club}\n"
            "⚡ <b>ክእለት፦</b> {skill}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "እዚ ሓበሬታ ትኽክል ድዩ? ናብ ኣድሚን ክለኣኽ?"
        ),
        'sub_btn': "✅ ኣረጋግጽን ስደድን",
        'cancel_btn': "🔄 ካብ መጀመርታ ጀምር",
        'cancelled': "🔄 ምዝገባ ተቛሪጹ። ንምጅማር /start ጠውቑ።",
        'done': "✅ <b>ምዝገባኹም ብዓወት ተላኢኹ!</b>\n\nኣድሚን {admin} ምስ ኣጽደቖ <b>ናይ QR መንነት ካርድ</b> ክለኣኸልኩም እዩ!",
        'qr_caption': (
            "🪪 <b>ናይ ASTU ክለባት ዲጂታል መንነት</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👤 <b>ሽም፦</b> {name}\n"
            "🆔 <b>ID፦</b> <code>{astu_id}</code>\n"
            "🎓 <b>ዓመት፦</b> {year}\n"
            "🎯 <b>ክለብ፦</b> {club}\n"
            "📊 <b>ኩነታት፦</b> <b>{status}</b>"
        ),
        'app_msg': "🎉 <b>እንቋዕ ደስ በለኩም {name}!</b>\n━━━━━━━━━━━━━━━━━━━━\nን <b>{club}</b> ዘቕረብኩምዎ ሕቶ ብኣድሚን {admin} <b>ጸዲቑ ኣሎ!</b>\nእዚ ናይ ኣባልነት QR ካርድኹም እዩ።",
        'rej_msg': "❌ <b>ምልክታ ምዝገባ</b>\nናይ ክለብ ምዝገባኹም ተነጺጉ (ካብ መዝገብ ተሰሪዙ) ኣሎ። ብትኽክለኛ ሓበሬታ ንምምዝጋብ /start ጠውቑ ወይ ን {admin} ኣዘራርቡ።"
    }
}

def get_batch_text(astu_id: str, lang: str) -> str:
    num = int(astu_id.split('/')[-1])
    t = LANGUAGES[lang]
    return t['batch_map'].get(num, t['batch_def'].format(num=num))

# ================= STUDENT HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(user.id)

    if existing:
        lang = existing.get('lang', 'en')
        if lang not in LANGUAGES:
            lang = 'en'
        t = LANGUAGES[lang]
        st_display = t['status_map'].get(existing['status'], existing['status'])

        kb = [
            [InlineKeyboardButton(t['qr_btn'], callback_data="get_my_qr")],
            [InlineKeyboardButton(t['chan_btn'], url=CHANNEL_URL),
             InlineKeyboardButton(t['sup_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
        ]
        if is_admin(user):
            kb.insert(0, [InlineKeyboardButton("👑 Admin Control Panel", callback_data="open_admin")])

        msg = t['already_reg'].format(
            name=html.escape(existing['full_name']),
            astu_id=existing['astu_id'],
            year=existing['year'],
            club=html.escape(existing['club']),
            status=st_display,
            admin=ADMIN_USERNAME
        )
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return ConversationHandler.END

    kb = [
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'),
         InlineKeyboardButton("🇪🇹 አማርኛ", callback_data='lang_am')],
        [InlineKeyboardButton("🌳 Afaan Oromoo", callback_data='lang_om'),
         InlineKeyboardButton("🌾 ትግርኛ", callback_data='lang_ti')]
    ]
    if is_admin(user):
        kb.append([InlineKeyboardButton("👑 Admin Control Panel", callback_data="open_admin")])

    await update.message.reply_text(
        "🏛 <b>ASTU Smart Club Portal</b>\n━━━━━━━━━━━━━━━━━━━━\nPlease select your language / እባክዎ ቋንቋ ይምረጡ፦",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML"
    )
    return LANG

async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    t = LANGUAGES[lang]

    kb = [
        [InlineKeyboardButton(t['reg_btn'], callback_data='init_reg')],
        [InlineKeyboardButton(t['chan_btn'], url=CHANNEL_URL),
         InlineKeyboardButton(t['sup_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    if is_admin(update.effective_user):
        kb.append([InlineKeyboardButton("👑 Admin Control Panel", callback_data="open_admin")])

    await query.edit_message_text(t['home'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return LANG

async def init_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'en')
    t = LANGUAGES[lang]

    if get_user(update.effective_user.id):
        await query.edit_message_text("⚠️ /start")
        return ConversationHandler.END

    await query.edit_message_text(t['ask_name'], parse_mode="HTML")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip().title()
    lang = context.user_data.get('lang', 'en')
    await update.message.reply_text(LANGUAGES[lang]['ask_id'], parse_mode="HTML")
    return ASTU_ID

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    astu_id = update.message.text.strip().upper()
    lang = context.user_data.get('lang', 'en')
    t = LANGUAGES[lang]

    if not re.match(r"^(UGR|PGR|BSC|MSC)/\d{3,6}/\d{2}$", astu_id):
        await update.message.reply_text(t['err_id'], parse_mode="HTML")
        return ASTU_ID

    owner = check_id_owner(astu_id)
    if owner:
        await update.message.reply_text(
            t['taken_id'].format(id=astu_id, name=html.escape(owner['full_name'])),
            parse_mode="HTML"
        )
        return ASTU_ID

    detected_year = get_batch_text(astu_id, lang)
    context.user_data['astu_id'] = astu_id
    context.user_data['year'] = detected_year

    kb = [[KeyboardButton(t['share_ph'], request_contact=True)]]
    await update.message.reply_text(
        t['ask_ph'].format(year=detected_year),
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="HTML"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    t = LANGUAGES[lang]
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip().replace(" ", "")
        if not re.match(r"^(\+?251|0)(9|7)\d{8}$", phone):
            await update.message.reply_text(t['err_ph'], parse_mode="HTML")
            return PHONE

    context.user_data['phone'] = phone
    temp = await update.message.reply_text("🔄...", reply_markup=ReplyKeyboardRemove())
    await temp.delete()

    kb = [[InlineKeyboardButton(c, callback_data=f"cl_{i}")] for i, c in enumerate(t['clubs'])]
    await update.message.reply_text(t['ask_club'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return CLUB

async def get_club(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'en')
    t = LANGUAGES[lang]

    idx = int(query.data.replace("cl_", ""))
    context.user_data['club'] = t['clubs'][idx]

    kb = [[InlineKeyboardButton(s, callback_data=f"sk_{r}_{c}") for c, s in enumerate(row)] for r, row in enumerate(t['skills'])]
    await query.edit_message_text(t['ask_skill'], reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return SKILL

async def get_skill_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'en')
    parts = query.data.split("_")
    r, c = int(parts[1]), int(parts[2])
    context.user_data['skill'] = LANGUAGES[lang]['skills'][r][c]
    return await show_preview(query.edit_message_text, context)

async def get_skill_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['skill'] = update.message.text.strip()
    return await show_preview(update.message.reply_text, context)

async def show_preview(send_func, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    t = LANGUAGES[lang]
    d = context.user_data

    kb = [
        [InlineKeyboardButton(t['sub_btn'], callback_data="conf_yes")],
        [InlineKeyboardButton(t['cancel_btn'], callback_data="conf_no")]
    ]
    txt = t['review'].format(
        name=html.escape(d['name']),
        astu_id=d['astu_id'],
        year=d['year'],
        phone=d['phone'],
        club=html.escape(d['club']),
        skill=html.escape(d['skill'])
    )
    await send_func(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    return CONFIRM

async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'en')
    t = LANGUAGES[lang]

    if query.data == "conf_no":
        await query.edit_message_text(t['cancelled'], parse_mode="HTML")
        return ConversationHandler.END

    user = update.effective_user
    d = context.user_data
    d['user_id'] = user.id
    d['username'] = f"@{user.username}" if user.username else "No_Username"
    d['lang'] = lang

    if check_id_owner(d['astu_id']):
        await query.edit_message_text(t['cancelled'], parse_mode="HTML")
        return ConversationHandler.END

    save_member(d)

    kb = [
        [InlineKeyboardButton(t['qr_btn'], callback_data="get_my_qr")],
        [InlineKeyboardButton(t['chan_btn'], url=CHANNEL_URL),
         InlineKeyboardButton(t['sup_btn'], url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")]
    ]
    await query.edit_message_text(t['done'].format(admin=ADMIN_USERNAME), reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    # Notify Admin safely using HTML
    admin_alert = (
        f"🔔 <b>NEW ASTU CLUB APPLICATION</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> {html.escape(d['name'])}\n"
        f"🆔 <b>ID:</b> <code>{d['astu_id']}</code>\n"
        f"🎓 <b>Year:</b> {d['year']}\n"
        f"📱 <b>Phone:</b> <code>{d['phone']}</code>\n"
        f"🎯 <b>Club:</b> {html.escape(d['club'])}\n"
        f"⚡ <b>Skill:</b> {html.escape(d['skill'])}\n"
        f"🌐 <b>Lang:</b> {lang.upper()}\n"
        f"🔗 <b>TG:</b> {html.escape(d['username'])} (<code>{user.id}</code>)"
    )
    adm_kb = [[
        InlineKeyboardButton("✅ Approve & Send QR", callback_data=f"adm_app_{user.id}"),
        InlineKeyboardButton("🗑️ Reject & Delete", callback_data=f"adm_rej_{user.id}")
    ]]
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_alert, reply_markup=InlineKeyboardMarkup(adm_kb), parse_mode="HTML")
    except Exception as e:
        print(f"Admin notify error: {e}")

    return ConversationHandler.END

# ================= QR CARD GENERATOR =================
async def send_qr_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u = get_user(update.effective_user.id)
    if not u:
        await query.answer("❌ Not registered! Press /start", show_alert=True)
        return

    await query.answer("🪪 Generating QR Card...")
    lang = u.get('lang', 'en')
    if lang not in LANGUAGES:
        lang = 'en'
    t = LANGUAGES[lang]
    st_display = t['status_map'].get(u['status'], u['status'])

    qr_url = generate_qr_url(u['full_name'], u['astu_id'], u['club'], u['year'])
    caption = t['qr_caption'].format(
        name=html.escape(u['full_name']),
        astu_id=u['astu_id'],
        year=u['year'],
        club=html.escape(u['club']),
        status=st_display
    )
    await context.bot.send_photo(chat_id=u['user_id'], photo=qr_url, caption=caption, parse_mode="HTML")

# ================= BULLETPROOF ADMIN PANEL (HTML) =================
async def render_admin_panel(send_func):
    with sqlite3.connect(DB_NAME) as conn:
        total = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        app_cnt = conn.execute("SELECT COUNT(*) FROM members WHERE status='Approved'").fetchone()[0]
        pend_cnt = conn.execute("SELECT COUNT(*) FROM members WHERE status='Pending'").fetchone()[0]
        clubs = conn.execute("SELECT club, COUNT(*) FROM members GROUP BY club").fetchall()

    c_stats = "\n".join([f"▫️ {html.escape(c[0])}: <code>{c[1]}</code>" for c in clubs]) or "▫️ No members yet"
    txt = (
        f"👑 <b>ASTU ADMIN CONTROL PANEL ({ADMIN_USERNAME})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Total Active:</b> <code>{total}</code>\n"
        f"✅ <b>Approved:</b> <code>{app_cnt}</code>\n"
        f"⏳ <b>Pending:</b> <code>{pend_cnt}</code>\n\n"
        f"📈 <b>Club Breakdown:</b>\n{c_stats}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    kb = [
        [InlineKeyboardButton("📥 Download Excel (CSV)", callback_data="adm_export"),
         InlineKeyboardButton("📋 Last 10 Members", callback_data="adm_list")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔄 Refresh Panel", callback_data="open_admin")]
    ]
    await send_func(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text(f"⛔ Unauthorized! Your Telegram ID is: <code>{update.effective_user.id}</code>", parse_mode="HTML")
        return ConversationHandler.END
    await render_admin_panel(update.message.reply_text)
    return ConversationHandler.END

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user):
        await query.answer("⛔ Admin Only!", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data == "open_admin":
        await render_admin_panel(query.edit_message_text)

    elif data == "adm_export":
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT * FROM members").fetchall()
        csv_file = "ASTU_Members.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(["User_ID", "Username", "Full_Name", "ASTU_ID", "Phone", "Year", "Club", "Skill", "Lang", "Status", "Date"])
            w.writerows(rows)
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=open(csv_file, 'rb'),
            caption="📊 <b>Exported ASTU Club Members (CSV)</b>",
            parse_mode="HTML"
        )

    elif data == "adm_list":
        with sqlite3.connect(DB_NAME) as conn:
            rows = conn.execute("SELECT full_name, astu_id, club, status FROM members ORDER BY rowid DESC LIMIT 10").fetchall()
        if not rows:
            txt = "📭 Database is empty."
        else:
            txt = "📋 <b>Last 10 Registered Members:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            for r in rows:
                txt += f"👤 <b>{html.escape(r[0])}</b> (<code>{r[1]}</code>)\n   🎯 {html.escape(r[2])} — <b>{r[3]}</b>\n\n"
        await query.edit_message_text(
            txt,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="open_admin")]]),
            parse_mode="HTML"
        )

    elif data.startswith("adm_app_"):
        uid = int(data.split("_")[2])
        u = get_user(uid)
        if not u:
            await query.edit_message_text("⚠️ User not found in database.")
            return

        update_db_status(uid, "approve")
        lang = u.get('lang', 'en')
        if lang not in LANGUAGES:
            lang = 'en'
        t = LANGUAGES[lang]

        qr_url = generate_qr_url(u['full_name'], u['astu_id'], u['club'], u['year'])
        caption = t['app_msg'].format(
            name=html.escape(u['full_name']),
            club=html.escape(u['club']),
            admin=ADMIN_USERNAME
        )
        try:
            await context.bot.send_photo(
                chat_id=uid, photo=qr_url, caption=caption,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t['chan_btn'], url=CHANNEL_URL)]]),
                parse_mode="HTML"
            )
        except Exception:
            pass
        await query.edit_message_text(query.message.text_html + "\n\n✅ <b>STATUS: APPROVED & QR SENT</b>", parse_mode="HTML")

    elif data.startswith("adm_rej_"):
        uid = int(data.split("_")[2])
        u = get_user(uid)
        lang = u.get('lang', 'en') if u else 'en'
        if lang not in LANGUAGES:
            lang = 'en'
        t = LANGUAGES[lang]

        update_db_status(uid, "reject")
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=t['rej_msg'].format(admin=ADMIN_USERNAME),
                parse_mode="HTML"
            )
        except Exception:
            pass
        await query.edit_message_text(query.message.text_html + "\n\n🗑️ <b>STATUS: REJECTED & REMOVED FROM DB</b>", parse_mode="HTML")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user):
        return ConversationHandler.END
    await query.answer()
    await query.edit_message_text("📢 <b>Send the message you want to broadcast to all members</b> (or /cancel):", parse_mode="HTML")
    return BROADCAST_MSG

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB_NAME) as conn:
        users = conn.execute("SELECT user_id FROM members").fetchall()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u[0],
                text=f"📢 <b>ASTU CLUB ANNOUNCEMENT</b>\n━━━━━━━━━━━━━━━━━━━━\n{html.escape(update.message.text)}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast delivered to <code>{sent}</code> members! /admin", parse_mode="HTML")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'en')
    await update.message.reply_text(LANGUAGES[lang]['cancelled'], reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    # Global Admin & QR Callbacks
    app.add_handler(CommandHandler('admin', admin_cmd))
    app.add_handler(CallbackQueryHandler(send_qr_card, pattern='^get_my_qr$'))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern='^(open_admin|adm_export|adm_list|adm_app_|adm_rej_)'))

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

    print("🚀 ASTU Bot V2 Running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    keep_alive()
    main()
