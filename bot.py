import sys
import os

# Windows cp1252 / Unicode Fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import sqlite3
import re
import datetime
import logging
import asyncio
import time
import io
try:
    import openpyxl
    EXCEL_SUPPORTED = True
except ImportError:
    EXCEL_SUPPORTED = False
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Bot, CopyTextButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ═══════════════════════════════════════════════
#              ⚙️  CONFIGURATION
# ═══════════════════════════════════════════════
DB_NAME = 'otp_bot.db'

# বটের টোকেনসমূহ
BOT_TOKEN = "8920102269:AAFMCsOM9iBJx0lZMmlS-_nR6sqdyl3-MFs"
FORWARDER_BOT_TOKEN = "8777573519:AAFpMkzgcb_IJR2K3EzmeYUXlxo1UP1iNis" # @mrprinceotps_bot (Admin in group)

ADMIN_ID = 8828657233

# গ্রুপ ও বাটন কনফিগারেশন
MY_OTP_GROUP_URL = "https://t.me/+9svajLMOCMdhZTNl"
GET_NUMBER_URL = "https://t.me/mrprinceot2_bot"   # আপনার টেলিগ্রাম নাম্বার বট
CHANNEL_URL = "https://t.me/"                      # চ্যানেল লিংক (বর্তমানে ব্ল্যাঙ্ক)
TARGET_GROUP_ID = -1004360634639      # PRINCE 🤴 OTP 📥 GROUP (যেখানে মেসেজ ফরওয়ার্ড হবে)
SOURCE_GROUP_ID = -1003406039344      # SOJIB METHOD WORLD (যেখান থেকে মেসেজ আসবে)

NUMBERS_PER_REQUEST = 4
admin_states = {}
user_states = {}

# ═══════════════════════════════════════════════
#        🌍  COUNTRY CODE + FLAG MAP
# ═══════════════════════════════════════════════
COUNTRY_DATA = {
    "sudan 2":     {"flag": "🇸🇩", "code": "+249", "short": "SD", "name": "SUDAN 2"},
    "sudan":       {"flag": "🇸🇩", "code": "+249", "short": "SD", "name": "SUDAN"},
    "ukraine":     {"flag": "🇺🇦", "code": "+380", "short": "UA", "name": "UKRAINE"},
    "togo":        {"flag": "🇹🇬", "code": "+228", "short": "TG", "name": "TOGO"},
    "mali":        {"flag": "🇲🇱", "code": "+223", "short": "ML", "name": "MALI"},
    "laos":        {"flag": "🇱🇦", "code": "+856", "short": "LA", "name": "LAOS"},
    "syria":       {"flag": "🇸🇾", "code": "+963", "short": "SY", "name": "SYRIA"},
    "venezuela":   {"flag": "🇻🇪", "code": "+58",  "short": "VE", "name": "VENEZUELA"},
    "indonesia":   {"flag": "🇮🇩", "code": "+62",  "short": "ID", "name": "INDONESIA"},
    "nigeria":     {"flag": "🇳🇬", "code": "+234", "short": "NG", "name": "NIGERIA"},
    "bangladesh":  {"flag": "🇧🇩", "code": "+880", "short": "BD", "name": "BANGLADESH"},
    "india":       {"flag": "🇮🇳", "code": "+91",  "short": "IN", "name": "INDIA"},
    "usa":         {"flag": "🇺🇸", "code": "+1",   "short": "US", "name": "USA"},
    "uk":          {"flag": "🇬🇧", "code": "+44",  "short": "GB", "name": "UK"},
    "russia":      {"flag": "🇷🇺", "code": "+7",   "short": "RU", "name": "RUSSIA"},
    "pakistan":    {"flag": "🇵🇰", "code": "+92",  "short": "PK", "name": "PAKISTAN"},
}


def clean_digits(val: str) -> str:
    return re.sub(r'\D', '', str(val))


def get_country_info(raw_name: str):
    clean = raw_name.strip().lower()
    for k, v in COUNTRY_DATA.items():
        if k in clean or v["name"].lower() in clean:
            return v
    return {"flag": "🌐", "code": "", "short": "XX", "name": raw_name.strip().upper()}


def format_number_with_code(raw_number: str, country_name: str) -> str:
    clean_num = clean_digits(raw_number)
    c_info = get_country_info(country_name)
    c_code_digits = clean_digits(c_info["code"])

    if c_code_digits and clean_num.startswith(c_code_digits):
        return f"+{clean_num}"
    elif c_code_digits:
        return f"+{c_code_digits}{clean_num}"
    else:
        return f"+{clean_num}"


# ═══════════════════════════════════════════════
#    🗄️ DATABASE SETUP & AUTO MIGRATION
# ═══════════════════════════════════════════════

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn


def setup_database():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        total_orders INTEGER DEFAULT 0,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_name TEXT,
        number TEXT,
        clean_number TEXT,
        status TEXT DEFAULT 'available',
        used_by INTEGER DEFAULT 0,
        used_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        country_name TEXT,
        number TEXT,
        clean_number TEXT,
        otp_code TEXT DEFAULT '',
        otp_status TEXT DEFAULT 'waiting',
        raw_message TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        received_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS required_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT,
        chat_id TEXT DEFAULT ''
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_verified (
        user_id INTEGER PRIMARY KEY,
        verified_at TEXT
    )''')

    # AUTO-MIGRATION
    c.execute("PRAGMA table_info(numbers)")
    cols = [column[1] for column in c.fetchall()]
    if 'clean_number' not in cols:
        c.execute("ALTER TABLE numbers ADD COLUMN clean_number TEXT")

    c.execute("PRAGMA table_info(orders)")
    cols = [column[1] for column in c.fetchall()]
    if 'clean_number' not in cols:
        c.execute("ALTER TABLE orders ADD COLUMN clean_number TEXT")
    if 'otp_code' not in cols:
        c.execute("ALTER TABLE orders ADD COLUMN otp_code TEXT DEFAULT ''")
    if 'otp_status' not in cols:
        c.execute("ALTER TABLE orders ADD COLUMN otp_status TEXT DEFAULT 'waiting'")
    if 'raw_message' not in cols:
        c.execute("ALTER TABLE orders ADD COLUMN raw_message TEXT DEFAULT ''")
    if 'received_at' not in cols:
        c.execute("ALTER TABLE orders ADD COLUMN received_at TEXT")

    c.execute("UPDATE numbers SET clean_number = REPLACE(REPLACE(number, '+', ''), ' ', '') WHERE clean_number IS NULL OR clean_number = ''")
    c.execute("UPDATE orders SET clean_number = REPLACE(REPLACE(number, '+', ''), ' ', '') WHERE clean_number IS NULL OR clean_number = ''")

    conn.commit()
    conn.close()

setup_database()


def ensure_user(user):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?,?,?)",
              (user.id, user.username or "", user.first_name or "User"))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════
#    📡 GUARANTEED GROUP SENDER (BOTH BOTS + IDS)
# ═══════════════════════════════════════════════

async def send_message_to_target_group(text: str, reply_markup=None):
    bot_forwarder = Bot(token=FORWARDER_BOT_TOKEN) # @mrprinceotps_bot
    bot_main = Bot(token=BOT_TOKEN)

    target_ids = [TARGET_GROUP_ID]
    if str(TARGET_GROUP_ID).startswith("-") and not str(TARGET_GROUP_ID).startswith("-100"):
        try:
            target_ids.append(int(f"-100{str(TARGET_GROUP_ID)[1:]}"))
        except Exception:
            pass

    for group_id in target_ids:
        try:
            await bot_forwarder.send_message(chat_id=group_id, text=text, parse_mode="HTML", reply_markup=reply_markup)
            return True
        except Exception as e1:
            try:
                await bot_main.send_message(chat_id=group_id, text=text, parse_mode="HTML", reply_markup=reply_markup)
                return True
            except Exception as e2:
                print(f"Group send attempt failed for ID {group_id}: {e1} | {e2}")

    return False


# ═══════════════════════════════════════════════
#         🧭 NAVIGATION & KEYBOARDS
# ═══════════════════════════════════════════════

def get_bottom_keyboard():
    keyboard = [
        ["🔥 Get Number", "🐥 Search Serial"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def post_init(application) -> None:
    commands = [
        BotCommand("start", "Start Bot"),
        BotCommand("admin", "Admin Panel"),
    ]
    await application.bot.set_my_commands(commands)


# ═══════════════════════════════════════════════
#    📢 FORCE JOIN SYSTEM (বাধ্যতামূলক চ্যানেল)
# ═══════════════════════════════════════════════

async def check_and_enforce_join(update: Update, context: ContextTypes.DEFAULT_TYPE, user) -> bool:
    """
    ইউজার সকল বাধ্যতামূলক চ্যানেল/গ্রুপে জয়েন করেছে কিনা তা চেক করা।
    জয়েন না করলে জয়েনিং বাটন দেখাবে এবং False রিটার্ন করবে।
    """
    if user.id == ADMIN_ID:
        return True

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, url, chat_id FROM required_channels ORDER BY id ASC")
    channels = c.fetchall()

    if not channels:
        conn.close()
        return True

    # চেক করুন ইউজার আগে অলরেডি ভেরিফাইড কিনা
    c.execute("SELECT user_id FROM user_verified WHERE user_id=?", (user.id,))
    verified = c.fetchone()
    conn.close()

    if verified:
        return True

    buttons = []
    for ch_id, title, url, chat_id in channels:
        buttons.append([InlineKeyboardButton(f"📢 {title} ↗", url=url)])
    buttons.append([InlineKeyboardButton("✅ I Have Joined / Check", callback_data="check_force_join")])

    text = (
        f"👋 Welcome <b>{user.first_name}</b> to <b>PRINCE OTP BOT</b>\n\n"
        f"⚠️ <b>বটটি ব্যবহার করতে এবং নম্বর নিতে নিচের চ্যানেল/গ্রুপগুলোতে অবশ্যই জয়েন করুন:</b>\n\n"
        f"সবগুলোতে জয়েন করার পর নিচের <b>✅ I Have Joined / Check</b> বাটনে ক্লিক করুন।"
    )
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await context.bot.send_message(chat_id=user.id, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    return False


# ═══════════════════════════════════════════════
#            🏠 /start COMMAND
# ═══════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)

    can_proceed = await check_and_enforce_join(update, context, user)
    if not can_proceed:
        return

    welcome_text = (
        f"👋 Welcome <b>{user.first_name}</b> to <b>PRINCE OTP BOT</b>\n\n"
        f"🔥 <i>WhatsApp OTP System Online</i>\n\n"
        f"👇 Click <b>🔥 Get Number</b> below to begin:"
    )

    await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=get_bottom_keyboard())
    await show_country_selection(update, context)


# ═══════════════════════════════════════════════
#       🎲 COUNTRY SELECTION (2-COLUMN GRID)
# ═══════════════════════════════════════════════

async def show_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        can_proceed = await check_and_enforce_join(update, context, user)
        if not can_proceed:
            return

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT country_name FROM numbers WHERE status='available' ORDER BY country_name")
    countries = c.fetchall()

    if not countries:
        c.execute("SELECT name FROM countries ORDER BY name")
        countries = c.fetchall()

    buttons = []
    row = []

    for (c_name,) in countries:
        c.execute("SELECT COUNT(*) FROM numbers WHERE country_name=? AND status='available'", (c_name,))
        count = c.fetchone()[0]
        info = get_country_info(c_name)
        
        label = f"{info['flag']} {info['name']} ({info['short']}) ({count})"
        row.append(InlineKeyboardButton(label, callback_data=f"sel_c_{c_name.strip()}"))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="btn_back")])
    conn.close()

    text = "🌐 <b>Select Country for 💬 WHATSAPP :</b>"

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await context.bot.send_message(chat_id=user.id, text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


# ═══════════════════════════════════════════════
#       💎 NUMBER ASSIGNMENT
# ═══════════════════════════════════════════════

async def assign_numbers_and_show(query, country_name: str, user):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT id, number FROM numbers WHERE country_name=? AND status='available' ORDER BY RANDOM() LIMIT ?",
              (country_name, NUMBERS_PER_REQUEST))
    rows = c.fetchall()

    if not rows:
        conn.close()
        info = get_country_info(country_name)
        text = (
            f"❌ <b>{info['flag']} {info['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>⚠️ এই মুহূর্তে কোনো নম্বর খালি নেই। অন্য কোনো দেশ নির্বাচন করুন।</i>"
        )
        kb = [
            [InlineKeyboardButton("🔄 Try Again", callback_data=f"sel_c_{country_name}")],
            [InlineKeyboardButton("🌐 Change Country", callback_data="btn_back")]
        ]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info = get_country_info(country_name)
    buttons = []

    for idx, row in enumerate(rows, 1):
        num_id, raw_num = row
        formatted = format_number_with_code(raw_num, country_name)
        clean_full = clean_digits(formatted)

        c.execute("UPDATE numbers SET status='used', used_by=?, used_at=? WHERE id=?",
                  (user.id, now, num_id))

        c.execute("INSERT INTO orders (user_id, country_name, number, clean_number) VALUES (?,?,?,?)",
                  (user.id, country_name, formatted, clean_full))

        # ১-ক্লিকেই সরাসরি ক্লিপবোর্ডে কপি করার জন্য CopyTextButton
        btn_label = f"📋 {formatted}"
        buttons.append([InlineKeyboardButton(btn_label, copy_text=CopyTextButton(text=formatted))])

    c.execute("UPDATE users SET total_orders = total_orders + ? WHERE user_id=?", (len(rows), user.id))
    conn.commit()
    conn.close()

    buttons.append([InlineKeyboardButton("🔄 Change Number", callback_data=f"sel_c_{country_name}")])
    buttons.append([InlineKeyboardButton("🌐 Change Country", callback_data="btn_back")])
    buttons.append([InlineKeyboardButton("📨 OTP Group ↗", url=MY_OTP_GROUP_URL)])

    header_text = (
        f"✨ <b>{info['flag']} {info['name']} • N U M B E R S</b> ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>Click any number below to <b>Copy Instantly</b>:</i>"
    )

    await query.edit_message_text(header_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


# ═══════════════════════════════════════════════
#    📢 AUTO ANNOUNCE STOCK & HIGH TRAFFIC ALERTS
# ═══════════════════════════════════════════════

async def announce_new_stock(context: ContextTypes.DEFAULT_TYPE, country_name: str, added_count: int) -> int:
    """নতুন নম্বর অ্যাড হলে স্বয়ংক্রিয়ভাবে ওটিপি গ্রুপ এবং সকল ইউজারের বটে নোটিফিকেশন পাঠানো"""
    info = get_country_info(country_name)
    announce_msg = (
        f"🎉 <b>New Stock Added</b>\n\n"
        f"<b>Service:</b> WhatsApp\n"
        f"<b>Country:</b> {info['flag']} {country_name} 🥵 - 💠\n"
        f"<b>Capacity:</b> {added_count}\n\n"
        f"All Numbers are New and Fresh.\n"
        f"New Numbers Available!\n"
        f"Use /start to get your numbers!"
    )

    # ১. টার্গেট ওটিপি গ্রুপে পাঠানো
    await send_message_to_target_group(announce_msg)

    # ২. সমস্ত ইউজারের বটের ইনবক্সে অটো ব্রডকাস্ট করা
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    sent_count = 0
    for (uid,) in users:
        try:
            await context.bot.send_message(chat_id=uid, text=announce_msg, parse_mode="HTML")
            sent_count += 1
            await asyncio.sleep(0.04)  # ফ্লাড লিমিট প্রতিরোধ
        except Exception:
            pass

    return sent_count


async def announce_high_traffic(context: ContextTypes.DEFAULT_TYPE, country_name: str = "", custom_text: str = None) -> int:
    """অ্যাডমিন প্যানেল থেকে হাই ট্রাফিক অ্যালার্ট সমস্ত ইউজার ও গ্রুপে পাঠানো"""
    if custom_text:
        alert_msg = (
            f"🚨 <b>HIGH TRAFFIC ALERT</b> 🔥\n\n"
            f"📢 <b>Update:</b> {custom_text}\n\n"
            f"⚡ Numbers are online and OTP is working fast!\n"
            f"👉 Use /start to get your numbers now!"
        )
    else:
        info = get_country_info(country_name)
        alert_msg = (
            f"🚨 <b>HIGH TRAFFIC ALERT</b> 🔥\n\n"
            f"<b>Service:</b> WhatsApp\n"
            f"<b>Country:</b> {info['flag']} {country_name} 🥵 - 💠\n"
            f"<b>Status:</b> ⚡ <b>HIGH TRAFFIC & FAST OTP!</b> 🚀\n\n"
            f"All Numbers are Online & Ready.\n"
            f"Grab your numbers fast before stock ends!\n"
            f"👉 Use /start to get your numbers!"
        )

    # ১. টার্গেট ওটিপি গ্রুপে পাঠানো
    await send_message_to_target_group(alert_msg)

    # ২. সমস্ত ইউজারের বটের ইনবক্সে ব্রডকাস্ট করা
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    sent_count = 0
    for (uid,) in users:
        try:
            await context.bot.send_message(chat_id=uid, text=alert_msg, parse_mode="HTML")
            sent_count += 1
            await asyncio.sleep(0.04)  # ফ্লাড লিমিট প্রতিরোধ
        except Exception:
            pass

    return sent_count


# ═══════════════════════════════════════════════
#    📨 GROUP FORWARDER & PARSER
# ═══════════════════════════════════════════════

def parse_otp_details(text: str):
    if not text:
        return [], [], None

    potential_nums = []
    matches = re.findall(r'(?:\+?[\d][\d\s\-]{6,16}[\d])', text)
    for m in matches:
        cd = clean_digits(m)
        if 8 <= len(cd) <= 16:
            potential_nums.append(cd)

    masked_nums = re.findall(r'(\d{4,7})[^\w\d\s]+(\d{3,8})', text)

    otp_code = None
    patterns = [
        r'(?:code|otp|passcode|pin|verification|kod|código|код|key)\s*[:=\-]?\s*([0-9]{3}[-\s][0-9]{3}|[0-9]{3,8})',
        r'([0-9]{3}-[0-9]{3})',
        r'(?:WhatsApp|WA|Telegram)\s*(?:code|otp)?\s*(?:is|:)?\s*([0-9]{3}[-\s][0-9]{3}|[0-9]{3,8})',
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).replace(' ', '')
            cand_clean = clean_digits(candidate)
            if not any(cand_clean == p for p in potential_nums) and (3 <= len(cand_clean) <= 8):
                otp_code = candidate
                break

    if not otp_code and masked_nums:
        otp_code = masked_nums[0][1]

    if not otp_code:
        digits_matches = re.findall(r'\b([0-9]{4,8})\b', text)
        for cand in digits_matches:
            cand_clean = clean_digits(cand)
            if not any(cand_clean == p for p in potential_nums):
                if not any(cand_clean == pre for pre, _ in masked_nums):
                    otp_code = cand
                    break

    return potential_nums, masked_nums, otp_code

def extract_key_from_telegram_message(message):
    if not message or not getattr(message, 'reply_markup', None):
        return None
    try:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if getattr(btn, 'copy_text', None) and btn.copy_text.text:
                    return str(btn.copy_text.text).strip()
                if getattr(btn, 'callback_data', None):
                    return str(btn.callback_data).strip()
    except Exception:
        pass
    return None


async def handle_group_message_relay(context: ContextTypes.DEFAULT_TYPE, message, raw_text: str, source_chat_id: int):
    """
    যে কোনো গ্রুপ বা চ্যানেল থেকে মেসেজ আসার সাথে সাথে:
    ১. 'PRINCE OTP GROUP' তে ইনস্ট্যান্ট সরাসরি পোস্ট হবে।
    ২. ইউজারের একাউন্টের অর্ডারের সাথে ফোন নম্বর মিললে সরাসরি ইউজারের ইনবক্সে OTP নোটিফিকেশন যাবে।
    """
    button_otp = extract_key_from_telegram_message(message)
    found_nums, masked_nums, text_otp = parse_otp_details(raw_text)
    otp_code = button_otp or text_otp or ""

    # ১. প্রাইভেট ওটিপি গ্রুপে (TARGET_GROUP_ID) পোস্ট করা
    if str(source_chat_id) != str(TARGET_GROUP_ID) and str(source_chat_id) != f"-100{abs(TARGET_GROUP_ID)}":
        copy_val = otp_code if otp_code else raw_text
        relay_buttons = [
            [InlineKeyboardButton("🔑 📋 Copy Your Key", copy_text=CopyTextButton(text=copy_val))],
            [
                InlineKeyboardButton("🤖 Get Number ↗", url=GET_NUMBER_URL),
                InlineKeyboardButton("📢 Channel ↗", url=CHANNEL_URL)
            ]
        ]
        await send_message_to_target_group(raw_text, reply_markup=InlineKeyboardMarkup(relay_buttons))

    # ২. ইউজারের চ্যাটে ওটিপি ডেলিভারি
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, user_id, country_name, number, clean_number FROM orders WHERE otp_status='waiting' ORDER BY id DESC")
    waiting_orders = c.fetchall()

    matched_order = None

    # ক. পূর্ণ নম্বর দিয়ে মেলানো
    for clean_num in found_nums:
        tail = clean_num[-8:] if len(clean_num) >= 8 else clean_num
        for order in waiting_orders:
            order_id, u_id, c_name, full_num, order_clean = order
            order_clean = clean_digits(order_clean or full_num)
            if order_clean.endswith(tail) or tail in order_clean:
                matched_order = order
                break
        if matched_order:
            break

    # খ. মাস্কড নম্বর দিয়ে মেলানো (যেমন 24911 বা 85620 এবং 4167)
    if not matched_order and masked_nums:
        for pre, tail in masked_nums:
            for order in waiting_orders:
                order_id, u_id, c_name, full_num, order_clean = order
                order_clean = clean_digits(order_clean or full_num)
                if (order_clean.startswith(pre) or pre in order_clean) and (order_clean.endswith(tail) or tail in order_clean or not tail):
                    matched_order = order
                    if not otp_code:
                        otp_code = tail
                    break
            if matched_order:
                break

    # গ. টেক্সটের ভেতরে নম্বরের শেষ ৪-৮ ডিজিট থাকলে মেলানো
    if not matched_order:
        text_clean = clean_digits(raw_text)
        for order in waiting_orders:
            order_id, u_id, c_name, full_num, order_clean = order
            order_clean = clean_digits(order_clean or full_num)
            tail = order_clean[-8:] if len(order_clean) >= 8 else order_clean
            if tail and tail in text_clean:
                matched_order = order
                break

    if matched_order:
        order_id, user_id, country_name, full_num, _ = matched_order
        final_otp = otp_code or "Available"
        now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        c.execute("UPDATE orders SET otp_code=?, otp_status='received', raw_message=?, received_at=? WHERE id=?",
                  (final_otp, raw_text, now, order_id))
        conn.commit()

        user_msg = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  🔔 <b>NEW OTP RECEIVED!</b> 💎\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 Service  : <b>WhatsApp</b>\n"
            f"🌍 Country  : <b>{country_name}</b>\n"
            f"📞 Number   : <code>{full_num}</code>\n\n"
            f"🔑 <b>Your OTP Code:</b>\n"
            f"👉 <code>{final_otp}</code> 👈\n\n"
            f"⏰ Received: <b>{now}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            await context.bot.send_message(user_id, user_msg, parse_mode="HTML")
        except Exception as ex:
            print(f"User OTP delivery error: {ex}")

    conn.close()


# ═══════════════════════════════════════════════
#         ⚙️ ADMIN CONTROL PANEL
# ═══════════════════════════════════════════════

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access Denied.")
        return

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM numbers WHERE status='available'")
    total_stock = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM countries")
    total_countries = c.fetchone()[0]
    conn.close()

    text = (
        f"<b>⚙️ Admin Control Panel</b>\n\n"
        f"👥 Total Users : <b>{total_users}</b>\n"
        f"🌍 Countries   : <b>{total_countries}</b>\n"
        f"📱 Avail Stock : <b>{total_stock}</b> pcs\n\n"
        f"📡 Target Group : <code>{TARGET_GROUP_ID}</code>\n"
        f"📡 Source Group : <code>{SOURCE_GROUP_ID}</code>\n"
    )

    kb = [
        [InlineKeyboardButton("➕ Add Country", callback_data="admin_add_country"),
         InlineKeyboardButton("📱 Add Number (.txt/Text)", callback_data="admin_add_number")],
        [InlineKeyboardButton("📊 View Stock", callback_data="admin_view_stock"),
         InlineKeyboardButton("🗑️ Delete Country", callback_data="admin_del_country")],
        [InlineKeyboardButton("⚡ High Traffic Alert", callback_data="admin_traffic_alert"),
         InlineKeyboardButton("📢 Force Join Groups", callback_data="admin_force_join")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("🧪 Test OTP Push", callback_data="admin_test_otp")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))


# ═══════════════════════════════════════════════
#    🔄 CALLBACK QUERY HANDLER
# ═══════════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    ensure_user(user)
    await query.answer()
    data = query.data

    if data == "check_force_join":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, title, url, chat_id FROM required_channels ORDER BY id ASC")
        channels = c.fetchall()

        not_joined = []
        for ch_id, title, url, chat_id in channels:
            if chat_id:
                try:
                    m = await context.bot.get_chat_member(chat_id=chat_id, user_id=user.id)
                    if m.status in ['left', 'kicked']:
                        not_joined.append((title, url))
                except Exception:
                    pass

        if not_joined:
            conn.close()
            await query.answer("⚠️ আপনি এখনও সব চ্যানেল/গ্রুপে জয়েন করেননি! সবগুলোতে জয়েন করে আবার চেক করুন।", show_alert=True)
            return

        c.execute("INSERT OR REPLACE INTO user_verified (user_id, verified_at) VALUES (?, datetime('now'))", (user_id,))
        conn.commit()
        conn.close()

        await query.answer("✅ ভেরিফিকেশন সফল হয়েছে!", show_alert=False)
        welcome_text = (
            f"👋 Welcome <b>{user.first_name}</b> to <b>PRINCE OTP BOT</b>\n\n"
            f"🔥 <i>WhatsApp OTP System Online</i>\n\n"
            f"👇 Click <b>🔥 Get Number</b> below to begin:"
        )
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(chat_id=user_id, text=welcome_text, parse_mode="HTML", reply_markup=get_bottom_keyboard())
        await show_country_selection(update, context)
        return

    if data == "get_number" or data == "btn_back":
        await show_country_selection(update, context)
        return

    if data.startswith("sel_c_"):
        country_name = data.replace("sel_c_", "")
        await assign_numbers_and_show(query, country_name, user)
        return

    if data.startswith("copy_"):
        await query.answer("📋 Number copied to clipboard!", show_alert=False)
        return

    if data == "copy_key":
        await query.answer("🔑 Key copied!", show_alert=False)
        return

    # Admin options
    if user_id != ADMIN_ID:
        return

    if data == "admin_add_country":
        admin_states[user_id] = {'action': 'waiting_for_country'}
        await query.message.reply_text("📝 নতুন দেশের নাম লিখুন (যেমন: Sudan 2, Togo, Ukraine):")
        return

    if data == "admin_add_number":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM countries ORDER BY name")
        countries = c.fetchall()
        conn.close()

        if not countries:
            await query.message.reply_text("❌ আগে Add Country দিয়ে দেশ যুক্ত করুন।")
            return

        buttons = [[InlineKeyboardButton(c[0], callback_data=f"add_n_to_{c[0]}")] for c in countries]
        await query.edit_message_text("📱 কোন দেশের জন্য নম্বর যুক্ত করবেন?", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("add_n_to_"):
        country = data.replace("add_n_to_", "")
        info = get_country_info(country)
        admin_states[user_id] = {'action': 'waiting_for_numbers', 'country': country}
        await query.message.reply_text(
            f"📁 <b>{info['flag']} {country} 에르 저 님버 아팼로드 하다를:</b>\n\n"
            f"✅ <b>저 포르매트에 파트 핥할:</b>\n"
            f"• 📄 <b>.txt 파일</b> — 하나도 하는니와 하나 님버\n"
            f"• 📊 <b>.xlsx / .xls 파일</b> — ivasms Excel 시트 사단 니와 안다를\n"
            f"• 📋 <b>.csv 파일</b> — 코마 모다 뉴라인 세파레이트드\n"
            f"• ✏️ <b>사단를 타이플 하다를</b> — 하나도 하는니와 하나 님버 페스트 하다를\n\n"
            f"⚡ <i>바트 스톤자동으로 사드 코맼 스캔 하여 포름 님버 설치는 모다 도플리케이트 뮣 하는니와 스통하는 기준시트 프레시 님버 실해하보사.</i>",
            parse_mode="HTML"
        )
        return

    if data == "admin_view_stock":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT country_name, COUNT(*) FROM numbers WHERE status='available' GROUP BY country_name")
        stocks = c.fetchall()
        conn.close()

        msg = "<b>📊 Current Stock Report:</b>\n\n"
        if stocks:
            for country, count in stocks:
                info = get_country_info(country)
                msg += f"{info['flag']} {country}: <b>{count}</b> pcs available\n"
        else:
            msg += "স্টকে কোনো নম্বর নেই।"
        await query.message.reply_text(msg, parse_mode="HTML")
        return

    if data == "admin_del_country":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM countries ORDER BY name")
        countries = c.fetchall()
        conn.close()

        if not countries:
            await query.message.reply_text("কোনো দেশ নেই।")
            return

        buttons = [[InlineKeyboardButton(f"❌ {c[0]}", callback_data=f"del_c_{c[0]}")] for c in countries]
        await query.edit_message_text("🗑️ ডিলিট করতে ক্লিক করুন:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("del_c_"):
        country = data.replace("del_c_", "")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM countries WHERE name=?", (country,))
        c.execute("DELETE FROM numbers WHERE country_name=?", (country,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"✅ {country} এবং এর সকল নম্বর ডিলিট করা হয়েছে।")
        return

    if data == "admin_test_otp":
        admin_states[user_id] = {'action': 'waiting_for_test_otp'}
        await query.message.reply_text("🧪 টেস্ট মেসেজ দিন (যেমন: WhatsApp code 123-456 for +249128890706):")
        return

    if data == "admin_traffic_alert":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM countries ORDER BY name")
        countries = c.fetchall()
        conn.close()

        buttons = []
        for c_row in countries:
            info = get_country_info(c_row[0])
            buttons.append([InlineKeyboardButton(f"⚡ {info['flag']} {c_row[0]} High Traffic", callback_data=f"send_trf_{c_row[0]}")])
        buttons.append([InlineKeyboardButton("✍️ Custom Traffic Alert (Type Text)", callback_data="custom_trf_alert")])
        buttons.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel_back")])

        text = "🚦 <b>High Traffic Alert Panel</b>\n\nযে দেশের জন্য হাই ট্রাফিক নোটিফিকেশন পাঠাতে চান তা বেছে নিন অথবা কাস্টম মেসেজ লিখতে নিচের বাটনে চাপ দিন:"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("send_trf_"):
        country = data.replace("send_trf_", "")
        await query.edit_message_text(f"⏳ <b>{country}</b> এর হাই ট্রাফিক অ্যালার্ট পাঠানো হচ্ছে...", parse_mode="HTML")
        sent = await announce_high_traffic(context, country_name=country)
        await query.message.reply_text(f"✅ <b>{country}</b> এর হাই ট্রাফিক অ্যালার্ট {sent} জন ইউজারের ইনবক্সে এবং ওটিপি গ্রুপে সফলভাবে পাঠানো হয়েছে!", parse_mode="HTML")
        return

    if data == "custom_trf_alert":
        admin_states[user_id] = {'action': 'waiting_for_custom_traffic'}
        await query.message.reply_text(
            "✍️ <b>কাস্টম ট্রাফিক মেসেজ লিখুন:</b>\n\n"
            "যেমন: <i>সুদান হাই ট্রাফিক ওটিপি ফাস্ট আসতেছে</i>\n"
            "মেসেজটি লিখে সেন্ড করলেই সকল ইউজার ও গ্রুপে চলে যাবে।",
            parse_mode="HTML"
        )
        return

    if data == "admin_force_join":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM required_channels")
        total_ch = c.fetchone()[0]
        conn.close()

        buttons = [
            [InlineKeyboardButton("➕ Add Channel / Group", callback_data="admin_add_fjoin")],
            [InlineKeyboardButton("📋 View All Channels", callback_data="admin_list_fjoin"),
             InlineKeyboardButton("🗑️ Delete Channel", callback_data="admin_del_fjoin")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel_back")]
        ]
        text = (
            f"📢 <b>Force Join Management (বাধ্যতামূলক গ্রুপ/চ্যানেল)</b>\n\n"
            f"বর্তমানে মোট <b>{total_ch}</b> টি চ্যানেল/গ্রুপ ফোর্স জয়েন লিস্টে সেট করা আছে।\n\n"
            f"ইউজাররা বট থেকে নম্বর নেওয়ার পূর্বে এই গ্রুপগুলোতে জয়েন করতে বাধ্য থাকবে।"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data == "admin_add_fjoin":
        admin_states[user_id] = {'action': 'waiting_for_add_channel'}
        text = (
            "📝 <b>নতুন চ্যানেল বা গ্রুপ যুক্ত করুন:</b>\n\n"
            "নিচের ফরম্যাটে মেসেজ লিখে পাঠান:\n"
            "<code>চ্যানেলের নাম | ইনভাইট লিংক</code>\n\n"
            "উদাহরণ:\n"
            "<code>PRINCE OTP GROUP | https://t.me/+9svajLMOCMdhZTNl</code>"
        )
        await query.message.reply_text(text, parse_mode="HTML")
        return

    if data == "admin_list_fjoin":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, title, url FROM required_channels ORDER BY id ASC")
        channels = c.fetchall()
        conn.close()

        if not channels:
            msg = "📢 ফোর্স জয়েন লিস্টে বর্তমানে কোনো চ্যানেল বা গ্রুপ নেই।"
        else:
            msg = "<b>📢 Force Join Channels & Groups List:</b>\n\n"
            for ch_id, title, url in channels:
                msg += f"🔹 <b>{title}</b>\n🔗 <code>{url}</code>\n\n"

        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="admin_force_join")]]
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data == "admin_del_fjoin":
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, title FROM required_channels ORDER BY id ASC")
        channels = c.fetchall()
        conn.close()

        if not channels:
            await query.message.reply_text("কোনো চ্যানেল নেই।")
            return

        buttons = [[InlineKeyboardButton(f"❌ {title}", callback_data=f"del_fjoin_{ch_id}")] for ch_id, title in channels]
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_force_join")])
        await query.edit_message_text("🗑️ ডিলিট করতে চ্যানেলের নামের উপর ক্লিক করুন:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("del_fjoin_"):
        ch_id = int(data.replace("del_fjoin_", ""))
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM required_channels WHERE id=?", (ch_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text("✅ চ্যানেলটি ফোর্স জয়েন লিস্ট থেকে মুছে ফেলা হয়েছে।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_force_join")]]))
        return

    if data == "admin_panel_back":
        await admin_panel(update, context)
        return

    if data == "admin_broadcast":
        admin_states[user_id] = {'action': 'waiting_for_broadcast'}
        await query.message.reply_text("📢 সকল ইউজারকে পাঠানোর টেক্সট লিখুন:")
        return


# ═══════════════════════════════════════════════
#   📝 MESSAGE & FILE HANDLER
# ═══════════════════════════════════════════════

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    text = update.message.text or ""
    ensure_user(user)

    if text == "🔥 Get Number":
        await show_country_selection(update, context)
        return

    elif text == "🐥 Search Serial":
        user_states[user_id] = "waiting_for_serial"
        await update.message.reply_text(
            "🔍 <b>Search Serial / Number:</b>\n"
            "আপনার সিরিয়াল নম্বর বা ফোন নম্বর লিখে সেন্ড করুন:",
            parse_mode="HTML"
        )
        return

    if user_id in user_states and user_states[user_id] == "waiting_for_serial":
        clean_search = clean_digits(text)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT country_name, number, otp_status, otp_code, created_at 
            FROM orders 
            WHERE user_id=? AND (clean_number LIKE ? OR number LIKE ?)
            ORDER BY id DESC LIMIT 5
        """, (user_id, f"%{clean_search}%", f"%{text}%"))
        orders = c.fetchall()
        conn.close()

        if orders:
            msg = "<b>🔍 Search Results:</b>\n\n"
            for country_name, number, otp_status, otp_code, created_at in orders:
                status_icon = "⏳" if otp_status == "waiting" else "✅"
                code_text = f"<code>{otp_code}</code>" if otp_code else "Waiting..."
                msg += (
                    f"🌍 {country_name}\n"
                    f"📞 <code>{number}</code>\n"
                    f"{status_icon} OTP: {code_text}\n"
                    f"🕐 {created_at}\n\n"
                )
            await update.message.reply_text(msg, parse_mode="HTML")
        else:
            await update.message.reply_text("❌ কোনো তথ্য পাওয়া যায়নি।")
        del user_states[user_id]
        return

    # Admin workflows
    if user_id in admin_states:
        state = admin_states[user_id]

        if state['action'] == 'waiting_for_country' and text:
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO countries (name) VALUES (?)", (text.strip(),))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"✅ দেশ <b>{text.strip()}</b> সফলভাবে যুক্ত হয়েছে!", parse_mode="HTML")
            except sqlite3.IntegrityError:
                await update.message.reply_text("⚠️ এই দেশ আগেই যুক্ত আছে।")
            del admin_states[user_id]
            return

        if state['action'] == 'waiting_for_add_channel' and text:
            parts = text.split("|")
            if len(parts) >= 2:
                title = parts[0].strip()
                url = parts[1].strip()
                chat_id = ""
                m_uname = re.search(r't\.me/([a-zA-Z0-9_]+)$', url)
                if m_uname and not url.startswith("https://t.me/+"):
                    chat_id = f"@{m_uname.group(1)}"

                conn = get_db_connection()
                c = conn.cursor()
                c.execute("INSERT INTO required_channels (title, url, chat_id) VALUES (?, ?, ?)", (title, url, chat_id))
                conn.commit()
                conn.close()

                await update.message.reply_text(f"✅ চ্যানেল <b>{title}</b> সফলভাবে ফোর্স জয়েন লিস্টে যুক্ত হয়েছে!", parse_mode="HTML")
            else:
                await update.message.reply_text("⚠️ ফরম্যাট সঠিক হয়নি! <code>নাম | লিংক</code> ফরম্যাটে লিখুন।", parse_mode="HTML")
            del admin_states[user_id]
            return

        if state['action'] == 'waiting_for_numbers':
            country_name = state['country']
            numbers_list = []

            status_msg = await update.message.reply_text("⏳ <i>ফাইল স্ক্যান করা হচ্ছে এবং ফ্রেশ নম্বর ফিল্টার করা হচ্ছে...</i>", parse_mode="HTML")

            try:
                if update.message.document:
                    file = await context.bot.get_file(update.message.document.file_id)
                    file_bytes = await file.download_as_bytearray()
                    file_name = (update.message.document.file_name or "").lower()

                    # Excel ফাইল (.xlsx / .xls)
                    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
                        if not EXCEL_SUPPORTED:
                            await status_msg.edit_text("⚠️ Excel সাপোর্টের জন্য openpyxl ইনস্টল করুন: pip install openpyxl")
                            return
                        import io as _io
                        wb = openpyxl.load_workbook(_io.BytesIO(bytes(file_bytes)), data_only=True)
                        for sheet in wb.worksheets:
                            for row in sheet.iter_rows(values_only=True):
                                for cell in row:
                                    val = str(cell).strip() if cell is not None else ""
                                    if re.search(r"\d{6,15}", val):
                                        numbers_list.append(val)

                    # CSV ফাইল
                    elif file_name.endswith(".csv"):
                        try:
                            file_text = bytes(file_bytes).decode("utf-8")
                        except Exception:
                            file_text = bytes(file_bytes).decode("latin-1", errors="ignore")
                        import csv, io as _io2
                        reader = csv.reader(_io2.StringIO(file_text))
                        for row in reader:
                            for cell in row:
                                cell = cell.strip()
                                if re.search(r"\d{6,15}", cell):
                                    numbers_list.append(cell)

                    # TXT ফাইল বা অন্যান্য
                    else:
                        try:
                            file_text = bytes(file_bytes).decode("utf-8")
                        except Exception:
                            file_text = bytes(file_bytes).decode("latin-1", errors="ignore")
                        numbers_list = [n.strip() for n in file_text.splitlines() if n.strip()]

                elif text:
                    numbers_list = [n.strip() for n in text.splitlines() if n.strip()]
            except Exception as ex:
                await status_msg.edit_text(f"⚠️ ফাইল পড়তে সমস্যা হয়েছে: {ex}")
                return

            if not numbers_list:
                await status_msg.edit_text("⚠️ ফাইলে বা মেসেজে কোনো নম্বর পাওয়া যায়নি।")
                del admin_states[user_id]
                return

            conn = get_db_connection()
            c = conn.cursor()
            added = 0
            skipped = 0
            seen_in_batch = set()

            for num in numbers_list:
                clean = clean_digits(num)
                if not clean or len(clean) < 6:
                    skipped += 1
                    continue
                formatted = format_number_with_code(clean, country_name)
                clean_full = clean_digits(formatted)

                if clean_full in seen_in_batch:
                    skipped += 1
                    continue
                seen_in_batch.add(clean_full)

                # চেক করা নম্বরটি আগে থেকে numbers টেবিলে আছে কিনা
                c.execute("SELECT id FROM numbers WHERE clean_number=?", (clean_full,))
                if c.fetchone():
                    skipped += 1
                    continue

                # চেক করা নম্বরটি পূর্বে ব্যবহৃত orders টেবিলে আছে কিনা
                c.execute("SELECT id FROM orders WHERE clean_number=?", (clean_full,))
                if c.fetchone():
                    skipped += 1
                    continue

                c.execute("INSERT INTO numbers (country_name, number, clean_number) VALUES (?, ?, ?)",
                          (country_name, formatted, clean_full))
                added += 1

            conn.commit()
            conn.close()

            info = get_country_info(country_name)
            sent_users = 0
            if added > 0:
                sent_users = await announce_new_stock(context, country_name, added)

            res_text = (
                f"✅ <b>স্ক্যানিং ও আপলোড সম্পন্ন!</b>\n\n"
                f"🌍 দেশ: <b>{info['flag']} {country_name}</b>\n"
                f"📊 মোট স্ক্যানকৃত: <b>{len(numbers_list)}</b> টি\n"
                f"✨ ফ্রেশ নম্বর যোগ হয়েছে: <b>{added}</b> টি\n"
                f"⚠️ বাদ দেওয়া হয়েছে: <b>{skipped}</b> টি (ডুপ্লিকেট / পূর্বে ব্যবহৃত / অকার্যকর)\n\n"
                f"📢 <b>{sent_users}</b> জন ইউজারের ইনবক্সে এবং ওটিপি গ্রুপে অটো স্টক অ্যানাউন্সমেন্ট পাঠানো হয়েছে।"
            )
            await status_msg.edit_text(res_text, parse_mode="HTML")
            del admin_states[user_id]
            return

        if state['action'] == 'waiting_for_custom_traffic' and text:
            sent_users = await announce_high_traffic(context, custom_text=text)
            await update.message.reply_text(
                f"✅ কাস্টম ট্রাফিক অ্যালার্ট <b>{sent_users}</b> জন ইউজারের ইনবক্সে এবং ওটিপি গ্রুপে সফলভাবে পাঠানো হয়েছে!",
                parse_mode="HTML"
            )
            del admin_states[user_id]
            return

        if state['action'] == 'waiting_for_test_otp' and text:
            await handle_group_message_relay(context, update.message, text, source_chat_id=user_id)
            await update.message.reply_text("🧪 টেস্ট ওটিপি প্রসেস এবং ফরওয়ার্ড করা হয়েছে।")
            del admin_states[user_id]
            return

        if state['action'] == 'waiting_for_broadcast' and text:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT user_id FROM users")
            users = c.fetchall()
            conn.close()

            count = 0
            for (uid,) in users:
                try:
                    await context.bot.send_message(uid, text, parse_mode="HTML")
                    count += 1
                except Exception:
                    pass

            await update.message.reply_text(f"📢 {count} জন ইউজারের কাছে ব্রডকাস্ট পাঠানো হয়েছে।")
            del admin_states[user_id]
            return


# ═══════════════════════════════════════════════
#   👥 GROUP LISTENER
# ═══════════════════════════════════════════════

async def group_listener(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    raw_text = message.text or message.caption or ""
    chat_id = update.effective_chat.id
    if raw_text:
        await handle_group_message_relay(context, message, raw_text, source_chat_id=chat_id)


# ═══════════════════════════════════════════════
#           🚀 MAIN FUNCTION
# ═══════════════════════════════════════════════

def main():
    while True:
        try:
            app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("admin", admin_panel))
            app.add_handler(CallbackQueryHandler(callback_handler))

            # যেকোনো গ্রুপ বা চ্যানেল থেকে রিসিভ হওয়া সব টাইপের বার্তা স্ক্যান
            app.add_handler(MessageHandler(
                filters.ALL & ~filters.COMMAND & ~filters.ChatType.PRIVATE,
                group_listener
            ))

            # ইনবক্স চ্যাট হ্যান্ডলার
            app.add_handler(MessageHandler(
                filters.ChatType.PRIVATE & (filters.TEXT | filters.Document.ALL) & ~filters.COMMAND,
                text_handler
            ))

            print("================================")
            print("  PRINCE OTP BOT is running...")
            print("================================")

            app.run_polling(drop_pending_updates=True, close_loop=False)
            break
        except (KeyboardInterrupt, SystemExit):
            print("🛑 Bot stopped by user.")
            break
        except Exception as e:
            err_str = str(e)
            if "Conflict" in err_str or "terminated by other getUpdates request" in err_str:
                print("\n" + "="*65)
                print("⚠️ [CONFLICT DETECTED] অন্য কোনো পিসি বা টার্মিনালে এই বটটি চালু আছে!")
                print("👉 টেলিগ্রামের নিয়ম অনুযায়ী একটি বট টোকেন দিয়ে একই সাথে ২ জায়গায়")
                print("   বট চালু রাখা যায় না। আপনার আগের বটটি (যেমন লোকাল পিসিতে) বন্ধ করুন।")
                print("⏳ ১০ সেকেন্ড পর অটোমেটিক আবার কানেক্ট করার চেষ্টা করা হচ্ছে...")
                print("="*65 + "\n")
                time.sleep(10)
            else:
                print(f"⚠️ [BOT ERROR] {e}")
                time.sleep(5)


if __name__ == '__main__':
    main()
