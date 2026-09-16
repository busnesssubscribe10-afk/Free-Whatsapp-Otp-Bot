"""
════════════════════════════════════════════════════════════════════════════════
             📲 TELEGRAM GROUP FORWARDER (FORWARDER.PY)
════════════════════════════════════════════════════════════════════════════════
যদি সোর্স গ্রুপে (Sojib Group) টেলিগ্রাম বটে প্রাইভেসি বা কোনো সীমাবদ্ধতা থাকে, 
তবে এই স্ক্রিপ্টটি আপনার নিজের টেলিগ্রাম একাউন্ট বা দ্বিতীয় টোকেন দিয়ে 
মেসেজ লাইভ পড়ে আপনার গ্রুপে ও ডেটাবেসে ফরোয়ার্ড করে দেবে।
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

import sqlite3
import re
import datetime
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

# কনফিগারেশন
BOT_TOKEN = "8777573519:AAFpMkzgcb_IJR2K3EzmeYUXlxo1UP1iNis" # আপনার প্রদানকৃত ২য় টোকেন
TARGET_GROUP_ID = -1004360634639
DB_NAME = 'otp_bot.db'

def clean_digits(val):
    return re.sub(r'\D', '', str(val))

def parse_otp(text):
    if not text:
        return None, None
    num_m = re.search(r'(?:\+?(\d{8,15}))', text)
    found_num = num_m.group(1) if num_m else None
    otp_code = None
    pats = [
        r'(?:code|otp|passcode|pin|verification)\s*(?:is|:|-)?\s*([0-9]{3,8}|[0-9]{3}-[0-9]{3})',
        r'([0-9]{3}-[0-9]{3})',
        r'\b([0-9]{4,8})\b'
    ]
    for p in pats:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            otp_code = m.group(1)
            break
    return found_num, otp_code

async def relay_otp_message(raw_text):
    bot = Bot(token=BOT_TOKEN)
    found_num, otp = parse_otp(raw_text)

    # আপনার গ্রুপে ফরওয়ার্ড
    try:
        copy_val = otp if otp else raw_text
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔑 📄 Copy Your Key", copy_text=CopyTextButton(text=copy_val))]])
        await bot.send_message(chat_id=TARGET_GROUP_ID, text=raw_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Forward error: {e}")

    # ইউজারের ইনবক্সে ডেলিভারি
    if found_num and otp:
        clean = clean_digits(found_num)
        tail = clean[-8:] if len(clean) >= 8 else clean
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, user_id, country_name, number FROM orders WHERE clean_number LIKE ? AND otp_status='waiting' ORDER BY id DESC LIMIT 1", (f"%{tail}",))
        row = c.fetchone()
        if row:
            order_id, user_id, country, full_num = row
            now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            c.execute("UPDATE orders SET otp_code=?, otp_status='received', raw_message=?, received_at=? WHERE id=?", (otp, raw_text, now, order_id))
            conn.commit()
            msg = f"🔔 <b>NEW OTP RECEIVED!</b>\n\n🌍 {country}\n📞 <code>{full_num}</code>\n🔑 OTP: <code>{otp}</code>"
            try:
                await bot.send_message(user_id, msg, parse_mode="HTML")
            except Exception:
                pass
        conn.close()

if __name__ == '__main__':
    print("Forwarder Script ready.")
