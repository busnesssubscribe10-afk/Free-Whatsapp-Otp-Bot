"""
════════════════════════════════════════════════════════════════════════════════
         📲 IVASMS.COM → PRINCE OTP BOT LIVE FETCHER (ivasms_fetcher.py)
════════════════════════════════════════════════════════════════════════════════
এই স্ক্রিপ্টটি ivasms.com এর লাইভ SMS Test History পেইজ থেকে প্রতি ৩ সেকেন্ড পর পর
নতুন ওটিপি মেসেজ স্ক্যান করবে। শুধুমাত্র আপনার বটের ডাটাবেসে স্টক থাকা নম্বরের
ওটিপিই আপনার গ্রুপে এবং ইউজারের ইনবক্সে পাঠাবে।
"""

import sys
import os

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
import time

try:
    from curl_cffi import requests as cf_requests
except ImportError:
    print("❌ curl_cffi ইনস্টল নেই! চালান: pip install curl_cffi")
    sys.exit(1)

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton

# ═══════════════════════════════════════════════
#              ⚙️ CONFIGURATION
# ═══════════════════════════════════════════════

# ── ivasms.com সেশন কনফিগ ──────────────────────────────────────────────────
# ⚠️ নিচে আপনার ব্রাউজারের সেশন কুকিগুলো বসান
# (কিভাবে বের করবেন তা IVASMS_GUIDE.txt ফাইলে দেখুন)

IVASMS_SESSION      = "eyJpdiI6Im5pcEI5SGRaaE5nRHRDTTltRmVVbVE9PSIsInZhbHVlIjoiODRFcHlqQ0ZqMlQvZkZCWVFNeE9xVTU1Zi9BOVVBQTZvUThGN2IyVXF3bWZaUEhFbW9tWjV3SDN5VFVlNzU3M3ZwbGJtRGRhU2xsTUozTE1DaXVlRncvRE5xOTJWODEwOUlkUUNEeHNkcEJERkZOVnJyYmlYK2lNR0JmSllwUmQiLCJtYWMiOiI0NmQ2YTJmZWFhZTUxNzViYzI4MmI0NjkyYWJiZWFkYzExMjNmYTMxODUzYWYzNGQ4NTUwOGIzYTBhZWIwZDM3IiwidGFnIjoiIn0%3D"
IVASMS_XSRF_TOKEN   = "eyJpdiI6InFRVURrN2MyQmpHWjVxRXhqN0R5RGc9PSIsInZhbHVlIjoiTWtGek9oT2hyaUcvaUlYYUtESkV1MzlOM0h4ZVc1OWtEUUlnbmhuTkJHU290bFVMdGREbGdGa3ZiVkZ1V0psL0ZadXNJZkNYSW0rNmQ3cDdSam1YT1VFVjRlY3NMQkxudWNmS0U1SFVJZnRHU3lKbnJNYmtrbFBMY05ZYTdLcXUiLCJtYWMiOiIzYmUwZjdiOTI5NzQ3ZjI0ZjFmMTEzZjc4YTE1ZWIyNjQ3NmU2MDViODZmNDJiM2ZlZjVkMWVkYTc5OTcyZmUwIiwidGFnIjoiIn0%3D"
IVASMS_CF_CLEARANCE = "OEKxyz6OkMHFlFcEiohNEkWRiRWJv39fZJhJA2aZwxo-1790414306-1.2.1.1-1hPsYM1dc1spe3yfCOHkY5MJXOSJMn_pd7K6g88SOZtOUuazvZMiOvAVj2l1BFlQyG3qI2ZcFBhuRD4_6k7pxdLfcOhNQRRLe1HluF3iFE19_yLSxrMjVexVDZ3.dWtkjzzREnPszljBK38DImpTl8mFfLIB5LPXvYY1tlJq2Cnc6inhH8V.CxH61F2f8b61KokNkfDb_uvsYDCf8IRvNXGR1NZ0mJp2301ki6BpI3Lobs_DmxxZPxtqnf_VjesMZ5jWFWfTgdL2UwzU.BcOcBj2H8MXP.yj69yZ5PMUmxjcb9E1ZNqIxZu4o2lyTTHNukVkb6iZSB82u7d9CHPHz1OHdLGarT51Kgj5uR4skRDjR14YrK.9flCKW53LOcfOuxDNwues0hb0dhVIFzCPHBE5NOaLzkDoe_M0FlJtNuR7woy7HX8Yoi1dlO42s5a4158z_txpJyUDXWCdGkeShaBwi28cD0UQ7gcEsy7hAkC18yNJUE9uzIZhZSK3XhZYwxwlM6uAKssgzHsNjx4W7Q"

# ── টেলিগ্রাম বট কনফিগ ───────────────────────────────────────────────────
BOT_TOKEN           = "8920102269:AAFMCsOM9iBJx0lZMmlS-_nR6sqdyl3-MFs"
FORWARDER_BOT_TOKEN = "8777573519:AAFpMkzgcb_IJR2K3EzmeYUXlxo1UP1iNis"
TARGET_CHAT_ID      = -1004360634639   # PRINCE 🤴 OTP 📥 GROUP
GET_NUMBER_URL      = "https://t.me/mrprinceot2_bot"
CHANNEL_URL         = "https://t.me/"

DB_NAME             = "otp_bot.db"
FETCH_INTERVAL      = 3   # প্রতি ৩ সেকেন্ডে একবার চেক করবে

# ivasms লাইভ পেইজ URL (কখনো পরিবর্তন হবে না)
IVASMS_URL = "https://www.ivasms.com/portal/sms/test/sms"

# ═══════════════════════════════════════════════
#          🔧 HELPER FUNCTIONS
# ═══════════════════════════════════════════════

def clean_digits(val):
    if not val:
        return ""
    return re.sub(r'\D', '', str(val))


def get_cookies():
    return {
        'ivas_sms_session': IVASMS_SESSION,
        'XSRF-TOKEN': IVASMS_XSRF_TOKEN,
        'cf_clearance': IVASMS_CF_CLEARANCE,
    }


def get_headers():
    return {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'referer': IVASMS_URL,
        'user-agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 9 Pro Fold) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Mobile Safari/537.36',
        'upgrade-insecure-requests': '1',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
    }


def parse_otp_from_text(text):
    """SMS টেক্সট থেকে ওটিপি কোড বের করা"""
    patterns = [
        r'(?:code|otp|passcode|pin|verification|код|código)[\s\:\-=]*([0-9]{3}[-\s][0-9]{3}|[0-9]{4,8})',
        r'([0-9]{3}-[0-9]{3})',
        r'\b([0-9]{4,8})\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).replace('-', '').replace(' ', '')
            if 4 <= len(candidate) <= 8:
                return m.group(1)
    return ""


def fetch_ivasms_rows():
    """ivasms.com পেইজ থেকে HTML ফেচ করে SMS রো পার্স করা"""
    try:
        resp = cf_requests.get(
            IVASMS_URL,
            cookies=get_cookies(),
            headers=get_headers(),
            impersonate="chrome124",
            timeout=15,
        )
        if resp.status_code == 403:
            print(f"[{ts()}] ⚠️ ivasms: সেশন মেয়াদ উত্তীর্ণ (403)! IVASMS_GUIDE.txt দেখে নতুন কুকি আপডেট করুন।")
            return []
        if resp.status_code != 200:
            print(f"[{ts()}] ⚠️ ivasms: HTTP {resp.status_code}")
            return []

        html = resp.text

        # টেবিলের tbody র মধ্যে রো পার্স করা
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
        results = []
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 4:
                clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                # সাধারণত: [Range, TestNumber, SID, Message]
                results.append(clean)
        return results

    except Exception as ex:
        print(f"[{ts()}] ❌ ivasms ফেচ এরর: {ex}")
        return []


def ts():
    return datetime.datetime.now().strftime('%H:%M:%S')


# ═══════════════════════════════════════════════
#     🗄️ DATABASE FUNCTIONS
# ═══════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def find_order_by_number(cursor, raw_number):
    """দেওয়া নম্বরের সাথে ডাটাবেসে ওয়েটিং অর্ডার খোঁজা"""
    search_digits = clean_digits(raw_number)
    if not search_digits or len(search_digits) < 6:
        return None

    # পুরো নম্বর অথবা শেষ ৮ ডিজিট দিয়ে মেলানো
    tail = search_digits[-8:]
    cursor.execute(
        """SELECT id, user_id, country_name, number, clean_number
           FROM orders
           WHERE otp_status='waiting'
           ORDER BY id DESC""",
    )
    orders = cursor.fetchall()
    for order in orders:
        order_clean = clean_digits(order['clean_number'] or order['number'])
        if order_clean.endswith(tail) or tail in order_clean:
            return order
    return None


def mark_otp_received(cursor, order_id, otp_code, raw_message):
    now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    cursor.execute(
        "UPDATE orders SET otp_code=?, otp_status='received', raw_message=?, received_at=? WHERE id=?",
        (otp_code, raw_message, now, order_id),
    )


# ═══════════════════════════════════════════════
#     📨 TELEGRAM SEND FUNCTIONS
# ═══════════════════════════════════════════════

async def send_to_group(number, service, otp_code, raw_message):
    """ওটিপি গ্রুপে সুন্দর ফরম্যাটে মেসেজ পাঠানো"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    text = (
        f"📩 <b>New OTP Received!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 <b>Number:</b> <code>{number}</code>\n"
        f"📱 <b>Service:</b> {service}\n"
        f"🔑 <b>OTP Code:</b> <code>{otp_code}</code>\n"
        f"📝 <b>Message:</b> {raw_message[:200]}\n"
        f"⏰ <b>Time:</b> <b>{now}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔑 📋 Copy OTP", copy_text=CopyTextButton(text=otp_code)),
            InlineKeyboardButton("📋 Copy Number", copy_text=CopyTextButton(text=number)),
        ],
        [
            InlineKeyboardButton("🤖 Get Number ↗", url=GET_NUMBER_URL),
            InlineKeyboardButton("📢 Channel ↗", url=CHANNEL_URL) if CHANNEL_URL.strip('/') != 'https://t.me' else InlineKeyboardButton("📢 Channel ↗", url=GET_NUMBER_URL),
        ],
    ])

    for token in [FORWARDER_BOT_TOKEN, BOT_TOKEN]:
        try:
            bot = Bot(token=token)
            await bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            print(f"[{ts()}] ✅ গ্রুপে পোস্ট সফল: {number} → OTP: {otp_code}")
            return True
        except Exception as e:
            print(f"[{ts()}] ❌ গ্রুপে পোস্ট ব্যর্থ (token={token[:15]}...): {e}")
    return False


async def send_to_user_inbox(user_id, country_name, number, otp_code, received_at):
    """ইউজারের ইনবক্সে সরাসরি ওটিপি নোটিফিকেশন পাঠানো"""
    text = (
        f"✅ <b>আপনার ওটিপি এসে গেছে!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 <b>Country:</b> {country_name}\n"
        f"📞 <b>Number:</b> <code>{number}</code>\n"
        f"🔑 <b>OTP Code:</b> <code>{otp_code}</code>\n"
        f"⏰ <b>Received:</b> <b>{received_at}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 📋 Copy OTP", copy_text=CopyTextButton(text=otp_code))],
    ])

    for token in [BOT_TOKEN, FORWARDER_BOT_TOKEN]:
        try:
            bot = Bot(token=token)
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            print(f"[{ts()}] 🚀 ইউজার {user_id} এর ইনবক্সে OTP ডেলিভারি সফল!")
            return True
        except Exception as e:
            print(f"[{ts()}] ⚠️ ইউজার ইনবক্স সেন্ড ব্যর্থ: {e}")
    return False


# ═══════════════════════════════════════════════
#      🔄 MAIN POLLING LOOP
# ═══════════════════════════════════════════════

# আগে প্রসেস করা মেসেজ ট্র্যাক করার জন্য (ডুপ্লিকেট এড়াতে)
seen_message_ids = set()


async def process_rows(rows):
    """ফেচ করা রো গুলো প্রসেস করা"""
    if not rows:
        return

    conn = get_db()
    c = conn.cursor()

    for cells in rows:
        # cells: [Range/Country, TestNumber, SID/Service, Message, ...]
        try:
            # নম্বর ও মেসেজ এক্সট্র্যাক্ট করা
            test_number = cells[1] if len(cells) > 1 else ""
            service     = cells[2] if len(cells) > 2 else "Unknown"
            raw_message = cells[3] if len(cells) > 3 else ""

            if not test_number or not raw_message:
                continue

            # ডুপ্লিকেট চেক (নম্বর + মেসেজের প্রথম ৩০ অক্ষর দিয়ে ইউনিক আইডি)
            msg_uid = f"{clean_digits(test_number)}_{raw_message[:30]}"
            if msg_uid in seen_message_ids:
                continue
            seen_message_ids.add(msg_uid)

            # সেট বেশি বড় হলে পুরানো এন্ট্রি মুছে ফেলা
            if len(seen_message_ids) > 2000:
                oldest = list(seen_message_ids)[:500]
                for old in oldest:
                    seen_message_ids.discard(old)

            # ডাটাবেসে এই নম্বরের কোনো ওয়েটিং অর্ডার আছে কিনা চেক করা
            order = find_order_by_number(c, test_number)
            if not order:
                # এই নম্বর আমাদের স্টকে নেই, স্কিপ করো
                continue

            # ওটিপি কোড এক্সট্র্যাক্ট করা
            otp_code = parse_otp_from_text(raw_message)
            if not otp_code:
                otp_code = "Check Message"

            print(f"\n[{ts()}] 🎉 OTP MATCHED!")
            print(f"       📞 Number : {test_number}")
            print(f"       📱 Service: {service}")
            print(f"       🔑 OTP    : {otp_code}")
            print(f"       📝 Message: {raw_message[:80]}")

            # ডাটাবেস আপডেট করা
            mark_otp_received(c, order['id'], otp_code, raw_message)
            conn.commit()

            now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

            # ১. গ্রুপে পোস্ট করা
            await send_to_group(test_number, service, otp_code, raw_message)

            # ২. ইউজারের ইনবক্সে পাঠানো
            await send_to_user_inbox(
                order['user_id'], order['country_name'],
                order['number'], otp_code, now
            )

        except Exception as ex:
            print(f"[{ts()}] ❌ রো প্রসেসিং এরর: {ex}")

    conn.close()


async def main_loop():
    print("=" * 60)
    print("  📲 IVASMS OTP FETCHER - PRINCE OTP BOT")
    print("=" * 60)
    print(f"  🌐 Source  : ivasms.com (SMS Test History)")
    print(f"  🎯 Target  : PRINCE 🤴 OTP 📥 GROUP")
    print(f"  🔄 Interval: প্রতি {FETCH_INTERVAL} সেকেন্ডে স্ক্যান")
    print("=" * 60)
    print(f"  ✅ সিস্টেম চালু হয়েছে। লাইভ ওটিপি মনিটরিং শুরু...")
    print("=" * 60 + "\n")

    consecutive_errors = 0

    while True:
        try:
            rows = fetch_ivasms_rows()
            if rows:
                print(f"[{ts()}] 📡 ivasms থেকে {len(rows)} টি SMS রো পাওয়া গেছে। স্ক্যানিং...")
                await process_rows(rows)
            else:
                pass  # নতুন কিছু না থাকলে চুপ থাকো

            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            print(f"[{ts()}] ❌ মেইন লুপ এরর (#{consecutive_errors}): {e}")
            if consecutive_errors >= 5:
                print(f"[{ts()}] ⚠️ ৫ বার ব্যর্থ হয়েছে। ৩০ সেকেন্ড অপেক্ষা করছি...")
                await asyncio.sleep(30)
                consecutive_errors = 0

        await asyncio.sleep(FETCH_INTERVAL)


if __name__ == '__main__':
    asyncio.run(main_loop())
