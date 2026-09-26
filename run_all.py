"""
════════════════════════════════════════════════════════════════════════════════
             🚀 MASTER RUNNER - PRINCE OTP BOT (run_all.py)
════════════════════════════════════════════════════════════════════════════════
এই স্ক্রিপ্টটি একই সাথে মেইন টেলিগ্রাম বট (bot.py) এবং ivasms ওটিপি ফেচার
(ivasms_fetcher.py) উভয়কেই স্বয়ংক্রিয়ভাবে চালু রাখবে।
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import subprocess
import time
import threading


def cleanup_old_instances():
    """পূর্বে চালু থাকা পুরনো প্রসেস ক্লিয়ার করা"""
    if sys.platform != "win32":
        return
    try:
        curr_pid = os.getpid()
        ps_cmd = (
            f"Get-CimInstance Win32_Process | Where-Object {{ "
            f"($_.CommandLine -like '*bot.py*' -or $_.CommandLine -like '*ivasms_fetcher.py*') "
            f"-and $_.ProcessId -ne {curr_pid} }} | ForEach-Object {{ "
            f"Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    except Exception:
        pass


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
    print("🧹 পূর্বের কোনো পুরনো প্রসেস থাকলে ক্লিয়ার করা হচ্ছে...")
    cleanup_old_instances()
    time.sleep(1)

    print("=" * 60)
    print("  🚀 STARTING BOT + IVASMS OTP FETCHER...")
    print("=" * 60)

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
        env=env,
    )

    # ২. ivasms ওটিপি ফেচার (ivasms_fetcher.py) চালু করা
    fetcher_proc = subprocess.Popen(
        [sys.executable, "-u", "ivasms_fetcher.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    t1 = threading.Thread(target=stream_output, args=(bot_proc.stdout, "[🤖 BOT]"), daemon=True)
    t2 = threading.Thread(target=stream_output, args=(fetcher_proc.stdout, "[📲 IVASMS]"), daemon=True)
    t1.start()
    t2.start()

    print("✅ উভয় সিস্টেম সফলভাবে ব্যাকগ্রাউন্ডে চালু হয়েছে!")
    print("💡 বন্ধ করতে কীবোর্ডে Ctrl + C চাপুন।\n")

    try:
        while True:
            ret_bot     = bot_proc.poll()
            ret_fetcher = fetcher_proc.poll()

            if ret_bot is not None:
                print(f"⚠️ [🤖 BOT] বন্ধ হয়ে গেছে (Exit: {ret_bot})! ৫ সেকেন্ড পর রিস্টার্ট...")
                time.sleep(5)
                bot_proc = subprocess.Popen(
                    [sys.executable, "-u", "bot.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, bufsize=1, encoding="utf-8", errors="replace", env=env,
                )
                threading.Thread(target=stream_output, args=(bot_proc.stdout, "[🤖 BOT]"), daemon=True).start()

            if ret_fetcher is not None:
                print(f"⚠️ [📲 IVASMS] বন্ধ হয়ে গেছে (Exit: {ret_fetcher})! ৫ সেকেন্ড পর রিস্টার্ট...")
                time.sleep(5)
                fetcher_proc = subprocess.Popen(
                    [sys.executable, "-u", "ivasms_fetcher.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, bufsize=1, encoding="utf-8", errors="replace", env=env,
                )
                threading.Thread(target=stream_output, args=(fetcher_proc.stdout, "[📲 IVASMS]"), daemon=True).start()

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 সিস্টেম বন্ধ করা হচ্ছে...")
        bot_proc.terminate()
        fetcher_proc.terminate()
        try:
            bot_proc.wait(timeout=3)
            fetcher_proc.wait(timeout=3)
        except Exception:
            bot_proc.kill()
            fetcher_proc.kill()
        print("✅ উভয় সিস্টেম নিরাপদে বন্ধ করা হয়েছে।")


if __name__ == '__main__':
    main()
