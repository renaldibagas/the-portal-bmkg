"""
BMKG Discord Self-Bot Native Client (Stealth Edition)
Impersonates official Discord Windows Desktop client telemetry.
Works across ALL Python & Discord environments (Python 3.7 - 3.14 / Docker / Cloud).
Listens for '!weather', '!forecast', '!dewdrop', '!gacha' in whitelisted channels.
"""

import os
import io
import time
import json
import random
import asyncio
import aiohttp
import requests
from dotenv import load_dotenv

from src.weather_card_generator import WeatherCardGenerator

load_dotenv()

USER_TOKEN = os.getenv("DISCORD_USER_TOKEN")

ALLOWED_CHANNELS = {
    1450072904120143954,
    1529292291846701117,
    1533253021557850163,
    1532763153492873447,
    1534563959737417820,
    1534644284215529602,
    1534654592866848929,
    1534664853673869443,
    1534743222046163045,
    1534955235351466176,
    1536608615031636048,
    1536763568454631475,
    1543682598302130278,
}

COOLDOWN_SECONDS = 5
last_response_time = {}

# Standard Discord Windows client user agent & headers
CLIENT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

generator = WeatherCardGenerator()

async def send_typing(session: aiohttp.ClientSession, channel_id: int, token: str):
    """Trigger typing indicator in channel."""
    try:
        url = f"https://discord.com/api/v9/channels/{channel_id}/typing"
        headers = {"Authorization": token, "User-Agent": CLIENT_USER_AGENT}
        async with session.post(url, headers=headers) as resp:
            pass
    except Exception:
        pass

async def send_weather_reply(session: aiohttp.ClientSession, channel_id: int, token: str, reply_to_id: int = None):
    """Generates the card and uploads directly via Discord REST API."""
    # 1. Fetch live telemetry from Railway cloud
    payload = {}
    try:
        r = requests.get("https://web-production-2cdb.up.railway.app/api/telemetry/latest", timeout=3.5, verify=False)
        if r.status_code == 200:
            payload = r.json()
    except Exception as e:
        print(f"[SelfBot] Telemetry sync warning: {e}")

    # 2. Render weather card in memory
    img = generator.render(payload)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    buf.seek(0)
    img_bytes = buf.getvalue()

    # 3. Multipart form upload to channel
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "User-Agent": CLIENT_USER_AGENT
    }

    form = aiohttp.FormData()
    body_data = {}
    if reply_to_id:
        body_data["message_reference"] = {
            "message_id": str(reply_to_id),
            "fail_if_not_exists": False
        }
    form.add_field("payload_json", json.dumps(body_data), content_type="application/json")
    form.add_field("file", img_bytes, filename="portal_weather_card.jpg", content_type="image/jpeg")

    async with session.post(url, headers=headers, data=form) as resp:
        if resp.status in (200, 201):
            print(f"[{time.strftime('%H:%M:%S')}] Weather card sent to channel {channel_id}!")
        else:
            txt = await resp.text()
            print(f"[SelfBot] Upload failed ({resp.status}): {txt}")

async def heartbeat_loop(ws, interval: float, last_seq_ref):
    """Maintains heartbeat with Discord gateway."""
    try:
        while True:
            await asyncio.sleep(interval)
            payload = {"op": 1, "d": last_seq_ref[0]}
            await ws.send_str(json.dumps(payload))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[SelfBot] Heartbeat error: {e}")

async def run_gateway_client(token: str):
    headers = {"User-Agent": CLIENT_USER_AGENT}
    gateway_url = "wss://gateway.discord.gg/?v=9&encoding=json"

    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] [SelfBot] Connecting to Discord Gateway (Stealth Client)...")
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.ws_connect(gateway_url, max_msg_size=10*1024*1024) as ws:
                    hello = await ws.receive()
                    hello_data = json.loads(hello.data)
                    hb_interval = hello_data["d"]["heartbeat_interval"] / 1000.0

                    last_seq = [None]
                    hb_task = asyncio.create_task(heartbeat_loop(ws, hb_interval, last_seq))

                    # Send Windows Client Identification
                    identify = {
                        "op": 2,
                        "d": {
                            "token": token,
                            "capabilities": 16381,
                            "properties": {
                                "os": "Windows",
                                "browser": "Chrome",
                                "device": "",
                                "system_locale": "en-US",
                                "browser_user_agent": CLIENT_USER_AGENT,
                                "browser_version": "122.0.0.0",
                                "os_version": "10",
                                "referrer": "",
                                "referring_domain": "",
                                "referrer_current": "",
                                "referring_domain_current": "",
                                "release_channel": "stable",
                                "client_build_number": 275000,
                                "client_event_source": None
                            },
                            "presence": {
                                "status": "online",
                                "since": 0,
                                "activities": [],
                                "afk": False
                            },
                            "compress": False,
                            "client_state": {
                                "guild_versions": {}
                            }
                        }
                    }
                    await ws.send_str(json.dumps(identify))

                    my_user_id = None

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            op = data.get("op")
                            t = data.get("t")
                            seq = data.get("s")
                            if seq is not None:
                                last_seq[0] = seq

                            if t == "READY":
                                u = data["d"]["user"]
                                my_user_id = str(u["id"])
                                print("=" * 60)
                                print(f"BMKG Stealth Self-Bot connected as: {u['username']} (ID: {my_user_id})")
                                print(f"Listening in {len(ALLOWED_CHANNELS)} whitelisted channels...")
                                print("=" * 60)

                            elif t == "MESSAGE_CREATE":
                                m = data.get("d", {})
                                author = m.get("author", {})
                                author_id = str(author.get("id"))
                                ch_id = int(m.get("channel_id", 0))
                                content = str(m.get("content", "")).strip().lower()

                                # 1. Ignore own messages
                                if author_id == my_user_id:
                                    continue

                                # 2. Filter strictly by whitelisted channels
                                if ch_id not in ALLOWED_CHANNELS:
                                    continue

                                # 3. Prefix matching
                                valid_prefixes = ("!weather", "!forecast", "!cuaca", "!bmkg", "!portal", "!gacha")
                                if not any(content.startswith(p) for p in valid_prefixes):
                                    continue

                                # 4. Cooldown check
                                now = time.time()
                                if ch_id in last_response_time and (now - last_response_time[ch_id]) < COOLDOWN_SECONDS:
                                    continue
                                last_response_time[ch_id] = now

                                print(f"[{time.strftime('%H:%M:%S')}] Trigger '{content}' from {author.get('username')} in channel {ch_id}")

                                # 5. Natural humanized delay & typing simulation
                                async def process_reply(target_ch, msg_id):
                                    await send_typing(session, target_ch, token)
                                    human_delay = random.uniform(1.2, 2.5)
                                    await asyncio.sleep(human_delay)
                                    await send_weather_reply(session, target_ch, token, reply_to_id=msg_id)

                                asyncio.create_task(process_reply(ch_id, m.get("id")))

                            elif op == 7: # Reconnect request
                                print("[SelfBot] Gateway requested reconnect.")
                                break
                            elif op == 9: # Invalid session
                                print("[SelfBot] Invalid session, waiting before retry...")
                                await asyncio.sleep(5)
                                break

                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            print(f"[SelfBot] Gateway connection closed: {msg}")
                            break

                    hb_task.cancel()

        except Exception as err:
            print(f"[SelfBot] Connection error: {err}. Reconnecting in 5s...")
            await asyncio.sleep(5)

def start_selfbot_background(token: str):
    """Spins up the selfbot in an independent background thread with its own event loop."""
    import threading
    def worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_gateway_client(token))

    t = threading.Thread(target=worker, daemon=True, name="BMKG_Stealth_SelfBot")
    t.start()
    print("[SelfBot] 🤖 Background stealth self-bot thread spawned!")
    return t

if __name__ == "__main__":
    if not USER_TOKEN:
        print("ERROR: DISCORD_USER_TOKEN not set!")
    else:
        print("Starting BMKG Stealth Self-Bot Client (Standalone)...")
        asyncio.run(run_gateway_client(USER_TOKEN))
