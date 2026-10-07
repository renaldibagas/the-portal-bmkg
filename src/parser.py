import re
from typing import Dict, List, Optional, Any

class WeatherData:
    def __init__(
        self,
        season: str = "Unknown",
        weather: str = "Unknown",
        portal_info: Optional[str] = None,
        portal_location: Optional[str] = None,
        portal_minutes_remaining: Optional[float] = None,
        in_game_time: Optional[str] = None,
        modifiers: Optional[List[str]] = None,
        raw_text: str = ""
    ):
        self.season = season
        self.weather = weather
        self.portal_info = portal_info
        self.portal_location = portal_location
        self.portal_minutes_remaining = portal_minutes_remaining
        self.in_game_time = in_game_time
        self.modifiers = modifiers or []
        self.raw_text = raw_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "season": self.season,
            "weather": self.weather,
            "portal_info": self.portal_info,
            "portal_location": self.portal_location,
            "portal_minutes_remaining": self.portal_minutes_remaining,
            "in_game_time": self.in_game_time,
            "modifiers": self.modifiers,
            "raw_text": self.raw_text
        }

    def is_valid(self) -> bool:
        if self.season == "Unknown" and self.weather == "Unknown":
            return False
        return True

    def get_weather_signature(self) -> str:
        return f"{self.season}|{self.weather}|{','.join(self.modifiers)}"

    def __repr__(self) -> str:
        return (
            f"<WeatherData Season='{self.season}', Weather='{self.weather}', "
            f"Portal='{self.portal_info}' ({self.portal_minutes_remaining}m), Modifiers={len(self.modifiers)}>"
        )


SEASONS = ["Spring", "Summer", "Autumn", "Fall", "Winter"]

KNOWN_WEATHERS = [
    "Portal Eclipse", "Solar Eclipse", "Lunar Eclipse", "Eclipse",
    "Blood Moon", "Starfall", "Aurora", "Rainbow",
    "Heavy Rain", "Rain", "Light Rain", "Drizzle",
    "Thunderstorm", "Storm", "Lightning Storm", "Thunder",
    "Sunny", "Clear", "Cloudy", "Overcast", "Fog", "Foggy",
    "Snow", "Blizzard", "Hail", "Windy", "Heatwave", "Acid Rain"
]

LEADERBOARD_KEYWORDS = [
    "people", "likes", "job", "cleric", "enchanter",
    "defender", "warrior", "lv 30", "lv 29", "lv ", "level"
]

# UI & Background Pet Noise Filter
FILTER_KEYWORDS = [
    "event", "ten", "wen", "hen", "en", "likes", "cleric", "job", "people",
    "portal", "season", "weather", "punk", "rooster", "ram", "grandpa",
    "bandit", "cow", "chick", "pet", "lv", "level", "player"
]

def is_leaderboard_blocking(raw_text: str) -> bool:
    text_lower = raw_text.lower()
    for kw in LEADERBOARD_KEYWORDS:
        if kw in text_lower:
            return True
    return False

def parse_weather_text(raw_text: str) -> WeatherData:
    """
    Parses the OCR text output from the Roblox weather tooltip popup.
    """
    clean_text = raw_text.replace("\r", " ").replace("\n", " ")
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # 1. Season detection
    season = "Unknown"
    for s in SEASONS:
        if re.search(rf"\b{s}\b", clean_text, re.IGNORECASE):
            season = "Autumn" if s.lower() == "fall" else s.capitalize()
            break

    # 2. Portal Event & Timer detection
    portal_info = None
    portal_location = None
    portal_minutes_remaining = None

    portal_match = re.search(
        r"(Portal\s+(?:Open\s+in|Opens?\s+in|Active\s+in|in)\s+([A-Za-z]{3,15})\s+(\d{1,2}:\d{2}(?::\d{2})?))",
        clean_text,
        re.IGNORECASE
    )
    if portal_match:
        portal_info = portal_match.group(1).strip()
        portal_location = portal_match.group(2).capitalize()
        time_str = portal_match.group(3)
        if time_str:
            parts = [int(p) for p in time_str.split(":")]
            if len(parts) == 2:
                portal_minutes_remaining = float(parts[0] * 60 + parts[1])
            elif len(parts) == 3:
                portal_minutes_remaining = float(parts[0] * 60 + parts[1] + parts[2] / 60.0)
    else:
        active_match = re.search(
            r"(Portal\s+(?:is\s+)?Active\s+in\s+([A-Za-z]{3,15}))",
            clean_text,
            re.IGNORECASE
        )
        if active_match:
            portal_info = active_match.group(1).strip()
            portal_location = active_match.group(2).capitalize()
            portal_minutes_remaining = 0.0

    # 3. Weather detection
    weather = "Unknown"
    for w in sorted(KNOWN_WEATHERS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(w)}\b", clean_text, re.IGNORECASE):
            weather = w
            break

    if weather == "Unknown" and season != "Unknown" and portal_info:
        season_idx = clean_text.lower().find(season.lower())
        portal_idx = clean_text.lower().find(portal_info.lower())
        if season_idx != -1 and portal_idx != -1 and portal_idx > season_idx:
            between = clean_text[season_idx + len(season):portal_idx].strip()
            between = re.sub(r"\bEvent\b", "", between, flags=re.IGNORECASE).strip()
            if 3 <= len(between) <= 25 and not re.search(r"\d", between):
                weather = between

    # 4. In-Game Clock detection
    in_game_time = None
    clock_match = re.search(r"\b(\d{1,2}:\d{2}\s*(?:AM|PM))\b", clean_text, re.IGNORECASE)
    if clock_match:
        in_game_time = clock_match.group(1).upper()

    # 5. Modifiers extraction
    modifiers = []
    if season != "Unknown" or weather != "Unknown":
        if portal_info and portal_info in clean_text:
            p_end = clean_text.find(portal_info) + len(portal_info)
            mod_text = clean_text[p_end:].strip()
        else:
            mod_text = clean_text
            if season != "Unknown":
                mod_text = re.sub(rf"\b{season}\b", "", mod_text, flags=re.IGNORECASE)
            if weather != "Unknown":
                mod_text = re.sub(rf"\b{re.escape(weather)}\b", "", mod_text, flags=re.IGNORECASE)

        # Normalize OCR typos in percentages
        mod_text_clean = re.sub(r"500/0|500%|50o/o", "50%", mod_text)
        mod_text_clean = re.sub(r"100/0|10o/o", "10%", mod_text_clean)
        mod_text_clean = re.sub(r"([+\-]\s*\d+)0*(?:/0|o/o)", r"\1%", mod_text_clean)
        mod_text_clean = re.sub(r"\+{2,}", "+", mod_text_clean)

        pct_pattern = re.compile(r"([A-Za-z\s]+?)\s*([+\-]\s*\d+\s*%?)")
        matches = list(pct_pattern.finditer(mod_text_clean))
        matched_spans = []

        for m in matches:
            name = m.group(1).strip()
            val = m.group(2).replace(" ", "").strip()
            if not val.endswith("%"):
                val += "%"
            val = re.sub(r"\+{2,}", "+", val)
            words = [w for w in name.split() if len(w) > 1 or w.lower() in ("to", "of", "in")]
            clean_name = " ".join(words).strip()
            
            # Check if name contains any background pet / noise keywords
            name_words = [w.lower() for w in clean_name.split()]
            if len(clean_name) >= 2 and not any(kw in name_words for kw in FILTER_KEYWORDS):
                modifiers.append(f"{clean_name} {val}")
                matched_spans.append((m.start(), m.end()))

        # Non-percentage modifiers (e.g. 'All Fish Biting')
        non_pct_text = mod_text_clean
        for start, end in reversed(matched_spans):
            non_pct_text = non_pct_text[:start] + " | " + non_pct_text[end:]

        for chunk in non_pct_text.split("|"):
            clean_chunk = chunk.strip()
            clean_chunk = re.sub(r"\b(Event|en|ten|wen|hen)\b", "", clean_chunk, flags=re.IGNORECASE).strip()
            chunk_words = [w.lower() for w in clean_chunk.split()]
            if (
                len(clean_chunk) >= 4 and
                not re.search(r"^\d", clean_chunk) and
                not any(kw in chunk_words for kw in FILTER_KEYWORDS)
            ):
                modifiers.append(clean_chunk)

    return WeatherData(
        season=season,
        weather=weather,
        portal_info=portal_info,
        portal_location=portal_location,
        portal_minutes_remaining=portal_minutes_remaining,
        in_game_time=in_game_time,
        modifiers=modifiers,
        raw_text=raw_text
    )
