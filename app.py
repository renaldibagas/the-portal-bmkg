import io
import json
import os
import datetime
import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
from PIL import Image

from src.weather_card_generator import WeatherCardGenerator

# 1. Initialize Generator & Fast Webhook Dispatcher
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
generator = WeatherCardGenerator()

# 2. FastAPI Backend (Receives requests from Roblox 24/7)
fastapi_app = FastAPI()

@fastapi_app.get("/health")
def health():
    return {
        "status": "online",
        "service": "BMKG Weather Card Cloud Engine",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

@fastapi_app.post("/api/weather")
async def handle_weather(request: Request):
    try:
        payload = await request.json()
        if not payload:
            return JSONResponse({"error": "No JSON payload provided"}, status_code=400)

        # Render high-resolution anime image card
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
            "footer": {"text": "Badan Meteorologi Klimatologi dan Gacha (BMKG) • 24/7 Cloud Satellite Radar"},
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }

        discord_payload = {
            "username": "BMKG Lazie",
            "avatar_url": "https://i.imgur.com/K3Z97fG.png",
            "content": content,
            "embeds": [embed],
            "allowed_mentions": {"parse": ["roles", "users", "everyone"]}
        }

        files = {"file": ("weather_card.png", img_bytes, "image/png")}
        target_webhook = payload.get("webhook_url", WEBHOOK_URL)

        res = requests.post(
            target_webhook,
            data={"payload_json": json.dumps(discord_payload)},
            files=files,
            timeout=15
        )

        if res.status_code in (200, 204):
            return {"success": True, "message": "Weather card delivered to Discord!"}
        else:
            return JSONResponse({"success": False, "discord_status": res.status_code, "detail": res.text}, status_code=502)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# 3. Interactive Web Dashboard (Gradio UI)
def generate_preview(weather_type, season, time_of_day, clock_str):
    data = {
        "weather_type": weather_type,
        "season": season,
        "time_of_day": time_of_day.lower(),
        "in_game_clock": clock_str,
        "target_roll_hour": "12:00 PM",
        "active_modifiers": [
            "Auto-Water Crops 100%",
            "Lumen Drops +35%",
            "Sprint Stamina Drain -20%"
        ]
    }
    img = generator.render(data)
    return img

with gr.Blocks(title="BMKG Portal Observatory Radar") as demo:
    gr.Markdown("# 📡 BMKG Weather Observatory • Live Cloud Engine")
    gr.Markdown("24/7 Cloud Image Generator & Discord Dispatcher for *The Portal*. API endpoint: `POST /api/weather`")
    
    with gr.Row():
        with gr.Column(scale=1):
            weather_in = gr.Dropdown(
                ["Dry", "Northern Lights", "Nightmare", "Rain", "Heavy Rain", "Drizzle", "Snow", "Gale", "Windy", "Portal Eclipse"],
                value="Northern Lights",
                label="Weather Condition"
            )
            season_in = gr.Dropdown(["Spring", "Summer", "Autumn", "Winter"], value="Winter", label="Season")
            tod_in = gr.Radio(["Day", "Afternoon", "Night"], value="Night", label="Time of Day")
            clock_in = gr.Textbox(value="11:45 PM", label="In-Game Clock")
            btn = gr.Button("Render & Preview Card", variant="primary")
            
        with gr.Column(scale=2):
            preview_out = gr.Image(label="Live Render Output", type="pil")

    btn.click(generate_preview, inputs=[weather_in, season_in, tod_in, clock_in], outputs=[preview_out])

# Mount Gradio into FastAPI
app = gr.mount_gradio_app(fastapi_app, demo, path="/")
