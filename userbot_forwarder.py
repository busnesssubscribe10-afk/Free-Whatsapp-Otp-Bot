"""
════════════════════════════════════════════════════════════════════════════════
             📲 TELEGRAM USERBOT OTP FORWARDER (USERBOT_FORWARDER.PY)
════════════════════════════════════════════════════════════════════════════════
এই স্ক্রিপ্টটি আপনার নিজস্ব টেলিগ্রাম একাউন্ট দিয়ে সোর্স চ্যানেল থেকে মেসেজ পড়বে,
স্বয়ংক্রিয়ভাবে আপনার গ্রুপে নতুন মেসেজ আকারে পোস্ট করবে এবং ইউজারের ইনবক্সে ওটিপি পৌঁছে দেবে।
"""

import sys
import os

# Windows cp1252 / Unicode Fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import asyncio
import sqlite3
import re
import datetime
from telethon import TelegramClient, events
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

# ⚙️ কনফিগারেশন (আপনার Telegram API ক্রেডেনশিয়াল)
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

# চ্যাট ও গ্রুপ আইডি
SOURCE_CHAT_ID = -1003406039344     # SOJIB METHOD WORLD (সোর্স চ্যানেল/গ্রুপ)
TARGET_CHAT_ID = -1004360634639     # PRINCE 🤴 OTP 📥 GROUP (টার্গেট গ্রুপ)

# বটের টোকেনসমূহ
BOT_TOKEN = os.environ["BOT_TOKEN"]
FORWARDER_BOT_TOKEN = os.environ["FORWARDER_BOT_TOKEN"]

# বাটন সেটিংস
GET_NUMBER_URL = "https://t.me/mrprinceot2_bot"   # আপনার টেলিগ্রাম নাম্বার বট
CHANNEL_URL = "https://t.me/"                      # চ্যানেল লিংক (বর্তমানে ব্ল্যাঙ্ক রাখা হয়েছে)

DB_NAME = 'otp_bot.db'

def clean_digits(val):
    if not val:
        return ""
    return re.sub(r'\D', '', str(val))

def parse_otp_details(text: str):
    if not text:
        return [], [], None

    # ১. পূর্ণ ফোন নম্বর খোঁজা (৮ থেকে ১৬ ডিজিট)
    potential_nums = []
    matches = re.findall(r'(?:\+?[\d][\d\s\-]{6,16}[\d])', text)
    for m in matches:
        cd = clean_digits(m)
        if 8 <= len(cd) <= 16:
            potential_nums.append(cd)

    # ২. মাস্কড নম্বর খোঁজা (যেমন: 24911❌6514, 85620⏸️4167 -> প্রিফিক্স 24911, ওটিপি 6514)
    masked_nums = re.findall(r'(\d{4,7})[^\w\d\s]+(\d{3,8})', text)

    # ৩. ওটিপি কোড খোঁজা
    otp_code = None

    # অগ্রাধিকার ১: সুনির্দিষ্ট কীওয়ার্ড
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

    # অগ্রাধিকার ২: মাস্কড ফরম্যাট থাকলে ২য় অংশটিই ওটিপি
    if not otp_code and masked_nums:
        otp_code = masked_nums[0][1]

    # অগ্রাধিকার ৩: সাধারণ ৪-৮ ডিজিটের নম্বর
    if not otp_code:
        digits_matches = re.findall(r'\b([0-9]{4,8})\b', text)
        for cand in digits_matches:
            cand_clean = clean_digits(cand)
            if not any(cand_clean == p for p in potential_nums):
                if not any(cand_clean == pre for pre, _ in masked_nums):
                    otp_code = cand
                    break

    return potential_nums, masked_nums, otp_code

def extract_key_from_message(message):
    """
    টেলিগ্রাম সোর্স মেসেজের বাটন (Copy Your Key) থেকে আসল ওটিপি কোডটি উদ্ধার করা
    """
    if not message:
        return None

    # ১. Telethon reply_markup চেক করা
    if hasattr(message, 'reply_markup') and message.reply_markup:
        rows = getattr(message.reply_markup, 'rows', [])
        for row in rows:
            buttons = getattr(row, 'buttons', [])
            for b in buttons:
                b_type = getattr(b, 'type', None)
                if b_type and hasattr(b_type, 'copy_text') and b_type.copy_text:
                    return str(b_type.copy_text).strip()
                if hasattr(b, 'copy_text') and b.copy_text:
                    return str(b.copy_text).strip()
                if hasattr(b, 'data') and b.data:
                    try:
                        return b.data.decode('utf-8', errors='ignore').strip()
                    except Exception:
                        pass

    # ২. Telethon message.buttons চেক করা
    if hasattr(message, 'buttons') and message.buttons:
        for row in message.buttons:
            for b in row:
                if hasattr(b, 'button'):
                    b_inner = b.button
                    b_type = getattr(b_inner, 'type', None)
                    if b_type and hasattr(b_type, 'copy_text') and b_type.copy_text:
                        return str(b_type.copy_text).strip()
                    if hasattr(b_inner, 'copy_text') and b_inner.copy_text:
                        return str(b_inner.copy_text).strip()
                    if hasattr(b_inner, 'data') and b_inner.data:
                        try:
                            return b_inner.data.decode('utf-8', errors='ignore').strip()
                        except Exception:
                            pass
    return None

# টেলিগ্রাম ইউজারবট ক্লায়েন্ট
client = TelegramClient('userbot_session', API_ID, API_HASH)

async def send_to_target_group(raw_text: str, otp_code: str = None):
    """
    টার্গেট গ্রুপে মেসেজ পাঠানো:
    ১. সরাসরি নতুন মেসেজ আকারে পোস্ট করা হবে (সোর্স চ্যানেলের লোগো বা ফরওয়ার্ড হেডার থাকবে না)
    ২. বাটন:
       - Row 1: [🔑 📋 Copy Your Key] (ক্লিক করলেই ওটিপি কপি হয়ে যাবে)
       - Row 2: [🤖 Get Number ↗] (আপনার বট লিংক) | [📢 Channel ↗] (ব্ল্যাঙ্ক চ্যানেল লিংক)
    """
    if not raw_text:
        return False

    # ওটিপি মান নির্ধারণ (বাটন ক্লিপবোর্ডে কপি করার জন্য)
    copy_val = otp_code if otp_code else raw_text

    # বাটন সেটআপ
    buttons = [
        [InlineKeyboardButton("🔑 📋 Copy Your Key", copy_text=CopyTextButton(text=copy_val))],
        [
            InlineKeyboardButton("🤖 Get Number ↗", url=GET_NUMBER_URL),
            InlineKeyboardButton("📢 Channel ↗", url=CHANNEL_URL)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    # মেথড ১: বট দিয়ে সরাসরি টার্গেট গ্রুপে পোস্ট (যাতে অন্য চ্যানেলের কোনো নাম বা লোগো না থাকে)
    for b_token in [FORWARDER_BOT_TOKEN, BOT_TOKEN]:
        try:
            bot = Bot(token=b_token)
            await bot.send_message(chat_id=TARGET_CHAT_ID, text=raw_text, reply_markup=reply_markup)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Target group message sent cleanly via Bot (No source logo)!")
            return True
        except Exception as e_bot:
            print(f"Bot send error: {e_bot}, trying fallback...")

    # মেথড ২: ইউজারবট দিয়ে সরাসরি নতুন মেসেজ সেন্ড (ফরওয়ার্ড ছাড়া)
    try:
        await client.send_message(TARGET_CHAT_ID, raw_text)
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Target group message sent via Userbot!")
        return True
    except Exception as e_ub:
        print(f"Userbot send error: {e_ub}")

    return False

async def send_otp_to_user_inbox(user_id: int, country_name: str, full_num: str, otp_code: str, now: str):
    """ইউজারের ইনবক্সে ওটিপি পাঠানো"""
    user_msg = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🔔 <b>NEW OTP RECEIVED!</b> 💎\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 Service  : <b>WhatsApp</b>\n"
        f"🌍 Country  : <b>{country_name}</b>\n"
        f"📞 Number   : <code>{full_num}</code>\n\n"
        f"🔑 <b>Your OTP Code:</b>\n"
        f"👉 <code>{otp_code}</code> 👈\n\n"
        f"⏰ Received: <b>{now}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    for b_token in [BOT_TOKEN, FORWARDER_BOT_TOKEN]:
        try:
            bot = Bot(token=b_token)
            await bot.send_message(chat_id=user_id, text=user_msg, parse_mode="HTML")
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🚀 OTP delivered to user inbox: {user_id}")
            return True
        except Exception as ex:
            print(f"Error sending OTP to user: {ex}")
    return False

async def process_incoming_otp_message(raw_text: str, found_nums, masked_nums, otp_code):
    """মেসেজ থেকে ওটিপি ও নম্বর চেক করে ডেটাবেস এবং ইউজার আপডেট করা"""
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    c = conn.cursor()

    # বর্তমানে অপেক্ষারত (waiting) সকল অর্ডার সংগ্রহ
    c.execute("SELECT id, user_id, country_name, number, clean_number FROM orders WHERE otp_status='waiting' ORDER BY id DESC")
    waiting_orders = c.fetchall()

    matched_order = None

    # ১. পূর্ণ নম্বর দিয়ে মেলানো
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

    # ২. মাস্কড নম্বর দিয়ে মেলানো (যেমন 24911 বা 85620 এবং 4167)
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

    # ৩. টেক্সটের ভেতরে নম্বরের শেষ ৪-৮ ডিজিট থাকলে মেলানো
    if not matched_order:
        text_clean = clean_digits(raw_text)
        for order in waiting_orders:
            order_id, u_id, c_name, full_num, order_clean = order
            order_clean = clean_digits(order_clean or full_num)
            tail = order_clean[-8:] if len(order_clean) >= 8 else order_clean
            if tail and tail in text_clean:
                matched_order = order
                break

    # যদি অর্ডার মিলে যায়
    if matched_order:
        order_id, user_id, country_name, full_num, _ = matched_order
        final_otp = otp_code or "Available"
        now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        c.execute("UPDATE orders SET otp_code=?, otp_status='received', raw_message=?, received_at=? WHERE id=?",
                  (final_otp, raw_text, now, order_id))
        conn.commit()
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🎉 OTP MATCHED! Order #{order_id} | {full_num} | OTP: {final_otp}")
        
        # ইউজারের ইনবক্সে তাৎক্ষণিক নোটিফিকেশন
        await send_otp_to_user_inbox(user_id, country_name, full_num, final_otp, now)

    conn.close()

@client.on(events.NewMessage)
async def incoming_message_handler(event):
    chat = await event.get_chat()
    chat_id = event.chat_id

    # শুধুমাত্র সোর্স চ্যানেল বা গ্রুপ থেকে আসলে প্রসেস করবে
    valid_source_ids = [
        SOURCE_CHAT_ID,
        int(str(SOURCE_CHAT_ID).replace("-100", "-")),
        abs(SOURCE_CHAT_ID)
    ]

    is_source = (chat_id in valid_source_ids)
    if not is_source and hasattr(chat, 'title') and chat.title:
        title_lower = chat.title.lower()
        if "sojib" in title_lower and ("otp" in title_lower or "world" in title_lower):
            is_source = True

    if not is_source:
        return

    raw_text = event.raw_text or event.message.message or ""
    if not raw_text:
        return

    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 📩 New OTP Message from Source Channel!")
    try:
        print(f"Content: {raw_text[:80]}")
    except Exception:
        pass

    # ১. বাটন থেকে আসল ওটিপি কোড উদ্ধার (যেমন: 4691874)
    button_otp = extract_key_from_message(event.message)

    # ২. টেক্সট থেকে নম্বর ও মাস্কড তথ্য বিশ্লেষণ
    found_nums, masked_nums, text_otp = parse_otp_details(raw_text)

    # চূড়ান্ত ওটিপি নির্ধারণ (বাটন ওটিপি সর্বোচ্চ অগ্রাধিকার পাবে)
    final_otp = button_otp or text_otp or ""

    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🔑 Extracted OTP Key from Message: '{final_otp}'")

    # ৩. টার্গেট গ্রুপে পোস্ট করা (সোর্স লোগো ছাড়া, সঠিক ওটিপি কি ও আপনার বাটন সহ)
    await send_to_target_group(raw_text, otp_code=final_otp)

    # ৪. ওটিপি ম্যাচিং এবং ইউজারের ইনবক্সে ডেলিভারি
    await process_incoming_otp_message(raw_text, found_nums, masked_nums, final_otp)

async def main():
    print("==================================================")
    print("  🚀 STARTING USERBOT OTP FORWARDER SYSTEM")
    print("==================================================")
    
    await client.start()
    
    me = await client.get_me()
    safe_name = me.first_name or "User"
    print(f"✅ Userbot logged in successfully as: {safe_name} (ID: {me.id})")
    print(f"📡 Listening to Source: {SOURCE_CHAT_ID}")
    print(f"🎯 Target Group: {TARGET_CHAT_ID}")
    print("--------------------------------------------------")
    print("⚡ System is active and live-relaying OTPs...")
    print("==================================================")
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
