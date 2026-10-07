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

# Discord Webhook (configured via Environment Variable or default fallback)
DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/1540322408672534558/4UCzxOUqPmWeE-GYbWZ0ebZmyFB0ewE4dTZZziInsfZwnOzVJ9A4wXNO0dIdUfJzX7fC"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", DEFAULT_WEBHOOK)

generator = WeatherCardGenerator()

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
    return jsonify({
        "status": "online",
        "service": "BMKG Weather Card Cloud Generator",
        "version": "2.4.1-catbox-direct",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    })

@app.route("/cards/<filename>", methods=["GET"])
def serve_card(filename):
    return send_from_directory(CARDS_DIR, filename, mimetype="image/jpeg")

@app.route("/api/card/upload", methods=["POST"])
def render_and_upload():
    """
    Renders the anime weather card and uploads it to CDN (Catbox / Litterbox / Render direct).
    Returns direct image URL that Discord embeds immediately with full dimensions!
    """
    try:
        payload = request.get_json(force=True) or {}
        img = generator.render(payload)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=90)
        buf.seek(0)
        img_bytes = buf.getvalue()

        # Always save a local copy for direct serving fallback
        file_id = f"card_{uuid.uuid4().hex[:10]}.jpg"
        local_path = os.path.join(CARDS_DIR, file_id)
        with open(local_path, "wb") as f:
            f.write(img_bytes)

        # Also save latest.jpg
        latest_path = os.path.join(CARDS_DIR, "latest.jpg")
        with open(latest_path, "wb") as f:
            f.write(img_bytes)

        # Upload to CDN for fastest Discord unfurling
        cdn_url = upload_card_to_cdn(img_bytes, base_name="weather_card.jpg")
        if not cdn_url:
            host_url = request.host_url.rstrip("/")
            cdn_url = f"{host_url}/cards/{file_id}"

        return jsonify({
            "status": "success",
            "image_url": cdn_url
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/api/weather", methods=["POST"])
def handle_weather():
    try:
        payload = request.get_json(force=True)
        if not payload:
            return jsonify({"error": "No JSON payload provided"}), 400

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
            "title": "📡 THE PORTAL OBSERVATORY • BMKG WEATHER RADAR",
            "description": payload.get("description", f"Live forecast generated for **{payload.get('weather_display', 'The Portal')}**"),
            "color": payload.get("color", 0x3498DB),
            "image": {"url": "attachment://weather_card.png"},
            "footer": {"text": "Badan Meteorologi Klimatologi dan Gacha (BMKG) • Cloud Satellite Radar"},
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
