import io
import json
import os
import datetime
import tempfile
import uuid
from flask import Flask, request, jsonify, send_from_directory
import requests

from src.weather_card_generator import WeatherCardGenerator

app = Flask(__name__)

CARDS_DIR = os.path.join(tempfile.gettempdir(), "bmkg_cards")
os.makedirs(CARDS_DIR, exist_ok=True)

# Discord Webhook (configured via Environment Variable or local .env)
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

generator = WeatherCardGenerator()

# -----------------------------------------------------------------
# 24/7 CLOUD DISCORD BOT THREAD (Runs automatically on Render / Gunicorn)
# -----------------------------------------------------------------
_bot_started = False
_bot_error = None
_bot_instance_ref = None

def init_cloud_discord_bot():
    global _bot_started, _bot_error, _bot_instance_ref
    if _bot_started:
        return
    # Check multiple common env var names
    bot_token = (
        os.environ.get("DISCORD_BOT")
        or os.environ.get("DISCORD_BOT_TOKEN")
        or os.environ.get("DISCORD_TOKEN")
        or os.environ.get("BOT_TOKEN")
        or os.environ.get("TOKEN")
    )
    if not bot_token:
        # Check local .env fallback
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if any(line.startswith(k) for k in ["DISCORD_BOT=", "DISCORD_BOT_TOKEN=", "DISCORD_TOKEN=", "BOT_TOKEN="]):
                        bot_token = line.strip().split("=", 1)[1].strip("\"'")
                        break

    if bot_token:
        _bot_started = True
        import threading
        def run_bot_worker():
            global _bot_error, _bot_instance_ref
            import asyncio
            try:
                from src.discord_bot import bot as discord_bot_instance
                _bot_instance_ref = discord_bot_instance
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(discord_bot_instance.start(bot_token))
            except Exception as be:
                import traceback
                _bot_error = f"{be}\n{traceback.format_exc()}"
                print(f"[Cloud Error] Discord Bot runner error: {_bot_error}")

        t = threading.Thread(target=run_bot_worker, daemon=True, name="DiscordBotThread")
        t.start()
        print("[Cloud] 🚀 Discord Bot (Slash Commands & Reaction Roles) launched 24/7 on Render!")
    else:
        _bot_error = "DISCORD_BOT_TOKEN environment variable is not set."

init_cloud_discord_bot()

# -----------------------------------------------------------------
# CLOUD DISCORD STEALTH SELF-BOT (DISABLED FOR SECURITY)
# -----------------------------------------------------------------
_selfbot_started = False


def upload_card_to_cdn(img_bytes, base_name="weather_card.jpg"):
    ua_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    # 1. Primary: Catbox.moe (Direct static image CDN with permanent hosting & full Discord crawler support)
    try:
        r = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (base_name, img_bytes, "image/jpeg")},
            headers=ua_headers,
            timeout=12
        )
        if r.status_code == 200 and r.text.startswith("https://files.catbox.moe/"):
            return r.text.strip()
    except Exception as e:
        print(f"[CDN] Catbox upload error: {e}")

    # 2. Secondary: Litterbox (Temporary 72h Catbox mirror)
    try:
        r = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "72h"},
            files={"fileToUpload": (base_name, img_bytes, "image/jpeg")},
            headers=ua_headers,
            timeout=12
        )
        if r.status_code == 200 and r.text.startswith("https://litter.catbox.moe/"):
            return r.text.strip()
    except Exception as e:
        print(f"[CDN] Litterbox upload error: {e}")

    return None

@app.route("/", methods=["GET"])
def health():
    bot_ready = False
    bot_user = None
    if _bot_instance_ref is not None:
        try:
            bot_ready = _bot_instance_ref.is_ready()
            if _bot_instance_ref.user:
                bot_user = str(_bot_instance_ref.user)
        except Exception:
            pass

    matched_keys = [k for k in os.environ.keys() if any(sub in k.upper() for sub in ["TOKEN", "DISCORD", "BOT"])]
    return jsonify({
        "status": "online",
        "service": "BMKG Weather Card Cloud Generator",
        "version": "2.5.2-direct-cdn",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "bot": {
            "has_token": bool(os.environ.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_TOKEN") or os.environ.get("BOT_TOKEN") or os.environ.get("TOKEN")),
            "started": _bot_started,
            "ready": bot_ready,
            "user": bot_user,
            "error": _bot_error,
            "matched_env_keys": matched_keys
        },
        "selfbot": {
            "has_token": bool(os.environ.get("DISCORD_USER_TOKEN")),
            "started": _selfbot_started
        }
    })

@app.route("/cards/<filename>", methods=["GET"])
def serve_card(filename):
    res = send_from_directory(CARDS_DIR, filename, mimetype="image/jpeg")
    res.headers["Cache-Control"] = "public, max-age=86400"
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

@app.route("/api/card/upload", methods=["POST"])
def render_and_upload():
    """
    Renders the anime weather card and serves it directly from the cloud instance.
    Returns direct image URL that Discord embeds immediately with 1080x1680 dimensions!
    """
    try:
        payload = request.get_json(force=True) or {}
        img = generator.render(payload)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=90)
        buf.seek(0)
        img_bytes = buf.getvalue()

        # Save unique card and latest.jpg for live viewing
        weather_slug = payload.get("weather_type", "weather").lower()
        file_id = f"card_{int(datetime.datetime.utcnow().timestamp())}_{weather_slug}_{uuid.uuid4().hex[:6]}.jpg"
        
        local_path = os.path.join(CARDS_DIR, file_id)
        with open(local_path, "wb") as f:
            f.write(img_bytes)

        latest_path = os.path.join(CARDS_DIR, "latest.jpg")
        with open(latest_path, "wb") as f:
            f.write(img_bytes)

        # Persist latest telemetry payload so Discord slash commands have real-time game data
        try:
            global _latest_telemetry_cache
            _latest_telemetry_cache = payload
            state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmkg_latest_state.json")
            with open(state_file, "w", encoding="utf-8") as sf:
                json.dump(payload, sf, indent=2)
        except Exception as se:
            print(f"[Warning] Failed to save latest telemetry: {se}")

        # Host URL (auto-detect across Railway, Render, or fallback)
        railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        if railway_domain:
            host_url = f"https://{railway_domain}"
        else:
            host_url = os.environ.get("RENDER_EXTERNAL_URL") or "https://web-production-2cdb.up.railway.app"

        card_url = f"{host_url.rstrip('/')}/cards/{file_id}"

        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🎨 Card generated: {card_url}")

        return jsonify({
            "status": "success",
            "image_url": card_url
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

_latest_telemetry_cache = {}

@app.route("/api/telemetry", methods=["POST"])
def post_telemetry():
    """Endpoint for Roblox client or scraper to push state updates without generating a full card."""
    global _latest_telemetry_cache
    try:
        payload = request.get_json(force=True) or {}
        _latest_telemetry_cache = payload
        state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmkg_latest_state.json")
        with open(state_file, "w", encoding="utf-8") as sf:
            json.dump(payload, sf, indent=2)
        return jsonify({"status": "success", "message": "Telemetry updated"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

@app.route("/api/telemetry/latest", methods=["GET"])
def get_latest_telemetry():
    """Serves the latest live telemetry reported by Roblox to all bot instances."""
    global _latest_telemetry_cache
    if _latest_telemetry_cache and "weather_type" in _latest_telemetry_cache:
        return jsonify(_latest_telemetry_cache)
        
    state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmkg_latest_state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as sf:
                data = json.load(sf)
                if data and "weather_type" in data:
                    _latest_telemetry_cache = data
                    return jsonify(data)
        except Exception:
            pass

    # Fallback to calculated current season state
    try:
        from src.game_data_engine import get_current_season_state, get_seasonal_odds, WEATHER_DISPLAY_NAMES, WEATHER_EFFECTS
        s_state = get_current_season_state()
        odds = get_seasonal_odds(s_state["season"], s_state["season_day"])
        top_weather = odds[0][0] if odds else "Dry"
        fallback_data = {
            "weather_type": top_weather,
            "weather_display": WEATHER_DISPLAY_NAMES.get(top_weather, top_weather),
            "season": s_state["season"],
            "season_day": s_state["season_day"],
            "slot_index": s_state["slot_index"],
            "server_id": "Synchronized",
            "in_game_clock": "12:00 PM",
            "temp_display": "31°",
            "active_modifiers": [WEATHER_EFFECTS.get(top_weather, {}).get("notes", "Normal Conditions")],
            "odds": [(name, name, pct) for name, pct in odds]
        }
        return jsonify(fallback_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def handle_stats():
    try:
        from src.discord_bot import get_install_stats
        return jsonify(get_install_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/weather", methods=["POST"])
def handle_weather():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"error": "No JSON payload provided"}), 400

        # Save latest telemetry
        global _latest_telemetry_cache
        _latest_telemetry_cache = payload
        try:
            state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bmkg_latest_state.json")
            with open(state_file, "w", encoding="utf-8") as sf:
                json.dump(payload, sf, indent=2)
        except Exception:
            pass

        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 📸 Rendering weather card for: {payload.get('weather_type', 'Unknown')}")

        # Render high-resolution image card
        img = generator.render(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_bytes = buf.getvalue()

        # Build Discord message
        role_ping = payload.get("role_ping", "")
        alert_reason = payload.get("alert_reason", "Weather Update")
        content = f"📢 **{alert_reason}!** {role_ping}" if role_ping else ""

        embed = {
            "color": payload.get("color", 0x3498DB),
            "image": {"url": "attachment://weather_card.png"}
        }

        discord_payload = {
            "username": "BMKG Lazie",
            "avatar_url": "https://i.imgur.com/K3Z97fG.png",
            "content": content,
            "embeds": [embed],
            "allowed_mentions": {"parse": ["roles", "users", "everyone"]}
        }

        # 1. First attempt: Direct Discord Webhook multipart upload
        target_webhook = payload.get("webhook_url", WEBHOOK_URL)
        headers = {"User-Agent": "BMKGObservatory/2.0 (ThePortalRadar; Python/Pillow)"}
        
        try:
            res = requests.post(
                target_webhook,
                data={"payload_json": json.dumps(discord_payload)},
                files={"file": ("weather_card.png", img_bytes, "image/png")},
                headers=headers,
                timeout=15
            )
            if res.status_code in (200, 204):
                return jsonify({"success": True, "message": "Weather card delivered directly to Discord!"})
        except Exception as e:
            print(f"[Warn] Direct Discord delivery failed: {e}")

        # 2. Resilient fallback: Upload card to tmpfiles.org and dispatch via Discord proxy
        # (Bypasses Cloudflare Error 1015 datacenter IP blocks on Render)
        fallback_error = "Unknown"
        try:
            print("[Cloud] Direct Discord blocked. Using tmpfiles CDN + Webhook Proxy fallback...")
            tmp_res = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": ("weather_card.png", img_bytes, "image/png")},
                timeout=25
            )
            print(f"[Cloud] tmpfiles response: {tmp_res.status_code}")
            if tmp_res.status_code == 200:
                res_data = tmp_res.json()
                raw_url = res_data.get("data", {}).get("url", "")
                if raw_url:
                    # Convert tmpfiles view URL into direct download image URL: https://tmpfiles.org/dl/...
                    direct_img_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                    embed["image"] = {"url": direct_img_url}
                    discord_payload["embeds"] = [embed]
                    
                    # Dispatch to Discord via Roblox-approved proxy
                    proxy_url = target_webhook.replace("https://discord.com", "https://webhook.lewisakura.moe")
                    browser_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    }
                    p_res = requests.post(proxy_url, json=discord_payload, headers=browser_headers, timeout=15)
                    print(f"[Cloud] Proxy response: {p_res.status_code}")
                    if p_res.status_code in (200, 204):
                        return jsonify({"success": True, "message": "Weather card delivered via CDN Proxy!", "cdn_url": direct_img_url})
                    else:
                        fallback_error = f"Proxy error {p_res.status_code}: {p_res.text}"
                else:
                    fallback_error = f"tmpfiles missing URL in data: {res_data}"
            else:
                fallback_error = f"tmpfiles upload failed: {tmp_res.status_code} -> {tmp_res.text}"
        except Exception as e:
            fallback_error = f"Fallback exception: {str(e)}"
            print(f"[Error] Fallback delivery failed: {e}")

        return jsonify({"success": False, "message": "Could not deliver card to Discord", "detail": fallback_error}), 502

    except Exception as e:
        print(f"[Error] Failed to render card: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # If DISCORD_BOT_TOKEN is provided, launch Discord Slash Bot concurrently in background thread
    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    if bot_token:
        import threading
        try:
            from src.discord_bot import bot as discord_bot_instance
            def start_bot():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(discord_bot_instance.start(bot_token))
            t = threading.Thread(target=start_bot, daemon=True)
            t.start()
            print("[Cloud] 🤖 Discord Slash Command Bot started in background thread!")
        except Exception as be:
            print(f"[Warning] Could not start Discord Slash Bot: {be}")

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
