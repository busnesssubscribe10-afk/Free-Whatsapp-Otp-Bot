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

API_ID = 37558252
API_HASH = "d782da275d3804545c5119341f97d781"
SESSION_NAME = 'userbot_session'

def cleanup_old_instances():
    """অন্য কোনো টার্মিনালে পূর্বে চালু থাকা bot.py বা userbot_forwarder.py থাকলে তা বন্ধ করা"""
    if sys.platform != "win32":
        return
    try:
        curr_pid = os.getpid()
        ps_cmd = (
            f"Get-CimInstance Win32_Process | Where-Object {{ "
            f"($_.CommandLine -like '*bot.py*' -or $_.CommandLine -like '*userbot_forwarder.py*') "
            f"-and $_.ProcessId -ne {curr_pid} }} | ForEach-Object {{ "
            f"Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    except Exception:
        pass

def check_and_authenticate():
    session_file = f"{SESSION_NAME}.session"
    if not os.path.exists(session_file):
        print("==================================================")
        print("⚠️ প্রথমবার ব্যবহারের জন্য ইউজারবট লগইন প্রয়োজন!")
        print("==================================================")
        print("আপনার টেলিগ্রাম একাউন্টের নম্বর দিন (যেমন: +88017xxxxxxxx)")
        try:
            client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            client.start()
            me = client.get_me()
            safe_name = me.first_name if me else "User"
            print(f"✅ সফলভাবে লগইন সম্পন্ন হয়েছে: {safe_name}")
            client.disconnect()
            print("==================================================\n")
        except Exception as e:
            print(f"⚠️ লগইনে সমস্যা হয়েছে: {e}")
            print("সরাসরি স্ক্রিপ্ট চালু করার চেষ্টা করা হচ্ছে...\n")

def stream_output(pipe, prefix):
    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break
            print(f"{prefix} {line.rstrip()}", flush=True)
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
    print("🧹 পূর্বের কোনো পুরনো প্রসেস থাকলে তা ক্লিয়ার করা হচ্ছে...")
    cleanup_old_instances()
    time.sleep(1)

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
                print(f"⚠️ [🤖 BOT] বন্ধ হয়ে গেছে (Exit code: {ret_bot})! ৫ সেকেন্ড পর রিস্টার্ট হচ্ছে...")
                time.sleep(5)
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
                print(f"⚠️ [⚡ FORWARDER] বন্ধ হয়ে গেছে (Exit code: {ret_fwd})! ৫ সেকেন্ড পর রিস্টার্ট হচ্ছে...")
                time.sleep(5)
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
