"""
BMKG Discord Bot Application
Supports both standard Prefix Commands (!weather, !gacha, !portal, !modifiers, !forecast, !help)
AND Discord Slash Commands (/weather, /gacha, /portal, /modifiers, /forecast, /help on discord.py 2.x).
Compatible across both discord.py 1.7.x and modern discord.py 2.x on Python 3.7+ / 3.11+ / Render Cloud.
"""

import os
import io
import json
import time
import asyncio
import datetime
from typing import Optional

import discord
from discord.ext import commands
try:
    from discord import app_commands
except ImportError:
    app_commands = None

from src.weather_card_generator import WeatherCardGenerator
from src.game_data_engine import (
    WEATHER_DISPLAY_NAMES,
    WEATHER_COLORS,
    WEATHER_EFFECTS,
    get_current_season_state,
    get_seasonal_odds,
    get_next_weekly_boss_schedule
)

# Load token securely from environment or local .env file
def get_bot_token():
    token = os.environ.get("DISCORD_BOT") or os.environ.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_TOKEN")
    if token:
        return token
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if any(line.startswith(k) for k in ["DISCORD_BOT=", "DISCORD_BOT_TOKEN=", "DISCORD_TOKEN="]):
                    return line.strip().split("=", 1)[1].strip("\"'")
    return ""

DISCORD_BOT_TOKEN = get_bot_token()
LATEST_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bmkg_latest_state.json")

# Discord.py 1.7 vs 2.x compatibility
HAS_SLASH_TREE = hasattr(discord, "app_commands") and app_commands is not None

intents = discord.Intents.default()
intents.members = True
if hasattr(intents, "message_content"):
    intents.message_content = True

bot = commands.Bot(command_prefix=["!", "/", "."], intents=intents, help_command=None)
generator = WeatherCardGenerator()

def load_latest_telemetry() -> dict:
    """Reads the latest live telemetry reported by the Roblox client."""
    # 0. In-memory cache check (when running embedded inside cloud_app.py)
    try:
        import sys
        if "cloud_app" in sys.modules:
            ca = sys.modules["cloud_app"]
            if hasattr(ca, "_latest_telemetry_cache") and ca._latest_telemetry_cache and "weather_type" in ca._latest_telemetry_cache:
                return ca._latest_telemetry_cache
    except Exception:
        pass

    # 1. Local state file check
    if os.path.exists(LATEST_DATA_PATH):
        try:
            with open(LATEST_DATA_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
                if d and "weather_type" in d:
                    return d
        except Exception:
            pass

    # 2. Cross-cloud telemetry sync (fetches directly from active web service)
    import requests
    sync_endpoints = [
        "https://web-production-2cdb.up.railway.app/api/telemetry/latest",
        "https://the-portal-bmkg.onrender.com/api/telemetry/latest"
    ]
    for endpoint in sync_endpoints:
        try:
            r = requests.get(endpoint, timeout=2.0)
            if r.status_code == 200:
                d = r.json()
                if d and "weather_type" in d:
                    return d
        except Exception:
            pass

    # 3. Fallback to calculated mathematical state if Roblox client is temporarily offline
    s_state = get_current_season_state()
    odds = get_seasonal_odds(s_state["season"], s_state["season_day"])
    top_weather = odds[0][0] if odds else "Dry"
    
    return {
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

def build_weather_embed_and_file():
    data = load_latest_telemetry()
    w_type = data.get("weather_type", "Dry")
    w_color = WEATHER_COLORS.get(w_type, 0x3498DB)
    
    img = generator.render(data)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    buf.seek(0)
    
    discord_file = discord.File(buf, filename="weather_card.jpg")
    embed = discord.Embed(
        color=w_color,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_image(url="attachment://weather_card.jpg")
    embed.set_footer(
        text="Badan Meteorologi Klimatologi dan Gacha (BMKG) • 24/7 Observatory",
        icon_url="https://i.imgur.com/K3Z97fG.png"
    )
    return embed, discord_file

def build_gacha_embed():
    data = load_latest_telemetry()
    season = data.get("season", "Summer")
    day = data.get("season_day", 1)
    
    odds = get_seasonal_odds(season, day)
    
    lines = []
    for name, pct in odds:
        disp = WEATHER_DISPLAY_NAMES.get(name, name)
        blocks = int(pct / 10)
        bar = "█" * blocks + "░" * (10 - blocks)
        lines.append(f"`{bar}` **{pct:2d}%** — {disp}")
        
    embed = discord.Embed(
        title=f"🎲 24H Weather Gacha Forecast • {season} Day {day}",
        description="Daily weather probability pool rolled every 2 real hours:\n\n" + "\n".join(lines),
        color=0xF1C40F,
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(
        name="ℹ️ Seasonal Gacha Mechanics",
        value="• Weather slots roll automatically at fixed 2-hour intervals.\n"
              "• Special events like **Northern Lights** & **Nightmare** have independent roll chance.",
        inline=False
    )
    embed.set_footer(text="BMKG Observatory Gacha Analytics")
    return embed

def build_portal_embed():
    boss_info = get_next_weekly_boss_schedule()
    data = load_latest_telemetry()
    
    portal_str = data.get("portal_time_str", "Opening soon")
    target_epoch = boss_info["target_epoch"]
    
    embed = discord.Embed(
        title="🌀 Dimensional Rift • Dewdrop Portal & Lycaros Raid",
        description=f"> 🚪 **Gate Status:** `{portal_str}`\n"
                    f"> 🐺 **Lycaros Raid:** <t:{target_epoch}:F> (<t:{target_epoch}:R>)\n"
                    f"> ⏳ **Time Remaining:** `{boss_info['time_str']}`",
        color=0x9B59B6,
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(
        name="🧬 Crop Mutations during Rift",
        value="• **Portal Eclipse:** `2.65x` Shadow Mutations (Every 120s)\n"
              "• **Nightmare:** `3.7x` Ghost Mutations (Every 120s)",
        inline=True
    )
    embed.add_field(
        name="🎣 Dimensional Fishing & Combat",
        value="• **Eclipse Biting:** `100%` Universal All-Fish Active\n"
              "• **Damage & Speed Buff:** `+10%` during active Rift",
        inline=True
    )
    embed.set_footer(text="BMKG Dimensional Observatory")
    return embed

def build_modifiers_embed():
    data = load_latest_telemetry()
    w_type = data.get("weather_type", "Dry")
    w_effects = WEATHER_EFFECTS.get(w_type, WEATHER_EFFECTS["Dry"])
    
    p_pct = int((w_effects.get("price", 1.0) - 1.0) * 100)
    d_pct = int((w_effects.get("damage", 1.0) - 1.0) * 100)
    s_pct = int((w_effects.get("speed", 1.0) - 1.0) * 100)
    w_pct = int(w_effects.get("autowater", 0.0) * 100)
    
    p_str = f"+{p_pct}% (Surcharge)" if p_pct > 0 else ("Sale!" if p_pct < 0 else "1.0x (Normal)")
    d_str = f"{d_pct:+d}%" if d_pct != 0 else "1.0x (Normal)"
    s_str = f"{s_pct:+d}%" if s_pct != 0 else "1.0x (Normal)"
    w_str = f"{w_pct}%" if w_pct > 0 else "None (Manual watering required)"
    
    embed = discord.Embed(
        title=f"⚔️ Active Realm Modifiers • {WEATHER_DISPLAY_NAMES.get(w_type, w_type)}",
        description=f"**Current Weather Effect Summary:**\n{w_effects.get('notes', 'Normal conditions')}",
        color=WEATHER_COLORS.get(w_type, 0x3498DB),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="🛒 Shop Prices", value=f"`{p_str}`", inline=True)
    embed.add_field(name="⚔️ Damage Output", value=f"`{d_str}`", inline=True)
    embed.add_field(name="👟 Movement Speed", value=f"`{s_str}`", inline=True)
    embed.add_field(name="🌱 Auto-Watering", value=f"`{w_str}`", inline=True)
    
    if "upgrade_bonus" in w_effects:
        embed.add_field(name="✨ Upgrade Bonus", value=f"`+{w_effects['upgrade_bonus']}% Success`", inline=True)
    if "lumen_luck" in w_effects:
        embed.add_field(name="🌟 Lumen Luck", value=f"`{w_effects['lumen_luck']}x Multiplier`", inline=True)
    if "exp_mult" in w_effects:
        embed.add_field(name="📈 EXP Multiplier", value=f"`{w_effects['exp_mult']}x (+50%)`", inline=True)
        
    embed.set_footer(text="BMKG Market & Combat Multipliers")
    return embed

def build_forecast_embed():
    data = load_latest_telemetry()
    s_state = get_current_season_state()
    
    now_slot = s_state["slot_index"]
    next_roll_ts = s_state["next_slot_epoch"]
    slot_hours = ["04:00 AM", "08:00 AM", "12:00 PM", "04:00 PM", "08:00 PM", "12:00 AM"]
    
    schedule_lines = []
    for i in range(1, 7):
        is_cur = (i == now_slot)
        prefix = "👉 **[LIVE NOW]**" if is_cur else "▫️"
        h_str = slot_hours[i - 1]
        schedule_lines.append(f"{prefix} **Slot {i}** (`{h_str}` in-game)")
        
    embed = discord.Embed(
        title=f"🕒 2-Hour Weather Roll Schedule • {s_state['season']} Day {s_state['season_day']}",
        description=f"> ⏳ **Next Roll In:** <t:{next_roll_ts}:R> (<t:{next_roll_ts}:t>)\n\n" + "\n".join(schedule_lines),
        color=0x34495E,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text="BMKG Observatory Precision Clock")
    return embed

def build_help_embed():
    embed = discord.Embed(
        title="🛰️ BMKG Portal Observatory • Bot Commands Guide",
        description="Interact with the 24/7 Portal Radar using commands (e.g. `!weather` or `/weather`):",
        color=0x2ECC71
    )
    embed.add_field(name="`!weather` / `/weather`", value="Display current live weather, temperature, and full widescreen anime radar card.", inline=False)
    embed.add_field(name="`!gacha` / `/gacha`", value="Check 24-hour seasonal probability gacha pool percentages for today.", inline=False)
    embed.add_field(name="`!portal` / `/portal`", value="View Dewdrop Portal timer, Lycaros Weekly Boss schedule, and Eclipse mutations.", inline=False)
    embed.add_field(name="`!modifiers` / `/modifiers`", value="Inspect active realm buffs, shop surcharges, speed, and combat modifiers.", inline=False)
    embed.add_field(name="`!forecast` / `/forecast`", value="View upcoming 2-hour roll schedule across the 6 daily slots.", inline=False)
    embed.set_footer(text="BMKG Lazie • Powered by Roblox Observatory Client")
    return embed

WEATHER_CHANNEL_ID = 1540058829356540094

def is_weather_channel(channel) -> bool:
    """Returns True ONLY for the dedicated weather radar channel."""
    if not channel:
        return False
    if getattr(channel, "id", None) == WEATHER_CHANNEL_ID:
        return True
    ch_name = getattr(channel, "name", "").lower()
    # Matches 'weather' or 'cuaca', but excludes 'roles-weather'
    if ch_name in ["weather", "cuaca", "bmkg-weather"] or ("weather" in ch_name and "role" not in ch_name):
        return True
    return False

async def purge_channel_messages(channel, limit: int = 100):
    """Purges prior messages in the channel to leave only the fresh radar intact."""
    try:
        if hasattr(channel, "purge"):
            await channel.purge(limit=limit)
    except Exception as pe:
        # Fallback if bulk purge fails (e.g. older than 14 days or missing Manage Messages permission)
        try:
            async for msg in channel.history(limit=limit):
                try:
                    await msg.delete()
                    await asyncio.sleep(0.2)
                except Exception:
                    pass
        except Exception:
            pass

# ============================================================
# BOT COMMAND HANDLERS (Standard Prefix + Slash)
# ============================================================
@bot.command(name="weather")
async def cmd_prefix_weather(ctx):
    # Only purge messages if used inside the dedicated weather channel
    if is_weather_channel(ctx.channel):
        await purge_channel_messages(ctx.channel)
    embed, f = build_weather_embed_and_file()
    await ctx.send(embed=embed, file=f)

@bot.command(name="gacha")
async def cmd_prefix_gacha(ctx):
    async with ctx.typing():
        embed = build_gacha_embed()
        await ctx.send(embed=embed)

@bot.command(name="portal")
async def cmd_prefix_portal(ctx):
    async with ctx.typing():
        embed = build_portal_embed()
        await ctx.send(embed=embed)

@bot.command(name="modifiers")
async def cmd_prefix_modifiers(ctx):
    async with ctx.typing():
        embed = build_modifiers_embed()
        await ctx.send(embed=embed)

@bot.command(name="forecast")
async def cmd_prefix_forecast(ctx):
    async with ctx.typing():
        embed = build_forecast_embed()
        await ctx.send(embed=embed)

@bot.command(name="help")
async def cmd_prefix_help(ctx):
    embed = build_help_embed()
    await ctx.send(embed=embed)

# Register Slash Commands if discord.py 2.x app_commands is present
if HAS_SLASH_TREE:
    @bot.tree.command(name="weather", description="Check current live weather, temperature, and anime radar card.")
    async def slash_weather(interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Only purge messages if executed inside the dedicated weather channel
        if is_weather_channel(interaction.channel):
            resp_msg_id = None
            try:
                resp_msg = await interaction.original_response()
                if resp_msg:
                    resp_msg_id = resp_msg.id
            except Exception:
                pass

            try:
                async for msg in interaction.channel.history(limit=50):
                    if resp_msg_id and msg.id == resp_msg_id:
                        continue
                    try:
                        await msg.delete()
                        await asyncio.sleep(0.1)
                    except Exception:
                        pass
            except Exception:
                pass
                
        embed, f = build_weather_embed_and_file()
        await interaction.followup.send(embed=embed, file=f)

    @bot.tree.command(name="gacha", description="View today's 24-hour seasonal weather probability gacha pool.")
    async def slash_gacha(interaction: discord.Interaction):
        await interaction.response.defer()
        embed = build_gacha_embed()
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="portal", description="View Dewdrop Portal countdown, Lycaros Boss raid, and Rift mutations.")
    async def slash_portal(interaction: discord.Interaction):
        await interaction.response.defer()
        embed = build_portal_embed()
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="modifiers", description="Inspect active realm buffs, price impacts, and combat modifiers.")
    async def slash_modifiers(interaction: discord.Interaction):
        await interaction.response.defer()
        embed = build_modifiers_embed()
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="forecast", description="Preview 6-slot 2-hour roll schedule for the current seasonal cycle.")
    async def slash_forecast(interaction: discord.Interaction):
        await interaction.response.defer()
        embed = build_forecast_embed()
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="help", description="List all available BMKG weather observatory slash commands.")
    async def slash_help(interaction: discord.Interaction):
        await interaction.response.defer()
        embed = build_help_embed()
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="createroles", description="Auto-create weather roles with matching colors in the server.")
    @app_commands.default_permissions(manage_roles=True)
    async def slash_createroles(interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ This command must be executed inside a Discord server.")
            return

        roles_to_create = [
            ("Northern Lights", discord.Color.from_rgb(0, 255, 180), "Astral Aurora & Upgrade Event"),
            ("Nightmare", discord.Color.from_rgb(180, 20, 35), "Blood Moon Eclipse & Abyssal Hazard"),
            ("Portal Eclipse", discord.Color.from_rgb(160, 60, 240), "Dimensional Rift & Boss Raid"),
            ("Snow", discord.Color.from_rgb(230, 240, 255), "Frost Blizzard & +20% Shop Surcharge"),
            ("Heavy Rain", discord.Color.from_rgb(52, 73, 94), "Severe Downpour & +10% Shop Surcharge"),
            ("Gale", discord.Color.from_rgb(22, 160, 133), "Violent Winds & +10% Shop Surcharge"),
            ("Rain", discord.Color.from_rgb(52, 152, 219), "Downpour & 100% Auto-Water"),
            ("Drizzle", discord.Color.from_rgb(93, 173, 226), "Soft Mist & 50% Auto-Water"),
            ("Windy", discord.Color.from_rgb(26, 188, 156), "Fresh Breeze & Movement Modifier"),
            ("Dry", discord.Color.from_rgb(243, 156, 18), "Sunny Skies & Standard Prices"),
        ]

        created = []
        existing = []
        for r_name, r_color, r_desc in roles_to_create:
            match = discord.utils.get(guild.roles, name=r_name)
            if match:
                existing.append(f"• **{match.name}**: `<@&{match.id}>` (`{match.id}`)")
            else:
                try:
                    new_role = await guild.create_role(
                        name=r_name,
                        color=r_color,
                        mentionable=True,
                        reason="BMKG Portal Observatory Weather Roles"
                    )
                    created.append(f"• **{new_role.name}**: `<@&{new_role.id}>` (`{new_role.id}`)")
                except Exception as e:
                    created.append(f"• Failed to create **{r_name}**: {e}")

        desc = ""
        if created:
            desc += "✅ **Newly Created Roles:**\n" + "\n".join(created) + "\n\n"
        if existing:
            desc += "ℹ️ **Already Existing Roles:**\n" + "\n".join(existing)

        embed = discord.Embed(
            title="🎭 BMKG Weather Roles Sync",
            description=desc or "No roles processed.",
            color=0x2ECC71,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Badan Meteorologi Klimatologi dan Gacha (BMKG)")
        await interaction.followup.send(embed=embed)

@bot.command(name="createroles")
@commands.has_permissions(manage_roles=True)
async def cmd_prefix_createroles(ctx):
    guild = ctx.guild
    if not guild:
        await ctx.send("❌ This command must be executed inside a server.")
        return

    roles_to_create = [
        ("Northern Lights", discord.Color.from_rgb(0, 255, 180)),
        ("Nightmare", discord.Color.from_rgb(180, 20, 35)),
        ("Portal Eclipse", discord.Color.from_rgb(160, 60, 240)),
        ("Snow", discord.Color.from_rgb(230, 240, 255)),
        ("Heavy Rain", discord.Color.from_rgb(52, 73, 94)),
        ("Gale", discord.Color.from_rgb(22, 160, 133)),
        ("Rain", discord.Color.from_rgb(52, 152, 219)),
        ("Drizzle", discord.Color.from_rgb(93, 173, 226)),
        ("Windy", discord.Color.from_rgb(26, 188, 156)),
        ("Dry", discord.Color.from_rgb(243, 156, 18)),
    ]

    results = []
    for r_name, r_color in roles_to_create:
        match = discord.utils.get(guild.roles, name=r_name)
        if match:
            results.append(f"• **{match.name}**: `<@&{match.id}>` (ID: `{match.id}`)")
        else:
            try:
                new_role = await guild.create_role(name=r_name, color=r_color, mentionable=True)
                results.append(f"• ✨ **{new_role.name}**: `<@&{new_role.id}>` (ID: `{new_role.id}`)")
            except Exception as e:
                results.append(f"• ❌ **{r_name}**: {e}")

    embed = discord.Embed(
        title="🎭 BMKG Weather Roles Setup",
        description="\n".join(results),
        color=0x2ECC71
    )
    await ctx.send(embed=embed)

# ============================================================
# REACTION ROLE ENGINE (Auto Add/Remove on Click)
# ============================================================
REACTION_ROLE_MSG_ID = 1557380895680364615
WEATHER_EMOJI_TO_ROLE = {
    '🌌': 1557371108032913521, # Northern Lights
    '🩸': 1557371110193106954, # Nightmare
    '🌀': 1557371112357367849, # Portal Eclipse
    '❄️': 1557371115024941056, # Snow
    '⛈️': 1557371120422883411, # Heavy Rain
    '🌪️': 1557371122318708857, # Gale
    '🌧️': 1557371124222787594, # Rain
    '🌦️': 1557371125971820554, # Drizzle
    '🍃': 1557371127326572579, # Windy
    '☀️': 1557371128920547460, # Dry
}

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.message_id != REACTION_ROLE_MSG_ID:
        return
    if payload.user_id == bot.user.id:
        return

    emoji_str = str(payload.emoji.name)
    role_id = WEATHER_EMOJI_TO_ROLE.get(emoji_str)
    if not role_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role = guild.get_role(role_id)
    member = payload.member or guild.get_member(payload.user_id)
    if role and member:
        try:
            await member.add_roles(role, reason="BMKG Reaction Role Added")
            print(f"[Role +] Added {role.name} to {member.display_name}")
        except Exception as e:
            print(f"[Role Error] Could not add role {role.name}: {e}")

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.message_id != REACTION_ROLE_MSG_ID:
        return

    emoji_str = str(payload.emoji.name)
    role_id = WEATHER_EMOJI_TO_ROLE.get(emoji_str)
    if not role_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role = guild.get_role(role_id)
    member = guild.get_member(payload.user_id)
    if not member:
        try:
            member = await guild.fetch_member(payload.user_id)
        except Exception:
            member = None

    if role and member:
        try:
            await member.remove_roles(role, reason="BMKG Reaction Role Removed")
            print(f"[Role -] Removed {role.name} from {member.display_name}")
        except Exception as e:
            print(f"[Role Error] Could not remove role {role.name}: {e}")

@bot.event
async def on_ready():
    print(f"[BMKG Bot] Logged in as {bot.user} (ID: {bot.user.id})")
    if HAS_SLASH_TREE:
        try:
            synced = await bot.tree.sync()
            print(f"[BMKG Bot] Synced {len(synced)} slash commands globally!")
        except Exception as e:
            print(f"[BMKG Bot] Slash sync error: {e}")

def run_discord_bot():
    token = get_bot_token() or DISCORD_BOT_TOKEN
    if not token:
        print("[BMKG Bot] ⚠️ DISCORD_BOT token not provided in environment.")
        return
    print(f"[BMKG Bot] Connecting to Discord Gateway with token ({token[:6]}...)...")
    bot.run(token)

if __name__ == "__main__":
    run_discord_bot()
