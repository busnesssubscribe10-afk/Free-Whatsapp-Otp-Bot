"""
════════════════════════════════════════════════════════════════════════════════
             🚀 MASTER RUNNER - PRINCE OTP BOT & FORWARDER
════════════════════════════════════════════════════════════════════════════════
এই স্ক্রিপ্টটি একই সাথে আপনার মেইন টেলিগ্রাম বট (bot.py) এবং ইউজারবট ফরওয়ার্ডার 
(userbot_forwarder.py) দুটোকেই একসাথে স্বয়ংক্রিয়ভাবে চালু রাখবে।
"""

import os
import sys

# Windows cp1252 / Unicode Fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import subprocess
import time
import threading
from telethon.sync import TelegramClient

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_NAME = 'userbot_session'

def check_and_authenticate():
    session_file = f"{SESSION_NAME}.session"
    if not os.path.exists(session_file):
        print("==================================================")
        print("⚠️ প্রথমবার ব্যবহারের জন্য ইউজারবট লগইন প্রয়োজন!")
        print("==================================================")
        print("আপনার টেলিগ্রাম একাউন্টের নম্বর দিন (যেমন: +88017xxxxxxxx)")
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        client.start()
        me = client.get_me()
        print(f"✅ সফলভাবে লগইন সম্পন্ন হয়েছে: {me.first_name}")
        client.disconnect()
        print("==================================================\n")

def stream_output(pipe, prefix):
    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break
            print(f"{prefix} {line.rstrip()}")
    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass

def get_subproc_env():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env

def main():
    check_and_authenticate()

    print("==================================================")
    print("  🚀 STARTING BOTH BOT & USERBOT FORWARDER...")
    print("==================================================")

    env = get_subproc_env()

    # ১. মেইন বট (bot.py) চালু করা
    bot_proc = subprocess.Popen(
        [sys.executable, "-u", "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        env=env
    )

    # ২. ইউজারবট ফরওয়ার্ডার (userbot_forwarder.py) চালু করা
    forwarder_proc = subprocess.Popen(
        [sys.executable, "-u", "userbot_forwarder.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        env=env
    )

    t1 = threading.Thread(target=stream_output, args=(bot_proc.stdout, "[🤖 BOT]"), daemon=True)
    t2 = threading.Thread(target=stream_output, args=(forwarder_proc.stdout, "[⚡ FORWARDER]"), daemon=True)
    t1.start()
    t2.start()

    print("✅ উভয় সিস্টেম সফলভাবে ব্যাকগ্রাউন্ডে চালু হয়েছে!")
    print("💡 বন্ধ করতে কীবোর্ডে Ctrl + C চাপুন।\n")

    try:
        while True:
            ret_bot = bot_proc.poll()
            ret_fwd = forwarder_proc.poll()

            if ret_bot is not None:
                print(f"⚠️ [🤖 BOT] বন্ধ হয়ে গেছে (Exit code: {ret_bot})! রিস্টার্ট করা হচ্ছে...")
                bot_proc = subprocess.Popen(
                    [sys.executable, "-u", "bot.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                    env=env
                )
                threading.Thread(target=stream_output, args=(bot_proc.stdout, "[🤖 BOT]"), daemon=True).start()

            if ret_fwd is not None:
                print(f"⚠️ [⚡ FORWARDER] বন্ধ হয়ে গেছে (Exit code: {ret_fwd})! রিস্টার্ট করা হচ্ছে...")
                forwarder_proc = subprocess.Popen(
                    [sys.executable, "-u", "userbot_forwarder.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace",
                    env=env
                )
                threading.Thread(target=stream_output, args=(forwarder_proc.stdout, "[⚡ FORWARDER]"), daemon=True).start()

            time.sleep(2)
    except KeyboardInterrupt:
        print("\n🛑 সিস্টেম বন্ধ করা হচ্ছে...")
        bot_proc.terminate()
        forwarder_proc.terminate()
        try:
            bot_proc.wait(timeout=3)
            forwarder_proc.wait(timeout=3)
        except Exception:
            bot_proc.kill()
            forwarder_proc.kill()
        print("✅ উভয় সিস্টেম নিরাপদে বন্ধ করা হয়েছে।")

if __name__ == '__main__':
    main()
