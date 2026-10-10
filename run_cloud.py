import os
import sys
import subprocess
import time

def main():
    print("[Launcher] 🚀 Starting BMKG Cloud Suite (Web API + Discord Bot)...")
    
    # 1. Start Discord Bot as a dedicated, independent process
    bot_token = (
        os.environ.get("DISCORD_BOT")
        or os.environ.get("DISCORD_BOT_TOKEN")
        or os.environ.get("DISCORD_TOKEN")
        or os.environ.get("BOT_TOKEN")
        or os.environ.get("TOKEN")
    )
    
    if bot_token:
        print(f"[Launcher] Discord Bot token detected ({bot_token[:6]}...). Launching bot process...")
        # Pass token explicitly in environment to ensure sub-process picks it up
        env = os.environ.copy()
        env["DISCORD_BOT"] = bot_token
        env["DISCORD_BOT_TOKEN"] = bot_token
        bot_proc = subprocess.Popen([sys.executable, "-m", "src.discord_bot"], env=env)
        print(f"[Launcher] Discord Bot sub-process started (PID: {bot_proc.pid})")
    else:
        print("[Launcher] ⚠️ WARNING: DISCORD_BOT token not found in environment variables!")

    # 1b. Start Alt Account Self-Bot as a dedicated, independent process if DISCORD_USER_TOKEN is set
    user_token = os.environ.get("DISCORD_USER_TOKEN")
    if user_token:
        print(f"[Launcher] Discord User Token detected ({user_token[:6]}...). Launching stealth self-bot listener...")
        user_env = os.environ.copy()
        user_env["DISCORD_USER_TOKEN"] = user_token
        selfbot_proc = subprocess.Popen([sys.executable, "-m", "src.selfbot_client"], env=user_env)
        print(f"[Launcher] Stealth Self-Bot sub-process started (PID: {selfbot_proc.pid})")
    else:
        print("[Launcher] (Info: DISCORD_USER_TOKEN not set, skipping self-bot listener)")

    # 2. Start Gunicorn Web Server for Cloudflare/Discord CDN and Webhook handling
    raw_port = os.environ.get("PORT", "8080")
    port = raw_port if str(raw_port).isdigit() else "8080"
    print(f"[Launcher] Starting Gunicorn on 0.0.0.0:{port} (raw PORT was: {raw_port})...")
    
    cmd = [
        sys.executable, "-m", "gunicorn",
        "cloud_app:app",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "1",
        "--timeout", "120"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("[Launcher] Process interrupted, exiting.")

if __name__ == "__main__":
    main()
