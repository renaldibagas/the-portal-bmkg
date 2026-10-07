import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

class WeatherCardGenerator:
    def __init__(self, width: int = 1080, height: int = 1680, bg_dir: str = None):
        self.width = width
        self.height = height
        if bg_dir is None:
            # Look in local project assets/backgrounds
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.bg_dir = os.path.join(base_dir, "assets", "backgrounds")
        else:
            self.bg_dir = bg_dir
        self._load_fonts()

    def _get_anime_background(self, weather_key: str, is_day: bool, carousel_idx: int = None, time_of_day: str = None) -> Image.Image:
        """
        Picks and scales an anime landscape wallpaper corresponding to the weather type AND time of day:
        - 'day': Bright morning/midday azure skies, sunlit meadows, crisp greenery
        - 'afternoon' / 'sunset': Warm golden hour, orange twilight, nostalgic Makoto Shinkai dusk
        - 'night': Starlit starry skies, tranquil moonlight, lo-fi nocturnal atmosphere
        Supports 5 nostalgic backgrounds per weather & time slot, rotating as a carousel on roll changes.
        """
        if not os.path.exists(self.bg_dir):
            return None

        w = weather_key.lower()

        # Resolve time of day if not explicitly passed
        if not time_of_day:
            time_of_day = "day" if is_day else "night"
        tod = time_of_day.lower()

        mapping = {
            "northernlights": [f"northernlights_{i}.jpg" if i != 4 else f"northernlights_{i}.png" for i in range(1, 6)],
            "nightmare": ["nightmare_1.jpg", "nightmare_2.jpg", "nightmare_3.png", "nightmare_4.jpg", "nightmare_5.jpg"],
            "portaleclipse": ["portaleclipse_1.jpg", "portaleclipse_2.jpg", "portaleclipse_3.png", "portaleclipse_4.jpg", "portaleclipse_5.png"],
            "snow": ["snow_1.png", "snow_2.jpg", "snow_3.jpg", "snow_4.png", "snow_5.png"],
            "heavyrain": ["heavyrain_1.png", "heavyrain_2.png", "heavyrain_3.png", "heavyrain_4.jpg", "heavyrain_5.jpg"],
            "rain": ["rain_1.png", "rain_2.jpg", "rain_3.png", "rain_4.jpg", "rain_5.png"],
            "drizzle": ["drizzle_1.png", "drizzle_2.jpg", "drizzle_3.png", "drizzle_4.png", "drizzle_5.png"],
            "gale": ["gale_1.png", "gale_2.png", "gale_3.jpg", "gale_4.png", "gale_5.png"],
            "windy": ["windy_1.jpg", "windy_2.jpg", "windy_3.png", "windy_4.png", "windy_5.jpg"],
            "dry": ["dry_1.jpg", "dry_2.png", "dry_3.png", "dry_4.png", "dry_5.png"],
            "afternoon": ["afternoon_1.png", "afternoon_2.png", "afternoon_3.jpg", "afternoon_4.jpg", "afternoon_5.png"],
            "night": ["night_1.jpg", "night_2.jpg", "night_3.png", "night_4.jpg", "night_5.png"],
        }

        # Time-based overrides for clear / general weather (Dry, Windy)
        matched_pool = None
        if "northern" in w:
            matched_pool = mapping["northernlights"]
        elif "nightmare" in w or "blood" in w:
            matched_pool = mapping["nightmare"]
        elif "eclipse" in w or "portal" in w:
            matched_pool = mapping["portaleclipse"]
        elif "snow" in w or "blizzard" in w:
            matched_pool = mapping["snow"]
        elif "heavy" in w:
            matched_pool = mapping["heavyrain"]
        elif "rain" in w:
            matched_pool = mapping["rain"]
        elif "drizzle" in w:
            matched_pool = mapping["drizzle"]
        elif "gale" in w:
            matched_pool = mapping["gale"]
        elif any(tod_k in tod for tod_k in ["afternoon", "sunset", "dusk", "evening"]):
            # Golden hour / Sunset for Dry or Windy weathers
            matched_pool = mapping["afternoon"]
        elif any(tod_k in tod for tod_k in ["night", "midnight"]) or not is_day:
            matched_pool = mapping["night"]
        elif "wind" in w:
            matched_pool = mapping["windy"]
        else:
            matched_pool = mapping["dry"]

        # Filter only existing files on disk
        valid_paths = [os.path.join(self.bg_dir, f) for f in matched_pool if os.path.exists(os.path.join(self.bg_dir, f))]
        if not valid_paths:
            return None

        # Carousel indexing: Rotate sequentially if carousel_idx is provided, otherwise random choice
        if carousel_idx is not None:
            chosen_file = valid_paths[carousel_idx % len(valid_paths)]
        else:
            chosen_file = random.choice(valid_paths)

        try:
            bg_img = Image.open(chosen_file).convert("RGBA")
            # Aspect fill crop to self.width x self.height
            bw, bh = bg_img.size
            scale = max(self.width / float(bw), self.height / float(bh))
            nw = int(bw * scale)
            nh = int(bh * scale)
            bg_resized = bg_img.resize((nw, nh), Image.LANCZOS)
            
            # Center crop
            left = (nw - self.width) // 2
            top = (nh - self.height) // 2
            bg_cropped = bg_resized.crop((left, top, left + self.width, top + self.height))
            return bg_cropped
        except Exception as e:
            return None

    def _load_fonts(self):
        font_paths = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        bold_paths = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/tahomabd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        light_paths = [
            "C:/Windows/Fonts/segoeuil.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]

        def get_font(paths, size):
            for p in paths:
                if os.path.exists(p):
                    try:
                        return ImageFont.truetype(p, size)
                    except Exception:
                        pass
            return ImageFont.load_default()

        self.font_hero_temp = get_font(light_paths, 108)
        self.font_hero_cond = get_font(bold_paths, 36)
        self.font_hero_sub  = get_font(font_paths, 22)
        self.font_title     = get_font(bold_paths, 26)
        self.font_body      = get_font(font_paths, 20)
        self.font_body_bold = get_font(bold_paths, 20)
        self.font_chip      = get_font(bold_paths, 17)
        self.font_small     = get_font(font_paths, 16)
        self.font_small_bold= get_font(bold_paths, 16)
        self.font_pill_time = get_font(bold_paths, 18)
        self.font_pill_temp = get_font(bold_paths, 24)

    def _draw_gradient(self, draw: ImageDraw.ImageDraw, color_top, color_bottom):
        for y in range(self.height):
            ratio = y / float(self.height)
            r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
            g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
            b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

    def _draw_fluffy_clouds(self, base_img: Image.Image, is_day: bool):
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cloud_col = (255, 255, 255, 45) if is_day else (200, 215, 255, 25)
        
        clusters = [
            (200, 180, 140, 70),
            (310, 160, 120, 60),
            (820, 210, 160, 80),
            (930, 230, 130, 65),
            (110, 360, 150, 75),
            (950, 340, 150, 70),
        ]
        for cx, cy, rx, ry in clusters:
            draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=cloud_col)
            draw.ellipse([cx - rx * 0.6, cy - ry * 1.2, cx + rx * 0.6, cy + ry * 0.4], fill=cloud_col)
            
        overlay = overlay.filter(ImageFilter.GaussianBlur(16))
        base_img.alpha_composite(overlay)

    def _draw_aurora_curtains(self, base_img: Image.Image):
        """Draws glowing Northern Lights / Aurora streamers in the upper atmosphere"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Emerald Green & Violet Aurora Waves
        for i in range(5):
            pts_green = []
            pts_violet = []
            base_y = 100 + i * 40
            for x in range(0, self.width + 40, 20):
                wave = math.sin((x + i * 80) * 0.008) * 45 + math.cos(x * 0.015) * 20
                pts_green.append((x, base_y + wave))
                pts_violet.append((x, base_y + wave - 35))
            
            draw.line(pts_green, fill=(0, 245, 175, 45), width=35)
            draw.line(pts_violet, fill=(185, 95, 255, 30), width=30)
            
        overlay = overlay.filter(ImageFilter.GaussianBlur(24))
        base_img.alpha_composite(overlay)

    def _draw_blood_mist(self, base_img: Image.Image):
        """Draws eerie crimson horror mist for Nightmare weather"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for i in range(4):
            cx = 200 + i * 240
            cy = 160 + (i % 2) * 80
            draw.ellipse([cx - 260, cy - 120, cx + 260, cy + 120], fill=(160, 20, 35, 40))
        overlay = overlay.filter(ImageFilter.GaussianBlur(32))
        base_img.alpha_composite(overlay)

    def _draw_cosmic_rift(self, base_img: Image.Image):
        """Draws cosmic purple celestial eclipse glow"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cx = self.width // 2
        cy = 190
        for r in range(180, 40, -25):
            alpha = int(45 * (1.0 - (r / 180.0)))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(175, 65, 255, alpha))
        overlay = overlay.filter(ImageFilter.GaussianBlur(28))
        base_img.alpha_composite(overlay)

    def _draw_rain_streaks(self, base_img: Image.Image, is_heavy: bool = False):
        """Draws dynamic angled rain streaks and splashes"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        random.seed(42)
        count = 180 if is_heavy else 90
        length = 32 if is_heavy else 18
        alpha = 85 if is_heavy else 50
        angle_dx = -6 if is_heavy else -3
        for _ in range(count):
            rx = random.randint(0, self.width + 100)
            ry = random.randint(30, int(self.height * 0.58))
            draw.line([(rx, ry), (rx + angle_dx, ry + length)], fill=(160, 215, 255, alpha), width=2 if is_heavy else 1)
        base_img.alpha_composite(overlay)

    def _draw_snow_fall(self, base_img: Image.Image):
        """Draws drifting frosty snowflakes and ice crystals"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        random.seed(77)
        for _ in range(120):
            sx = random.randint(10, self.width - 10)
            sy = random.randint(20, int(self.height * 0.60))
            sz = random.choice([2, 3, 4, 5])
            draw.ellipse([sx, sy, sx + sz, sy + sz], fill=(230, 245, 255, random.randint(80, 180)))
        overlay = overlay.filter(ImageFilter.GaussianBlur(1))
        base_img.alpha_composite(overlay)

    def _draw_wind_swirls(self, base_img: Image.Image, is_gale: bool = False):
        """Draws dynamic streaming wind ribbons across the sky"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        swirl_count = 5 if is_gale else 3
        alpha = 55 if is_gale else 35
        for s in range(swirl_count):
            pts = []
            base_y = 120 + s * 65
            for x in range(0, self.width + 40, 25):
                wy = base_y + math.sin((x + s * 120) * 0.01) * (35 if is_gale else 20)
                pts.append((x, wy))
            draw.line(pts, fill=(200, 245, 255, alpha), width=4 if is_gale else 2)
        overlay = overlay.filter(ImageFilter.GaussianBlur(4))
        base_img.alpha_composite(overlay)

    def _draw_sun_flare(self, base_img: Image.Image):
        """Draws radiant golden sunburst glow for Dry heatwave"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cx = self.width // 2
        cy = 190
        for r in range(240, 60, -30):
            alpha = int(35 * (1.0 - (r / 240.0)))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 205, 70, alpha))
        overlay = overlay.filter(ImageFilter.GaussianBlur(30))
        base_img.alpha_composite(overlay)

    def _draw_starry_sky(self, draw: ImageDraw.ImageDraw, count: int = 160):
        random.seed(101)
        for _ in range(count):
            x = random.randint(15, self.width - 15)
            y = random.randint(15, int(self.height * 0.50))
            brightness = random.randint(180, 255)
            size = random.choice([1, 1, 1, 2, 2, 3])
            alpha = random.randint(120, 255)
            draw.ellipse([x, y, x + size, y + size], fill=(brightness, brightness, 255, alpha))

    def _draw_glass_card(self, base_img: Image.Image, x0: int, y0: int, x1: int, y1: int, 
                         radius: int = 28, fill_color=(18, 26, 46, 175), border_color=(255, 255, 255, 45)):
        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill_color, outline=border_color, width=2)
        base_img.alpha_composite(overlay)

    def _draw_buff_chip(self, base_img: Image.Image, draw: ImageDraw.ImageDraw, x0: int, y0: int, label: str, buff_type: str = "neutral"):
        """
        Draws a crisp colored status chip:
        - 'positive': Green background + Green text (#00E676)
        - 'negative': Red background + Red text (#FF5252)
        - 'neutral': Soft blue background + White text
        """
        # Calculate text width
        try:
            bbox = self.font_chip.getbbox(label)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except Exception:
            tw = len(label) * 9
            th = 18

        chip_w = tw + 24
        chip_h = 34
        x1 = x0 + chip_w
        y1 = y0 + chip_h

        if buff_type == "positive":
            fill_col = (0, 180, 90, 50)
            border_col = (0, 230, 120, 180)
            text_col = (50, 255, 145, 255)
            dot_col = (0, 255, 130, 255)
        elif buff_type == "negative":
            fill_col = (200, 40, 40, 55)
            border_col = (255, 80, 80, 190)
            text_col = (255, 95, 95, 255)
            dot_col = (255, 70, 70, 255)
        else:
            fill_col = (45, 65, 105, 55)
            border_col = (130, 170, 235, 130)
            text_col = (215, 235, 255, 235)
            dot_col = (160, 200, 255, 255)

        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=fill_col, outline=border_col, width=1)
        base_img.alpha_composite(overlay)

        # Indicator dot
        draw.ellipse([x0 + 8, y0 + 13, x0 + 16, y0 + 21], fill=dot_col)
        # Label text
        draw.text((x0 + 22, y0 + 7), label, font=self.font_chip, fill=text_col)

        return x1 + 10 # return next x coordinate

    def _draw_weather_icon(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, wtype: str, size: int = 32):
        """
        Draws crisp vector weather iconography including Northern Lights and Nightmare.
        """
        r = size // 2
        w = wtype.lower()

        if "northern" in w or "aurora" in w:
            # Northern Lights: Shimmering Teal/Blue/Purple Aurora Curtains with Stars
            pts_1 = [(cx - r, cy + 6), (cx - r//2, cy - 8), (cx, cy + 2), (cx + r//2, cy - 6), (cx + r, cy + 4)]
            draw.line(pts_1, fill=(0, 240, 210, 255), width=4)
            pts_2 = [(cx - r + 3, cy), (cx - r//3, cy - 11), (cx + r//3, cy), (cx + r, cy - 8)]
            draw.line(pts_2, fill=(60, 130, 255, 255), width=3)
            # Sparkle Stars
            draw.ellipse([cx - 7, cy - 10, cx - 3, cy - 6], fill=(255, 255, 255, 255))
            draw.ellipse([cx + 6, cy + 6, cx + 10, cy + 10], fill=(140, 240, 255, 255))
            draw.ellipse([cx + 8, cy - 8, cx + 11, cy - 5], fill=(255, 255, 255, 255))

        elif "nightmare" in w or "blood" in w:
            # Nightmare: Glowing Harvest Blood Moon with Bats Silhouette
            draw.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=(255, 125, 25, 255), outline=(255, 70, 20, 255), width=2)
            # Dark craters
            draw.ellipse([cx - 4, cy - 6, cx + 2, cy], fill=(215, 80, 15, 200))
            draw.ellipse([cx + 2, cy + 3, cx + 7, cy + 8], fill=(215, 80, 15, 200))
            # Flying Bats Silhouette (Wings)
            # Bat 1
            draw.arc([cx - 8, cy - 3, cx - 2, cy + 3], start=180, end=360, fill=(35, 15, 15, 255), width=2)
            draw.arc([cx - 3, cy - 3, cx + 3, cy + 3], start=180, end=360, fill=(35, 15, 15, 255), width=2)
            # Bat 2
            draw.arc([cx + 1, cy - 8, cx + 6, cy - 3], start=180, end=360, fill=(35, 15, 15, 255), width=2)
            draw.arc([cx + 5, cy - 8, cx + 10, cy - 3], start=180, end=360, fill=(35, 15, 15, 255), width=2)

        elif "portal" in w or "eclipse" in w:
            # Portal Eclipse: Cosmic Violet Ring
            draw.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=(35, 12, 55, 255), outline=(215, 115, 255, 255), width=3)

        elif "heavy" in w or "storm" in w:
            # Storm Cloud + Raindrops + Lightning
            draw.ellipse([cx - r + 2, cy - r + 6, cx + r - 2, cy + 2], fill=(160, 180, 205, 255))
            draw.ellipse([cx - r + 6, cy - r + 1, cx + 4, cy + 1], fill=(185, 200, 220, 255))
            pts = [(cx - 2, cy - 2), (cx + 3, cy + 5), (cx, cy + 5), (cx + 2, cy + 13), (cx - 4, cy + 6), (cx - 1, cy + 6)]
            draw.polygon(pts, fill=(255, 230, 70, 255))

        elif "rain" in w or "drizzle" in w:
            # Cloud + Rain
            draw.ellipse([cx - r + 2, cy - r + 4, cx + r - 2, cy + 2], fill=(215, 230, 245, 255))
            draw.ellipse([cx - r + 6, cy - r + 1, cx + 4, cy + 2], fill=(235, 245, 255, 255))
            draw.line([(cx - 6, cy + 5), (cx - 9, cy + 12)], fill=(110, 210, 255, 240), width=2)
            draw.line([(cx + 1, cy + 5), (cx - 2, cy + 12)], fill=(110, 210, 255, 240), width=2)
            draw.line([(cx + 8, cy + 5), (cx + 5, cy + 12)], fill=(110, 210, 255, 240), width=2)

        elif "snow" in w or "blizzard" in w:
            # Snowflake
            draw.line([(cx, cy - r + 2), (cx, cy + r - 2)], fill=(180, 240, 255, 255), width=2)
            draw.line([(cx - r + 2, cy), (cx + r - 2, cy)], fill=(180, 240, 255, 255), width=2)
            draw.line([(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)], fill=(180, 240, 255, 255), width=2)
            draw.line([(cx - r * 0.7, cy + r * 0.7), (cx + r * 0.7, cy - r * 0.7)], fill=(180, 240, 255, 255), width=2)

        elif "wind" in w or "gale" in w:
            # Wind streams
            draw.arc([cx - r, cy - 6, cx + r - 2, cy + 2], start=160, end=350, fill=(160, 240, 230, 255), width=2)
            draw.arc([cx - r + 4, cy - 1, cx + r, cy + 8], start=180, end=360, fill=(160, 240, 230, 255), width=2)

        elif "night" in w or "moon" in w:
            # Crescent Moon
            draw.ellipse([cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3], fill=(250, 240, 180, 255))
            draw.ellipse([cx - r + 8, cy - r + 1, cx + r + 2, cy + r - 5], fill=(25, 35, 65, 255))

        else:
            # Golden Sun
            draw.ellipse([cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3], fill=(255, 205, 50, 255))
            for deg in range(0, 360, 45):
                rad = math.radians(deg)
                x1 = cx + (r - 2) * math.cos(rad)
                y1 = cy + (r - 2) * math.sin(rad)
                x2 = cx + (r + 4) * math.cos(rad)
                y2 = cy + (r + 4) * math.sin(rad)
                draw.line([(x1, y1), (x2, y2)], fill=(255, 220, 80, 220), width=2)

    def render(self, data: dict) -> Image.Image:
        is_day = data.get("is_day", True)
        weather_type = data.get("weather_type", "Dry")
        w_lower = weather_type.lower()

        # -------------------------------------------------------------
        # DEDICATED WEATHER CARD TEMPLATES & PALETTES
        # -------------------------------------------------------------
        # Each weather has its own bespoke color grading, card glass tint, and accent glow:
        if "nightmare" in w_lower or "blood" in w_lower:
            theme = {
                "top": (38, 8, 16),
                "bottom": (74, 14, 28),
                "card_fill": (36, 12, 22, 185),
                "card_border": (255, 75, 95, 65),
                "pill_active_fill": (180, 35, 55, 230),
                "pill_active_border": (255, 120, 140, 210),
                "pill_inactive_fill": (45, 14, 25, 140),
                "sub_text": (255, 195, 205, 200),
                "fx": "nightmare",
            }
        elif "northern" in w_lower or "aurora" in w_lower:
            theme = {
                "top": (10, 26, 46),
                "bottom": (16, 56, 62),
                "card_fill": (14, 38, 52, 175),
                "card_border": (0, 245, 185, 60),
                "pill_active_fill": (0, 185, 155, 220),
                "pill_active_border": (120, 255, 225, 210),
                "pill_inactive_fill": (18, 44, 62, 135),
                "sub_text": (185, 245, 240, 200),
                "fx": "aurora",
            }
        elif "eclipse" in w_lower or "portal" in w_lower:
            theme = {
                "top": (24, 10, 48),
                "bottom": (64, 22, 92),
                "card_fill": (36, 18, 62, 180),
                "card_border": (195, 100, 255, 75),
                "pill_active_fill": (145, 55, 215, 225),
                "pill_active_border": (225, 155, 255, 210),
                "pill_inactive_fill": (42, 20, 68, 140),
                "sub_text": (230, 200, 255, 200),
                "fx": "eclipse",
            }
        elif "snow" in w_lower or "blizzard" in w_lower:
            theme = {
                "top": (36, 75, 115),
                "bottom": (125, 175, 215),
                "card_fill": (25, 55, 88, 175),
                "card_border": (190, 230, 255, 85),
                "pill_active_fill": (85, 150, 225, 225),
                "pill_active_border": (220, 245, 255, 220),
                "pill_inactive_fill": (35, 68, 105, 140),
                "sub_text": (210, 240, 255, 210),
                "fx": "snow",
            }
        elif "heavy" in w_lower or "storm" in w_lower or "thunder" in w_lower:
            theme = {
                "top": (22, 34, 52),
                "bottom": (54, 76, 102),
                "card_fill": (20, 32, 50, 185),
                "card_border": (115, 160, 210, 65),
                "pill_active_fill": (52, 95, 155, 225),
                "pill_active_border": (150, 200, 255, 200),
                "pill_inactive_fill": (25, 42, 65, 145),
                "sub_text": (195, 220, 245, 195),
                "fx": "heavy_rain",
            }
        elif "gale" in w_lower:
            theme = {
                "top": (26, 48, 62),
                "bottom": (62, 98, 116),
                "card_fill": (22, 42, 58, 180),
                "card_border": (130, 205, 215, 65),
                "pill_active_fill": (45, 135, 155, 220),
                "pill_active_border": (160, 240, 250, 200),
                "pill_inactive_fill": (28, 52, 72, 140),
                "sub_text": (195, 235, 245, 195),
                "fx": "gale",
            }
        elif "wind" in w_lower:
            theme = {
                "top": (36, 85, 125),
                "bottom": (82, 145, 185),
                "card_fill": (26, 58, 88, 175),
                "card_border": (165, 225, 245, 60),
                "pill_active_fill": (58, 145, 195, 220),
                "pill_active_border": (185, 240, 255, 200),
                "pill_inactive_fill": (32, 68, 98, 135),
                "sub_text": (210, 240, 255, 200),
                "fx": "wind",
            }
        elif "rain" in w_lower or "drizzle" in w_lower:
            theme = {
                "top": (28, 55, 92),
                "bottom": (68, 110, 155),
                "card_fill": (22, 44, 76, 175),
                "card_border": (145, 195, 245, 60),
                "pill_active_fill": (52, 118, 195, 220),
                "pill_active_border": (175, 225, 255, 200),
                "pill_inactive_fill": (28, 54, 90, 135),
                "sub_text": (205, 235, 255, 200),
                "fx": "rain",
            }
        elif not is_day:
            theme = {
                "top": (14, 20, 48),
                "bottom": (36, 32, 72),
                "card_fill": (18, 25, 54, 180),
                "card_border": (130, 160, 235, 55),
                "pill_active_fill": (65, 85, 185, 220),
                "pill_active_border": (160, 195, 255, 200),
                "pill_inactive_fill": (24, 34, 68, 135),
                "sub_text": (210, 230, 255, 190),
                "fx": "night",
            }
        else: # Dry / Sunny Clear
            theme = {
                "top": (38, 112, 205),
                "bottom": (92, 175, 238),
                "card_fill": (20, 56, 105, 165),
                "card_border": (255, 235, 160, 65),
                "pill_active_fill": (45, 135, 225, 220),
                "pill_active_border": (255, 230, 150, 210),
                "pill_inactive_fill": (24, 65, 118, 130),
                "sub_text": (225, 245, 255, 200),
                "fx": "dry",
            }

        # -------------------------------------------------------------
        # IN-GAME TIME-OF-DAY RESOLUTION (Day, Afternoon/Sunset, Night)
        # -------------------------------------------------------------
        clock_str = data.get("in_game_clock", "")
        time_of_day = data.get("time_of_day", None)
        
        if not time_of_day and clock_str:
            # Parse in-game hour from clock e.g. "05:20 PM", "11:00 AM", "01:30 PM"
            try:
                parts = clock_str.split()
                time_part = parts[0]
                period = parts[1].upper() if len(parts) > 1 else "AM"
                h = int(time_part.split(":")[0])
                if period == "PM" and h != 12:
                    h += 12
                elif period == "AM" and h == 12:
                    h = 0
                
                # In-Game diurnal cycle:
                # 05:00 to 15:59 -> Day
                # 16:00 to 18:59 -> Afternoon / Golden Hour Dusk
                # 19:00 to 04:59 -> Night
                if 5 <= h < 16:
                    time_of_day = "day"
                elif 16 <= h < 19:
                    time_of_day = "afternoon"
                else:
                    time_of_day = "night"
            except Exception:
                time_of_day = "day" if is_day else "night"

        if not time_of_day:
            time_of_day = "day" if is_day else "night"

        # Afternoon / Sunset theme palette adjustments for clear weathers
        if time_of_day == "afternoon" and any(k in w_lower for k in ["dry", "wind", "clear"]):
            theme["top"] = (72, 32, 28)        # Deep Sunset Amber
            theme["bottom"] = (145, 68, 38)    # Golden Horizon Orange
            theme["card_fill"] = (46, 22, 26, 175)
            theme["card_border"] = (255, 170, 90, 70)
            theme["pill_active_fill"] = (215, 95, 45, 225)
            theme["pill_active_border"] = (255, 195, 120, 210)
            theme["sub_text"] = (255, 220, 195, 210)

        # Try to load high quality nostalgic anime wallpaper for this weather and time of day
        carousel_idx = data.get("carousel_idx", None)
        if carousel_idx is None and "slot_index" in data:
            carousel_idx = data.get("slot_index", 0)

        anime_bg = self._get_anime_background(weather_type, is_day, carousel_idx=carousel_idx, time_of_day=time_of_day)

        if anime_bg:
            img = anime_bg.copy()
            # Apply a cinematic weather tint & soft vignette overlay to ensure text and glassmorphism stand out
            vignette = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            vig_draw = ImageDraw.Draw(vignette)
            
            # Subtle weather-color gradient wash from top to bottom
            for y in range(self.height):
                ratio = y / float(self.height)
                # Darken more towards cards area
                alpha = int(40 + ratio * 150)
                r = int(theme["top"][0] * (1 - ratio) + theme["bottom"][0] * ratio)
                g = int(theme["top"][1] * (1 - ratio) + theme["bottom"][1] * ratio)
                b = int(theme["top"][2] * (1 - ratio) + theme["bottom"][2] * ratio)
                vig_draw.line([(0, y), (self.width, y)], fill=(r, g, b, alpha))
            
            img.alpha_composite(vignette)
            draw = ImageDraw.Draw(img)
        else:
            img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 255))
            draw = ImageDraw.Draw(img)
            self._draw_gradient(draw, theme["top"], theme["bottom"])

        # Render procedural atmospheric weather effects on top of anime background
        fx_mode = theme["fx"]
        if fx_mode == "aurora":
            self._draw_starry_sky(draw, 140)
            self._draw_aurora_curtains(img)
        elif fx_mode == "nightmare":
            self._draw_blood_mist(img)
        elif fx_mode == "eclipse":
            self._draw_cosmic_rift(img)
        elif fx_mode == "snow":
            self._draw_snow_fall(img)
        elif fx_mode == "heavy_rain":
            self._draw_rain_streaks(img, is_heavy=True)
        elif fx_mode == "rain":
            self._draw_rain_streaks(img, is_heavy=False)
        elif fx_mode in ["gale", "wind"]:
            self._draw_wind_swirls(img, is_gale=(fx_mode == "gale"))
        elif fx_mode == "night":
            self._draw_starry_sky(draw, 100)
        else: # dry
            if not anime_bg:
                self._draw_sun_flare(img)
                self._draw_fluffy_clouds(img, True)

        # -------------------------------------------------------------
        # 1. TOP HEADER & HERO METRICS
        # -------------------------------------------------------------
        realm_name = "THE PORTAL REALM"
        location_sub = f"BMKG Observatory • Server [{data.get('server_id', 'Online')[:8]}]"
        
        draw.text((self.width // 2, 65), realm_name, font=self.font_hero_cond, fill=(255, 255, 255, 245), anchor="mt")
        draw.text((self.width // 2, 112), location_sub, font=self.font_hero_sub, fill=theme["sub_text"], anchor="mt")

        temp_str = data.get("temp_display", "31°")
        draw.text((self.width // 2, 155), temp_str, font=self.font_hero_temp, fill=(255, 255, 255, 255), anchor="mt")
        
        cond_str = data.get("weather_display", "Dry • Mostly Clear")
        high_low = f"Season: {data.get('season', 'Spring')} (Day {data.get('season_day', 1)}/4) • Slot {data.get('slot_index', 3)}/6"
        draw.text((self.width // 2, 275), cond_str, font=self.font_hero_cond, fill=(255, 255, 255, 250), anchor="mt")
        draw.text((self.width // 2, 325), high_low, font=self.font_hero_sub, fill=theme["sub_text"], anchor="mt")

        # -------------------------------------------------------------
        # 2. HOURLY FORECAST CAPSULE PILLS
        # -------------------------------------------------------------
        card_y0 = 375
        card_y1 = 665
        self._draw_glass_card(img, 40, card_y0, self.width - 40, card_y1, radius=32, 
                              fill_color=theme["card_fill"], border_color=theme["card_border"])
        draw = ImageDraw.Draw(img)

        draw.text((70, card_y0 + 20), "Hourly Weather Forecast", font=self.font_title, fill=(255, 255, 255, 245))
        draw.text((self.width - 70, card_y0 + 26), "Rolls every 2 Real Hours", font=self.font_small, fill=theme["sub_text"], anchor="ra")

        slots = data.get("hourly_slots", [
            {"time": "04 AM", "icon": "Dry", "temp": "28°", "temp_num": 28, "prob": "35%", "is_active": False},
            {"time": "08 AM", "icon": "NorthernLights", "temp": "29°", "temp_num": 29, "prob": "22%", "is_active": False},
            {"time": "Now",   "icon": weather_type, "temp": "31°", "temp_num": 31, "prob": "Live", "is_active": True},
            {"time": "04 PM", "icon": "Nightmare", "temp": "30°", "temp_num": 30, "prob": "12%", "is_active": False},
            {"time": "08 PM", "icon": "Rain", "temp": "26°", "temp_num": 26, "prob": "20%", "is_active": False},
            {"time": "12 AM", "icon": "Night", "temp": "24°", "temp_num": 24, "prob": "8%",  "is_active": False},
        ])

        pill_width = 142
        pill_gap = 18
        start_x = (self.width - (len(slots) * pill_width + (len(slots) - 1) * pill_gap)) // 2
        pill_y0 = card_y0 + 65
        pill_y1 = card_y1 - 30

        for i, s in enumerate(slots):
            px0 = start_x + i * (pill_width + pill_gap)
            px1 = px0 + pill_width
            is_active = s.get("is_active", False)

            if is_active:
                self._draw_glass_card(img, px0, pill_y0, px1, pill_y1, radius=24, 
                                      fill_color=theme["pill_active_fill"], border_color=theme["pill_active_border"])
            else:
                self._draw_glass_card(img, px0, pill_y0, px1, pill_y1, radius=24, 
                                      fill_color=theme["pill_inactive_fill"], border_color=theme["card_border"])
            
            draw = ImageDraw.Draw(img)
            cx = (px0 + px1) // 2
            
            # Time Label
            time_col = (255, 255, 255, 255) if is_active else (210, 225, 255, 205)
            draw.text((cx, pill_y0 + 16), s["time"], font=self.font_pill_time, fill=time_col, anchor="mt")

            # Icon
            icon_key = s.get("icon", "Dry")
            self._draw_weather_icon(draw, cx, pill_y0 + 64, icon_key, size=34)

            # Prob
            prob_str = s.get("prob", "0%")
            prob_col = (130, 240, 255, 255) if is_active else (170, 210, 255, 185)
            draw.text((cx, pill_y0 + 94), prob_str, font=self.font_small, fill=prob_col, anchor="mt")

            # Temp (cleanly placed inside capsule)
            temp_val = s.get("temp", "30°")
            draw.text((cx, pill_y0 + 125), temp_val, font=self.font_pill_temp, fill=(255, 255, 255, 255), anchor="mt")

        # -------------------------------------------------------------
        # 3. CELESTIAL SUN / MOON ARC WIDGET
        # -------------------------------------------------------------
        arc_card_y0 = 690
        arc_card_y1 = 905
        self._draw_glass_card(img, 40, arc_card_y0, self.width - 40, arc_card_y1, radius=28, 
                              fill_color=theme["card_fill"], border_color=theme["card_border"])
        draw = ImageDraw.Draw(img)

        draw.text((70, arc_card_y0 + 20), "In-Game Celestial Orbit & Clock", font=self.font_title, fill=(255, 255, 255, 245))
        clock_str = f"In-Game: {data.get('in_game_clock', '9:17 AM')} (Rolls at {data.get('target_roll_hour', '12:00 PM')})"
        draw.text((70, arc_card_y0 + 52), clock_str, font=self.font_body, fill=theme["sub_text"])

        arc_cx = self.width // 2
        arc_cy = arc_card_y1 - 36
        arc_rx = 320
        arc_ry = 110

        arc_points = []
        for deg in range(180, 361, 3):
            rad = math.radians(deg)
            ax = arc_cx + arc_rx * math.cos(rad)
            ay = arc_cy + arc_ry * math.sin(rad)
            arc_points.append((ax, ay))

        if len(arc_points) > 1:
            draw.line(arc_points, fill=(125, 165, 245, 135), width=4)

        progress = data.get("slot_progress", 0.65)
        current_deg = 180 + progress * 180
        curr_rad = math.radians(current_deg)
        sun_x = arc_cx + arc_rx * math.cos(curr_rad)
        sun_y = arc_cy + arc_ry * math.sin(curr_rad)

        draw.ellipse([sun_x - 14, sun_y - 14, sun_x + 14, sun_y + 14], fill=(255, 220, 90, 255), outline=(255, 255, 255, 245), width=3)
        draw.text((sun_x, sun_y - 24), "Current Time", font=self.font_small_bold, fill=(255, 240, 165, 245), anchor="mb")

        draw.text((arc_cx - arc_rx + 10, arc_cy + 8), "03:00 AM (Roll Start)", font=self.font_small, fill=theme["sub_text"], anchor="mt")
        draw.text((arc_cx + arc_rx - 10, arc_cy + 8), "05:00 AM (Next Roll)", font=self.font_small, fill=theme["sub_text"], anchor="mt")

        # -------------------------------------------------------------
        # 4. TELEMETRY & STATS 2X2 GRID (WITH RED / GREEN BUFF BADGES)
        # -------------------------------------------------------------
        grid_y0 = 930
        grid_h = 220
        col_w = (self.width - 80 - 20) // 2
        left_x0 = 40
        left_x1 = left_x0 + col_w
        right_x0 = left_x1 + 20
        right_x1 = right_x0 + col_w

        # --- Card 1: Atmospheric Severity & Sensors ---
        self._draw_glass_card(img, left_x0, grid_y0, left_x1, grid_y0 + grid_h, radius=24, 
                              fill_color=theme["card_fill"], border_color=theme["card_border"])
        draw = ImageDraw.Draw(img)
        draw.text((left_x0 + 24, grid_y0 + 18), "ATMOSPHERE & SEVERITY", font=self.font_small_bold, fill=(160, 205, 255, 190))
        draw.text((left_x0 + 24, grid_y0 + 44), f"Storm Level: {data.get('storm_level', '0% (Calm)')}", font=self.font_body_bold, fill=(255, 255, 255, 245))
        
        # Severity Bar
        bar_x0 = left_x0 + 24
        bar_x1 = left_x1 - 24
        bar_y = grid_y0 + 82
        draw.rounded_rectangle([bar_x0, bar_y, bar_x1, bar_y + 12], radius=6, fill=(48, 68, 108, 180))
        storm_pct = data.get("storm_pct", 0.05)
        fill_x = bar_x0 + (bar_x1 - bar_x0) * storm_pct
        if fill_x - bar_x0 >= 16:
            draw.rounded_rectangle([bar_x0, bar_y, fill_x, bar_y + 12], radius=6, fill=(80, 210, 255, 255))
        elif fill_x > bar_x0:
            draw.rectangle([bar_x0, bar_y, fill_x, bar_y + 12], fill=(80, 210, 255, 255))

        draw.text((left_x0 + 24, grid_y0 + 114), f"Wind Force: {data.get('wind_force', '0.2 (Gentle)')}", font=self.font_small, fill=(215, 235, 255, 220))
        draw.text((left_x0 + 24, grid_y0 + 144), f"Precipitation: {data.get('rain_index', '0.0 (None)')}", font=self.font_small, fill=(215, 235, 255, 220))
        draw.text((left_x0 + 24, grid_y0 + 174), f"Shelter Sensor: {data.get('indoor_status', 'Outdoors')}", font=self.font_small, fill=(215, 235, 255, 220))

        # --- Card 2: Market & Modifiers (WITH COLORED CHIPS) ---
        self._draw_glass_card(img, right_x0, grid_y0, right_x1, grid_y0 + grid_h, radius=24, 
                              fill_color=theme["card_fill"], border_color=theme["card_border"])
        draw = ImageDraw.Draw(img)
        active_mods = data.get("active_modifiers", [])
        if active_mods:
            # Render exactly the active in-game modifiers as beautiful chips
            curr_y = grid_y0 + 48
            curr_x = right_x0 + 24
            for mod_str in active_mods:
                m_low = mod_str.lower()
                # Positive buffs even if they have special words
                if any(k in m_low for k in ["auto-water", "lumen", "upgrade", "exp", "monster", "mining", "mineral", "fish", "unlocked", "sale"]):
                    b_type = "positive"
                elif "-" in mod_str or "shop +" in m_low or "inflation" in m_low:
                    b_type = "negative"
                else:
                    b_type = "positive"
                # Check wrap
                try:
                    tw = self.font_chip.getbbox(mod_str)[2] - self.font_chip.getbbox(mod_str)[0]
                except Exception:
                    tw = len(mod_str) * 9
                if curr_x + tw + 34 > right_x1 - 10:
                    curr_x = right_x0 + 24
                    curr_y += 46
                curr_x = self._draw_buff_chip(img, draw, curr_x, curr_y, mod_str, b_type)
        else:
            # Fallback to standard 3 rows
            chip_y1 = grid_y0 + 46
            curr_x = right_x0 + 24
            
            price_val = data.get("price_val", 0)
            if price_val > 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y1, f"Shop +{price_val}%", "negative")
            elif price_val < 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y1, f"Shop {price_val}% Sale", "positive")
            else:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y1, "Shop 1.0x Normal", "neutral")
            
            dmg_val = data.get("damage_val", 0)
            if dmg_val > 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y1, f"Damage +{dmg_val}%", "positive")
            elif dmg_val < 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y1, f"Damage {dmg_val}%", "negative")
            else:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y1, "Damage 1.0x", "neutral")

            chip_y2 = grid_y0 + 94
            curr_x = right_x0 + 24

            spd_val = data.get("speed_val", 0)
            if spd_val > 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y2, f"Speed +{spd_val}%", "positive")
            elif spd_val < 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y2, f"Speed {spd_val}%", "negative")
            else:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y2, "Speed 1.0x", "neutral")

            upg_val = data.get("upgrade_val", 0)
            if upg_val > 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y2, f"Upgrade +{upg_val}%", "positive")
            else:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y2, "Upgrade +0%", "neutral")

            chip_y3 = grid_y0 + 142
            curr_x = right_x0 + 24

            mine_val = data.get("mining_val", 0)
            if mine_val > 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y3, f"Mining +{mine_val}%", "positive")
            elif mine_val < 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y3, f"Mining {mine_val}%", "negative")
            
            extra_buff = data.get("special_buff", "")
            if extra_buff:
                is_pos = "+" in extra_buff or any(k in extra_buff.lower() for k in ["lumen", "fish", "water", "aurora", "mineral", "luck", "drop", "bonus", "exp"])
                if "shop +" in extra_buff.lower() or "inflation" in extra_buff.lower() or "hazard" in extra_buff.lower() or "horror" in extra_buff.lower():
                    is_pos = False
                b_type = "positive" if is_pos else "negative"
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y3, extra_buff, b_type)
            elif mine_val == 0:
                curr_x = self._draw_buff_chip(img, draw, curr_x, chip_y3, "Mining 1.0x Normal", "neutral")

        # -------------------------------------------------------------
        # 5. 24H WEATHER GACHA ODDS CARD (INCLUDES NORTHERN LIGHTS & NIGHTMARE)
        # -------------------------------------------------------------
        gacha_y0 = 1175
        gacha_y1 = 1535
        self._draw_glass_card(img, 40, gacha_y0, self.width - 40, gacha_y1, radius=28, 
                              fill_color=theme["card_fill"], border_color=theme["card_border"])
        draw = ImageDraw.Draw(img)

        draw.text((70, gacha_y0 + 20), f"Weather Gacha Probability (Day {data.get('season_day', 1)} Pool)", font=self.font_title, fill=(255, 255, 255, 245))
        draw.text((self.width - 70, gacha_y0 + 26), "Calculated from Seasonal Odds", font=self.font_small, fill=theme["sub_text"], anchor="ra")

        odds = data.get("odds", [
            ("Northern Lights", "NorthernLights", 25),
            ("Dry", "Dry", 25),
            ("Drizzle", "Drizzle", 18),
            ("Rain", "Rain", 15),
            ("Windy", "Windy", 10),
            ("Heavy Rain", "HeavyRain", 5),
            ("Gale", "Gale", 2),
            ("Nightmare", "Nightmare", 0),
            ("Snow", "Snow", 0),
        ])

        odds_start_y = gacha_y0 + 64
        row_h = 34
        for idx, (w_name, w_key, w_pct) in enumerate(odds[:9]):
            ry = odds_start_y + idx * row_h
            # Draw vector weather icon
            self._draw_weather_icon(draw, 85, ry + 10, w_key, size=22)
            
            # Label
            draw.text((108, ry), w_name, font=self.font_body, fill=(255, 255, 255, 235))
            
            # Bar gauge
            bx0 = 310
            bx1 = self.width - 150
            draw.rounded_rectangle([bx0, ry + 6, bx1, ry + 18], radius=6, fill=(45, 62, 98, 165))
            
            fill_len = (bx1 - bx0) * (w_pct / 100.0)
            if fill_len >= 16:
                # Custom bar colors for special weathers
                if "northern" in w_key.lower():
                    bar_color = (0, 245, 185, 255)
                elif "nightmare" in w_key.lower():
                    bar_color = (255, 60, 85, 255)
                elif w_pct > 15:
                    bar_color = (100, 205, 255, 245)
                else:
                    bar_color = (75, 145, 225, 205)
                draw.rounded_rectangle([bx0, ry + 6, bx0 + fill_len, ry + 18], radius=6, fill=bar_color)
            elif fill_len > 2:
                draw.rectangle([bx0, ry + 6, bx0 + fill_len, ry + 18], fill=(75, 145, 225, 205))

            # Percentage text
            draw.text((self.width - 70, ry), f"{w_pct:2d}%", font=self.font_body_bold, fill=(225, 245, 255, 245), anchor="ra")

        # -------------------------------------------------------------
        # 6. PORTAL RIFT FOOTER BANNER
        # -------------------------------------------------------------
        portal_y0 = 1555
        portal_y1 = 1645
        self._draw_glass_card(img, 40, portal_y0, self.width - 40, portal_y1, radius=20, 
                              fill_color=(46, 26, 78, 185), border_color=(185, 105, 255, 85))
        draw = ImageDraw.Draw(img)

        portal_text = f"Dewdrop Portal & Eclipse: {data.get('portal_time_str', 'Opening in 2 days 8 hours')}"
        draw.text((70, portal_y0 + 16), portal_text, font=self.font_body_bold, fill=(240, 210, 255, 255))
        draw.text((70, portal_y0 + 48), "Siapkan mental & equip terbaik! (Prepare your best gear & potions!)", font=self.font_small, fill=(205, 185, 245, 205))

        return img
