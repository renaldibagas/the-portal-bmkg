import io
import json
import requests
import datetime
from typing import Optional, Dict, Any
from .parser import WeatherData
from .weather_card_generator import WeatherCardGenerator

SEASON_COLORS = {
    "Spring": 0x22C55E,      # Green
    "Summer": 0xF59E0B,      # Bright Orange / Gold
    "Autumn": 0xD97706,      # Deep Amber / Autumn Orange
    "Winter": 0x38BDF8,      # Ice Blue
    "Unknown": 0x64748B      # Slate Gray
}

class DiscordNotifier:
    def __init__(self, webhook_url: str, bot_username: str = "BMKG Lazie"):
        self.webhook_url = webhook_url
        self.bot_username = bot_username
        self.generator = WeatherCardGenerator()

    def _get_embed_color(self, weather_data: WeatherData, is_portal_alert: bool = False) -> int:
        if is_portal_alert or "eclipse" in weather_data.weather.lower() or "moon" in weather_data.weather.lower():
            return 0x8B5CF6  # Deep Mystical Purple
        if "Rain" in weather_data.weather or "Storm" in weather_data.weather:
            return 0x3B82F6  # Storm Blue
        return SEASON_COLORS.get(weather_data.season, 0x6366F1)

    def send_weather_update(
        self,
        weather_data: WeatherData,
        role_ping: Optional[str] = None,
        alert_reason: str = "Weather/Portal Update"
    ) -> bool:
        """
        Renders an ultra-modern weather app card and posts it to Discord with role mentions.
        """
        if not self.webhook_url or not self.webhook_url.startswith("https://discord.com/api/webhooks/"):
            print("[Discord] Invalid or missing Webhook URL!")
            return False

        is_portal_alert = "portal" in alert_reason.lower()
        color = self._get_embed_color(weather_data, is_portal_alert=is_portal_alert)

        # 1. Prepare render data for WeatherCardGenerator
        now = datetime.datetime.now()
        is_day = 6 <= now.hour < 18
        
        card_data = {
            "is_day": is_day,
            "weather_type": weather_data.weather,
            "weather_display": f"{weather_data.weather} • Live",
            "temp_display": "31°" if is_day else "19°",
            "season": weather_data.season or "Spring",
            "season_day": 4,
            "slot_index": 3,
            "server_id": "Online",
            "in_game_clock": weather_data.in_game_time or now.strftime("%I:%M %p"),
            "target_roll_hour": "12:00 PM",
            "slot_progress": (now.minute % 60) / 60.0,
            "storm_level": "70% (Torrential)" if "heavy" in weather_data.weather.lower() else "0% (Calm)",
            "storm_pct": 0.7 if "heavy" in weather_data.weather.lower() else 0.05,
            "wind_force": "0.8 (Gale)" if "gale" in weather_data.weather.lower() else "0.2 (Breeze)",
            "indoor_status": "Outdoors",
            "price_display": "Shop Prices: Normal (1.0x)",
            "damage_mod": "Normal",
            "speed_mod": "Normal",
            "upgrade_bonus": "+0%",
            "mining_speed": "+0%",
            "portal_time_str": weather_data.portal_info or "Check Portal Gate",
            "hourly_slots": [
                {"time": "04 AM", "icon": "Dry", "temp": "28°", "temp_num": 28, "prob": "35%", "is_active": False},
                {"time": "08 AM", "icon": "Drizzle", "temp": "29°", "temp_num": 29, "prob": "22%", "is_active": False},
                {"time": "Now",   "icon": weather_data.weather, "temp": "31°", "temp_num": 31, "prob": "Live", "is_active": True},
                {"time": "04 PM", "icon": "Windy", "temp": "30°", "temp_num": 30, "prob": "12%", "is_active": False},
                {"time": "08 PM", "icon": "Rain", "temp": "26°", "temp_num": 26, "prob": "20%", "is_active": False},
                {"time": "12 AM", "icon": "Night", "temp": "24°", "temp_num": 24, "prob": "8%",  "is_active": False},
            ],
            "odds": [
                ("Dry", "Dry", 35),
                ("Drizzle", "Drizzle", 22),
                ("Rain", "Rain", 20),
                ("Windy", "Windy", 12),
                ("Heavy Rain", "HeavyRain", 8),
                ("Gale", "Gale", 3),
                ("Snow", "Snow", 0),
            ]
        }

        # 2. Render Card Image to Bytes
        img = self.generator.render(card_data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_bytes = buf.getvalue()

        # 3. Build Discord Payload
        content = ""
        if role_ping and role_ping.strip():
            ping_str = role_ping.strip()
            if ping_str.isdigit():
                mention_tag = f"<@&{ping_str}>"
            elif ping_str.startswith("<@&") and ping_str.endswith(">"):
                mention_tag = ping_str
            else:
                mention_tag = f"{ping_str}"
            content = f"📢 **{alert_reason}!** {mention_tag}"

        embed = {
            "title": "📡 THE PORTAL OBSERVATORY • BMKG WEATHER RADAR",
            "description": f"**Status:** {alert_reason}\n*Modern weather telemetry card generated below:*",
            "color": color,
            "image": {
                "url": "attachment://weather_card.png"
            },
            "footer": {
                "text": "Badan Meteorologi Klimatologi dan Gacha (BMKG) • Automated Satellite Card"
            },
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }

        payload = {
            "username": self.bot_username,
            "avatar_url": "https://i.imgur.com/K3Z97fG.png",
            "content": content,
            "embeds": [embed],
            "allowed_mentions": {
                "parse": ["roles", "users", "everyone"]
            }
        }

        # 4. Dispatch Multipart POST
        files = {
            "file": ("weather_card.png", img_bytes, "image/png")
        }

        try:
            response = requests.post(
                self.webhook_url,
                data={"payload_json": json.dumps(payload)},
                files=files,
                timeout=15
            )
            if response.status_code in (200, 204):
                print(f"[Discord] Successfully delivered Weather Card image to Discord!")
                return True
            else:
                print(f"[Discord] Failed to send update. HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[Discord] Error sending webhook payload: {e}")
            return False

    def send_test_message(self) -> bool:
        dummy = WeatherData(
            season="Spring",
            weather="Dry",
            in_game_time="9:17 AM",
            portal_info="Opening in 2 days",
            portal_location="Dewdrop",
            portal_minutes_remaining=3360,
            modifiers=["Price: Normal", "All Fish Biting"]
        )
        return self.send_weather_update(dummy, alert_reason="Test Satellite Broadcast")
