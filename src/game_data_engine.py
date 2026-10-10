"""
BMKG Game Data & Mechanics Engine
Reconstructs exact The Portal mechanics from scraped game data files:
- Seasonal Probabilities
- Weather Effects (Price, Speed, Damage, AutoWater, Mining, EXP, Luck)
- Lycaros Weekly Boss Timers
- Dewdrop Portal Schedule
- In-Game Diurnal Clocks
"""

import json
import os
import time
import math
from typing import Dict, Any, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "bmkg_gamedata")

WEATHER_DISPLAY_NAMES = {
    "Dry": "Dry • Clear Sky ☀️",
    "Rain": "Rain • Gentle Downpour 🌧️",
    "NormalRain": "Rain • Gentle Downpour 🌧️",
    "HeavyRain": "Heavy Rain • Storm ⛈️",
    "Windy": "Windy • Fresh Breeze 🍃",
    "Drizzle": "Drizzle • Soft Mist 🌦️",
    "Gale": "Gale • Violent Winds 🌪️",
    "Snow": "Snow • Frost Blizzard ❄️",
    "NorthernLights": "Northern Lights • Astral Aurora 🌌",
    "Nightmare": "Nightmare • Blood Moon Eclipse 🩸",
    "PortalEclipse": "Portal Eclipse • Dimensional Rift 🌀",
    "Void": "Void • Timeless Abyss 🌌"
}

WEATHER_COLORS = {
    "Dry": 0xF39C12,
    "Rain": 0x3498DB,
    "NormalRain": 0x3498DB,
    "HeavyRain": 0x2C3E50,
    "Windy": 0x1ABC9C,
    "Drizzle": 0x5DADE2,
    "Gale": 0x16A085,
    "Snow": 0xECF0F1,
    "NorthernLights": 0x00FFB4,
    "Nightmare": 0x960018,
    "PortalEclipse": 0x8E44AD,
    "Void": 0x1F1F1F
}

WEATHER_EFFECTS = {
    "Dry": {
        "price": 1.0, "damage": 1.0, "speed": 1.0, "autowater": 0.0,
        "notes": "Standard realm prices, normal combat conditions."
    },
    "Drizzle": {
        "price": 1.05, "damage": 1.0, "speed": 1.0, "autowater": 0.5,
        "notes": "Shop prices +5%, 50% Auto-Water across crops."
    },
    "NormalRain": {
        "price": 1.05, "damage": 0.95, "speed": 0.95, "autowater": 1.0,
        "notes": "Shop +5%, Damage -5%, Speed -5%, 100% Auto-Water crops."
    },
    "Rain": {
        "price": 1.05, "damage": 0.95, "speed": 0.95, "autowater": 1.0,
        "notes": "Shop +5%, Damage -5%, Speed -5%, 100% Auto-Water crops."
    },
    "HeavyRain": {
        "price": 1.10, "damage": 0.90, "speed": 0.90, "autowater": 1.0,
        "notes": "Shop +10% Surcharge, Combat -10%, Speed -10%, 100% Auto-Water."
    },
    "Windy": {
        "price": 1.05, "damage": 0.95, "speed": 0.95, "autowater": 0.0,
        "notes": "Shop +5%, Damage -5%, Movement Speed -5%."
    },
    "Gale": {
        "price": 1.10, "damage": 0.90, "speed": 0.90, "autowater": 0.0,
        "notes": "Shop +10% Surcharge, Combat -10%, Movement Speed -10%."
    },
    "Snow": {
        "price": 1.20, "damage": 0.90, "speed": 0.90, "autowater": 0.0,
        "notes": "Shop +20% Severe Surcharge! Damage -10%, Speed -10%."
    },
    "NorthernLights": {
        "price": 1.0, "damage": 1.0, "speed": 1.0, "autowater": 0.0,
        "upgrade_bonus": 10, "lumen_luck": 2.0,
        "notes": "✨ Equipment Upgrade Success +10%, Lumen Luck 2.0x, Normal Shop prices!"
    },
    "Nightmare": {
        "price": 1.0, "damage": 1.0, "speed": 1.0, "autowater": 0.0,
        "mining_speed": 10, "mineral_chance": 10, "exp_mult": 1.5, "drop_luck": 1.5,
        "notes": "🩸 EXP +50%, Monster Drops +50%, Mining Speed +10%, Ghost Mutations (3.7x)!"
    },
    "PortalEclipse": {
        "price": 1.0, "damage": 1.10, "speed": 1.10, "autowater": 0.0,
        "exp_mult": 1.5, "drop_luck": 1.5,
        "notes": "🌀 Damage +10%, Speed +10%, EXP +50%, Drops +50%, Shadow Mutations (2.65x), 100% Universal Fish Biting!"
    }
}

SEASONAL_ODDS = {
    "Summer": {
        1: [("Dry", 48), ("NormalRain", 14), ("HeavyRain", 10), ("Windy", 9), ("Drizzle", 16), ("Gale", 3), ("NorthernLights", 10), ("Nightmare", 10)],
        2: [("Dry", 42), ("HeavyRain", 18), ("NormalRain", 14), ("Windy", 13), ("Drizzle", 8), ("Gale", 5), ("NorthernLights", 10), ("Nightmare", 10)],
        3: [("Dry", 40), ("HeavyRain", 22), ("Windy", 14), ("NormalRain", 13), ("Drizzle", 6), ("Gale", 5), ("NorthernLights", 10), ("Nightmare", 10)],
        4: [("Dry", 38), ("NormalRain", 20), ("HeavyRain", 16), ("Windy", 13), ("Drizzle", 8), ("Gale", 5), ("NorthernLights", 10), ("Nightmare", 10)]
    },
    "Autumn": {
        1: [("NormalRain", 34), ("Dry", 24), ("Drizzle", 16), ("HeavyRain", 14), ("Windy", 9), ("Gale", 3), ("NorthernLights", 10), ("Nightmare", 10)],
        2: [("NormalRain", 32), ("HeavyRain", 20), ("Drizzle", 16), ("Dry", 14), ("Windy", 13), ("Gale", 5), ("NorthernLights", 10), ("Nightmare", 10)],
        3: [("HeavyRain", 28), ("NormalRain", 26), ("Windy", 14), ("Drizzle", 14), ("Dry", 8), ("Gale", 8), ("NorthernLights", 10), ("Nightmare", 10)],
        4: [("NormalRain", 30), ("HeavyRain", 22), ("Drizzle", 14), ("Windy", 12), ("Dry", 10), ("Gale", 6), ("NorthernLights", 10), ("Nightmare", 10)]
    },
    "Winter": {
        1: [("Snow", 30), ("NormalRain", 24), ("Dry", 18), ("Windy", 11), ("Drizzle", 8), ("HeavyRain", 6), ("Gale", 3), ("NorthernLights", 10), ("Nightmare", 10)],
        2: [("Snow", 55), ("Dry", 14), ("Windy", 11), ("NormalRain", 8), ("Gale", 5), ("Drizzle", 4), ("HeavyRain", 3), ("NorthernLights", 10), ("Nightmare", 10)],
        3: [("Snow", 62), ("Dry", 12), ("Windy", 9), ("NormalRain", 6), ("Gale", 5), ("Drizzle", 4), ("HeavyRain", 2), ("NorthernLights", 10), ("Nightmare", 10)],
        4: [("Snow", 42), ("Dry", 16), ("Drizzle", 16), ("NormalRain", 10), ("Windy", 9), ("Gale", 4), ("HeavyRain", 3), ("NorthernLights", 10), ("Nightmare", 10)]
    },
    "Spring": {
        1: [("Drizzle", 38), ("NormalRain", 20), ("Windy", 18), ("Dry", 10), ("HeavyRain", 6), ("Gale", 4), ("Snow", 4), ("NorthernLights", 10), ("Nightmare", 10)],
        2: [("Drizzle", 34), ("NormalRain", 25), ("Dry", 15), ("Windy", 14), ("HeavyRain", 8), ("Gale", 4), ("Snow", 0), ("NorthernLights", 10), ("Nightmare", 10)],
        3: [("NormalRain", 30), ("Drizzle", 26), ("Dry", 22), ("HeavyRain", 10), ("Windy", 9), ("Gale", 3), ("Snow", 0), ("NorthernLights", 10), ("Nightmare", 10)],
        4: [("Dry", 35), ("Drizzle", 22), ("NormalRain", 20), ("Windy", 12), ("HeavyRain", 8), ("Gale", 3), ("Snow", 0), ("NorthernLights", 10), ("Nightmare", 10)]
    }
}

SEASON_EPOCH_UNIX = 1785542400 # Scraped from Constants.Season.EpochUnix
TOTAL_YEAR_CYCLE_SECONDS = 691200 # 8 Real Days
WEATHER_SLOT_SECONDS = 7200 # 2 Real Hours per weather slot
REAL_SECONDS_PER_DAY = 43200 # 12 Real Hours per season day (6 slots * 7200s)

def get_current_season_state(epoch_time: float = None) -> Dict[str, Any]:
    """Calculates active season, season day (1-4), and cycle position using exact Roblox Constants."""
    if epoch_time is None:
        epoch_time = time.time()
    
    elapsed = (epoch_time - SEASON_EPOCH_UNIX) % TOTAL_YEAR_CYCLE_SECONDS
    if elapsed < 0:
        elapsed += TOTAL_YEAR_CYCLE_SECONDS
    pos = elapsed / float(TOTAL_YEAR_CYCLE_SECONDS)
    
    # 4 seasons: Spring (0.00-0.25), Summer (0.25-0.50), Autumn (0.50-0.75), Winter (0.75-1.00)
    seasons = ["Spring", "Summer", "Autumn", "Winter"]
    s_idx = int(pos * 4) % 4
    season_name = seasons[s_idx]
    
    fraction_in_season = (pos * 4) - s_idx
    season_day = int(fraction_in_season * 4) + 1
    season_day = max(1, min(4, season_day))
    
    # Weather slot index in daily cycle (6 slots of 2 hours)
    day_fraction = (fraction_in_season * 4) - (season_day - 1)
    slot_index = int(day_fraction * 6) + 1
    slot_index = max(1, min(6, slot_index))
    
    # Calculate seconds remaining in active 2-hour slot
    slot_sec = int(elapsed) % WEATHER_SLOT_SECONDS
    rem_in_slot = WEATHER_SLOT_SECONDS - slot_sec
    
    return {
        "season": season_name,
        "season_day": season_day,
        "slot_index": slot_index,
        "cycle_pos": pos,
        "seconds_remaining_in_slot": rem_in_slot,
        "next_slot_epoch": int(epoch_time + rem_in_slot)
    }

def get_seasonal_odds(season: str, day: int) -> List[Tuple[str, int]]:
    """Returns probability tuples sorted by highest percentage."""
    pool = SEASONAL_ODDS.get(season, {}).get(day, SEASONAL_ODDS["Summer"][1])
    return sorted(pool, key=lambda x: x[1], reverse=True)

def get_next_weekly_boss_schedule() -> Dict[str, Any]:
    """
    Scraped WeeklyBoss.Schedule.FixedWeekly:
    Lycaros arrives every Sunday at 04:00 AM and 04:00 PM GMT+7.
    """
    now = time.time()
    # In GMT+7
    offset = 7 * 3600
    local_now = now + offset
    day_sec = int(local_now) % 86400
    # Day of week: Monday=0 ... Sunday=6
    day_of_week = int(local_now // 86400 + 3) % 7 # Unix epoch 1970-01-01 was Thursday (3)
    
    # Sunday is index 6
    days_until_sunday = (6 - day_of_week) % 7
    if days_until_sunday == 0:
        # Check if 04:00 AM (14400s) or 16:00 PM (57600s) have passed
        if day_sec < 14400:
            target_sec = 14400 - day_sec
        elif day_sec < 57600:
            target_sec = 57600 - day_sec
        else:
            target_sec = (7 * 86400) + 14400 - day_sec
    else:
        target_sec = (days_until_sunday * 86400) + 14400 - day_sec
        
    target_epoch = int(now + target_sec)
    
    hours = target_sec // 3600
    mins = (target_sec % 3600) // 60
    
    return {
        "target_epoch": target_epoch,
        "remaining_seconds": target_sec,
        "time_str": f"{hours}h {mins}m",
        "description": "Lycaros arrives every Sunday at 04:00 AM & 04:00 PM (GMT+7)"
    }
