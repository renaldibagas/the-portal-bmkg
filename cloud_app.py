import io
import json
import os
import datetime
from flask import Flask, request, jsonify
import requests

from src.weather_card_generator import WeatherCardGenerator

app = Flask(__name__)

# Discord Webhook (configured via Environment Variable or default fallback)
DEFAULT_WEBHOOK = "https://discord.com/api/webhooks/1540322408672534558/4UCzxOUqPmWeE-GYbWZ0ebZmyFB0ewE4dTZZziInsfZwnOzVJ9A4wXNO0dIdUfJzX7fC"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", DEFAULT_WEBHOOK)

generator = WeatherCardGenerator()

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "service": "BMKG Weather Card Cloud Generator",
        "version": "2.2.0-resilient",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    })

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

        # 2. Resilient fallback: Upload card to Catbox and dispatch via Discord proxy
        # (Bypasses Cloudflare Error 1015 datacenter IP rate limits on Render)
        fallback_error = "Unknown"
        try:
            print("[Cloud] Direct Discord blocked. Using Catbox CDN + Webhook Proxy fallback...")
            cat_res = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": ("weather_card.png", img_bytes, "image/png")},
                timeout=20
            )
            print(f"[Cloud] Catbox upload response: {cat_res.status_code} -> {cat_res.text[:80]}")
            if cat_res.status_code == 200 and cat_res.text.strip().startswith("http"):
                hosted_url = cat_res.text.strip()
                embed["image"] = {"url": hosted_url}
                discord_payload["embeds"] = [embed]
                
                # Send via reliable Roblox/Discord proxy or target webhook
                proxy_url = target_webhook.replace("https://discord.com", "https://webhook.lewisakura.moe")
                p_res = requests.post(proxy_url, json=discord_payload, timeout=15)
                print(f"[Cloud] Proxy response: {p_res.status_code}")
                if p_res.status_code in (200, 204):
                    return jsonify({"success": True, "message": "Weather card delivered via CDN Proxy!", "cdn_url": hosted_url})
                else:
                    fallback_error = f"Proxy error {p_res.status_code}: {p_res.text}"
            else:
                fallback_error = f"Catbox upload failed: {cat_res.status_code} -> {cat_res.text}"
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
