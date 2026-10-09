import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

class WeatherCardGenerator:
    def __init__(self, width: int = 1600, height: int = 900, bg_dir: str = None):
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
        self.font_micro     = get_font(font_paths, 13)
        self.font_micro_bold= get_font(bold_paths, 13)
        self.font_stat_val  = get_font(bold_paths, 16)
        self.font_stat_hdr  = get_font(bold_paths, 14)
        self.font_stat_sub  = get_font(font_paths, 11)


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
                         radius: int = 28, fill_color=(16, 26, 48, 140), border_color=(255, 255, 255, 50), blur_radius: int = 6):
        # 1. Subtle Box Blur behind card for soft translucent frosted glass effect
        w, h = base_img.size
        # Clamp crop coordinates
        cx0, cy0 = max(0, x0), max(0, y0)
        cx1, cy1 = min(w, x1), min(h, y1)
        if cx1 > cx0 and cy1 > cy0 and blur_radius > 0:
            crop = base_img.crop((cx0, cy0, cx1, cy1)).filter(ImageFilter.GaussianBlur(blur_radius))
            # Mask to rounded rectangle
            mask = Image.new("L", (cx1 - cx0, cy1 - cy0), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, cx1 - cx0, cy1 - cy0], radius=radius, fill=255)
            base_img.paste(crop, (cx0, cy0), mask)

        # 2. Glassmorphic tinted overlay with border
        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill_color, outline=border_color, width=2)
        base_img.alpha_composite(overlay)

    def _draw_buff_chip(self, base_img: Image.Image, draw: ImageDraw.ImageDraw, x0: int, y0: int, label: str, buff_type: str = "neutral", max_width: int = None):
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
        if max_width and chip_w > max_width:
            chip_w = max_width
        chip_h = 32
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

        disp_label = label
        if max_width:
            avail_tw = max_width - 32
            while len(disp_label) > 4:
                try:
                    bb = self.font_chip.getbbox(disp_label)
                    w = bb[2] - bb[0]
                except Exception:
                    w = len(disp_label) * 9
                if w <= avail_tw:
                    break
                disp_label = disp_label[:-2] + "…"

        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=fill_col, outline=border_col, width=1)
        base_img.alpha_composite(overlay)

        # Indicator dot
        draw.ellipse([x0 + 8, y0 + 13, x0 + 16, y0 + 21], fill=dot_col)
        # Label text
        draw.text((x0 + 22, y0 + 7), disp_label, font=self.font_chip, fill=text_col)

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
                "card_fill": (28, 8, 16, 155),
                "card_border": (255, 75, 95, 80),
                "pill_active_fill": (180, 35, 55, 210),
                "pill_active_border": (255, 120, 140, 200),
                "pill_inactive_fill": (38, 10, 20, 130),
                "sub_text": (255, 195, 205, 215),
                "fx": "nightmare",
            }
        elif "northern" in w_lower or "aurora" in w_lower:
            theme = {
                "top": (10, 26, 46),
                "bottom": (16, 56, 62),
                "card_fill": (10, 28, 42, 150),
                "card_border": (0, 245, 185, 80),
                "pill_active_fill": (0, 185, 155, 210),
                "pill_active_border": (120, 255, 225, 200),
                "pill_inactive_fill": (12, 32, 48, 130),
                "sub_text": (185, 245, 240, 215),
                "fx": "aurora",
            }
        elif "eclipse" in w_lower or "portal" in w_lower:
            theme = {
                "top": (24, 10, 48),
                "bottom": (64, 22, 92),
                "card_fill": (26, 12, 48, 155),
                "card_border": (195, 100, 255, 80),
                "pill_active_fill": (145, 55, 215, 210),
                "pill_active_border": (225, 155, 255, 200),
                "pill_inactive_fill": (30, 14, 52, 130),
                "sub_text": (230, 200, 255, 215),
                "fx": "eclipse",
            }
        elif "snow" in w_lower or "blizzard" in w_lower:
            theme = {
                "top": (36, 75, 115),
                "bottom": (125, 175, 215),
                "card_fill": (18, 42, 70, 150),
                "card_border": (190, 230, 255, 80),
                "pill_active_fill": (85, 150, 225, 210),
                "pill_active_border": (220, 245, 255, 200),
                "pill_inactive_fill": (24, 48, 80, 130),
                "sub_text": (210, 240, 255, 215),
                "fx": "snow",
            }
        elif "heavy" in w_lower or "storm" in w_lower or "thunder" in w_lower:
            theme = {
                "top": (22, 34, 52),
                "bottom": (54, 76, 102),
                "card_fill": (16, 26, 42, 155),
                "card_border": (115, 160, 210, 75),
                "pill_active_fill": (52, 95, 155, 210),
                "pill_active_border": (150, 200, 255, 200),
                "pill_inactive_fill": (20, 32, 52, 130),
                "sub_text": (195, 220, 245, 215),
                "fx": "heavy_rain",
            }
        elif "gale" in w_lower:
            theme = {
                "top": (26, 48, 62),
                "bottom": (62, 98, 116),
                "card_fill": (16, 32, 46, 150),
                "card_border": (130, 205, 215, 75),
                "pill_active_fill": (45, 135, 155, 210),
                "pill_active_border": (160, 240, 250, 200),
                "pill_inactive_fill": (20, 40, 56, 130),
                "sub_text": (195, 235, 245, 215),
                "fx": "gale",
            }
        elif "wind" in w_lower:
            theme = {
                "top": (36, 85, 125),
                "bottom": (82, 145, 185),
                "card_fill": (18, 42, 68, 150),
                "card_border": (165, 225, 245, 75),
                "pill_active_fill": (58, 145, 195, 210),
                "pill_active_border": (185, 240, 255, 200),
                "pill_inactive_fill": (24, 52, 78, 130),
                "sub_text": (210, 240, 255, 215),
                "fx": "wind",
            }
        elif "rain" in w_lower or "drizzle" in w_lower:
            theme = {
                "top": (28, 55, 92),
                "bottom": (68, 110, 155),
                "card_fill": (16, 34, 62, 150),
                "card_border": (145, 195, 245, 75),
                "pill_active_fill": (52, 118, 195, 210),
                "pill_active_border": (175, 225, 255, 200),
                "pill_inactive_fill": (22, 42, 72, 130),
                "sub_text": (205, 235, 255, 215),
                "fx": "rain",
            }
        elif not is_day:
            theme = {
                "top": (14, 20, 48),
                "bottom": (36, 32, 72),
                "card_fill": (14, 20, 44, 155),
                "card_border": (130, 160, 235, 70),
                "pill_active_fill": (65, 85, 185, 210),
                "pill_active_border": (160, 195, 255, 200),
                "pill_inactive_fill": (18, 26, 54, 130),
                "sub_text": (210, 230, 255, 215),
                "fx": "night",
            }
        else: # Dry / Sunny Clear
            theme = {
                "top": (38, 112, 205),
                "bottom": (92, 175, 238),
                "card_fill": (16, 44, 86, 145),
                "card_border": (255, 235, 160, 75),
                "pill_active_fill": (45, 135, 225, 210),
                "pill_active_border": (255, 230, 150, 200),
                "pill_inactive_fill": (18, 50, 95, 125),
                "sub_text": (225, 245, 255, 215),
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
            theme["card_fill"] = (46, 22, 26, 150)
            theme["card_border"] = (255, 170, 90, 70)
            theme["pill_active_fill"] = (215, 95, 45, 210)
            theme["pill_active_border"] = (255, 195, 120, 200)
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
            
            # Subtle weather-color gradient wash from top to bottom (soft and translucent)
            for y in range(self.height):
                ratio = y / float(self.height)
                alpha = int(25 + ratio * 85)
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

        # =============================================================
        # LEFT PANEL (Hero Banner, Season & Dewdrop Portal)
        # Dimensions: x0: 30, y0: 30, x1: 710, y1: 870
        # =============================================================
        left_x0, left_y0, left_x1, left_y1 = 30, 30, 710, 870
        self._draw_glass_card(img, left_x0, left_y0, left_x1, left_y1, radius=28,
                              fill_color=theme["card_fill"], border_color=theme["card_border"], blur_radius=6)
        draw = ImageDraw.Draw(img)

        # Header
        draw.text(((left_x0 + left_x1) // 2, left_y0 + 35), "THE PORTAL REALM", font=self.font_hero_cond, fill=(255, 255, 255, 255), anchor="mt")
        loc_sub = f"BMKG Observatory • Server: [{data.get('server_id', 'Online')[:8]}]"
        draw.text(((left_x0 + left_x1) // 2, left_y0 + 78), loc_sub, font=self.font_hero_sub, fill=theme["sub_text"], anchor="mt")

        # Giant Temperature
        temp_val = data.get("temp_display", "31°")
        draw.text(((left_x0 + left_x1) // 2, left_y0 + 125), temp_val, font=self.font_hero_temp, fill=(255, 255, 255, 255), anchor="mt")
        
        # Weather Condition Display & Weather Vector Icon
        cond_text = data.get("weather_display", "Drizzle • Gentle Rain")
        import re
        cond_clean = re.sub(r'[^\x20-\x7E]', '', cond_text).strip()
        hero_cx = (left_x0 + left_x1) // 2
        try:
            bbox = self.font_hero_cond.getbbox(cond_clean)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(cond_clean) * 18
        icon_cx = hero_cx - (tw // 2) - 24
        self._draw_weather_icon(draw, icon_cx, left_y0 + 278, weather_type, size=30)
        draw.text((hero_cx + 16, left_y0 + 262), cond_clean, font=self.font_hero_cond, fill=(255, 255, 255, 250), anchor="mt")
        
        # Season Badge Box (Wide inner margin)
        season_y0 = left_y0 + 328
        season_y1 = left_y0 + 440
        self._draw_glass_card(img, left_x0 + 45, season_y0, left_x1 - 45, season_y1, radius=20,
                              fill_color=theme["pill_inactive_fill"], border_color=theme["card_border"], blur_radius=5)
        draw = ImageDraw.Draw(img)
        season_name = data.get('season', 'Summer')
        season_day = data.get('season_day', 1)
        slot_idx = data.get('slot_index', 1)
        
        # Calculate real countdown to next 2-hour weather roll
        slot_prog = data.get("slot_progress")
        if slot_prog is not None and isinstance(slot_prog, (int, float)):
            rem_sec = int((1.0 - min(1.0, max(0.0, float(slot_prog)))) * 7200)
        else:
            try:
                import time
                from src.game_data_engine import get_current_season_state
                s_state = get_current_season_state()
                rem_sec = s_state.get("seconds_remaining_in_slot", 3600)
            except Exception:
                rem_sec = 3600

        rem_h = rem_sec // 3600
        rem_m = (rem_sec % 3600) // 60
        countdown_str = f"{rem_h}h {rem_m:02d}m" if rem_h > 0 else f"{rem_m}m"

        cur_slot = int(slot_idx) if str(slot_idx).isdigit() else 1
        if cur_slot < 1 or cur_slot > 6:
            cur_slot = 1
        next_slot = (cur_slot % 6) + 1

        # Determine upcoming roll probabilities
        odds = data.get("odds", [])
        if not odds:
            try:
                from src.game_data_engine import get_seasonal_odds
                raw_odds = get_seasonal_odds(season_name, season_day)
                odds = [(name, name, pct) for name, pct in raw_odds]
            except Exception:
                odds = [("Dry", "Dry", 40), ("Rain", "Rain", 25), ("Windy", "Windy", 15)]

        top_next_name = str(odds[0][0]) if len(odds) > 0 else "Normal"
        top_next_key = str(odds[0][1]) if len(odds) > 0 else "Dry"
        top_next_pct = int(odds[0][2]) if len(odds) > 0 else 30

        draw.text(((left_x0 + left_x1) // 2, season_y0 + 20), f"SEASON: {season_name.upper()}", font=self.font_title, fill=(255, 255, 255, 245), anchor="mt")
        season_desc = f"Day {season_day} of 4 • Slot {slot_idx} of 6 (Next Roll in {countdown_str})"
        draw.text(((left_x0 + left_x1) // 2, season_y0 + 58), season_desc, font=self.font_body, fill=theme["sub_text"], anchor="mt")

        # Dewdrop Portal & Lycaros Boss Raid Card (Generous padding from borders)
        portal_y0 = left_y1 - 345
        portal_y1 = left_y1 - 40
        self._draw_glass_card(img, left_x0 + 45, portal_y0, left_x1 - 45, portal_y1, radius=24,
                              fill_color=(18, 12, 38, 150), border_color=(185, 120, 255, 110), blur_radius=6)
        draw = ImageDraw.Draw(img)
        draw.text((left_x0 + 75, portal_y0 + 28), "DIMENSIONAL RIFT • LYCAROS RAID", font=self.font_title, fill=(215, 175, 255, 255))
        
        portal_time = data.get('portal_time_str', 'Opening in 2 days 10 hours')
        import re
        portal_time = re.sub(r'\s*\(\<t:\d+:[a-zA-Z]\>\)', '', portal_time).strip()
        draw.text((left_x0 + 75, portal_y0 + 74), f"Gate Status: {portal_time}", font=self.font_body_bold, fill=(255, 255, 255, 245))
        draw.text((left_x0 + 75, portal_y0 + 114), "Weekly Boss Lycaros: Fixed Sunday 04:00 AM & 04:00 PM", font=self.font_small, fill=(230, 210, 255, 230))
        draw.text((left_x0 + 75, portal_y0 + 152), "Rift Mutations: 2.65x Shadow Mutations every 120s (Rare)", font=self.font_small, fill=(255, 225, 140, 235))
        draw.text((left_x0 + 75, portal_y0 + 190), "Fish Biting: 100% Universal All-Fish active during Eclipse", font=self.font_small, fill=theme["sub_text"])

        # =============================================================
        # RIGHT PANEL (Hourly Forecast, Active Modifiers, Gacha Odds)
        # Dimensions: x0: 735, y0: 30, x1: 1570, y1: 870
        # =============================================================
        right_x0, right_y0, right_x1, right_y1 = 735, 30, 1570, 870

        # 1. Hourly Forecast Capsule Bar (Top of Right Panel)
        hour_y0 = right_y0
        hour_y1 = right_y0 + 225
        self._draw_glass_card(img, right_x0, hour_y0, right_x1, hour_y1, radius=24,
                              fill_color=theme["card_fill"], border_color=theme["card_border"], blur_radius=6)
        draw = ImageDraw.Draw(img)
        draw.text((right_x0 + 40, hour_y0 + 20), "Hourly Weather Forecast", font=self.font_title, fill=(255, 255, 255, 245))
        next_header_str = f"Next Roll in {countdown_str} • Top Chance: {top_next_name} ({top_next_pct}%)"
        draw.text((right_x1 - 40, hour_y0 + 24), next_header_str, font=self.font_small_bold, fill=(130, 240, 255, 245), anchor="ra")

        # Dynamically build 6 daily weather roll slots
        SLOT_HOURS = ["04 AM", "08 AM", "12 PM", "04 PM", "08 PM", "12 AM"]
        slots = []
        for i in range(1, 7):
            s_time = SLOT_HOURS[i - 1]
            if i == cur_slot:
                slots.append({
                    "time": "Now",
                    "badge": "LIVE",
                    "icon": weather_type,
                    "prob": "Live",
                    "temp": temp_val,
                    "is_active": True,
                    "is_next": False
                })
            elif i == next_slot:
                slots.append({
                    "time": s_time,
                    "badge": f"NEXT",
                    "icon": top_next_key,
                    "prob": f"{top_next_pct}%",
                    "temp": f"in {countdown_str}",
                    "is_active": False,
                    "is_next": True
                })
            elif i < cur_slot:
                slots.append({
                    "time": s_time,
                    "badge": "PAST",
                    "icon": "Dry",
                    "prob": "--",
                    "temp": "--",
                    "is_active": False,
                    "is_next": False
                })
            else:
                offset = (i - next_slot) % len(odds)
                f_name, f_key, f_pct = odds[offset] if offset < len(odds) else ("Dry", "Dry", 20)
                slots.append({
                    "time": s_time,
                    "badge": f"Roll {i}",
                    "icon": f_key,
                    "prob": f"{int(f_pct)}%",
                    "temp": f"~{int(f_pct)}%",
                    "is_active": False,
                    "is_next": False
                })

        pill_w = 114
        pill_gap = 14
        start_px = right_x0 + 40
        pill_y0 = hour_y0 + 64
        pill_y1 = hour_y1 - 22

        for i, s in enumerate(slots):
            px0 = start_px + i * (pill_w + pill_gap)
            px1 = px0 + pill_w
            is_act = s.get("is_active", False)
            is_nxt = s.get("is_next", False)
            
            if is_act:
                self._draw_glass_card(img, px0, pill_y0, px1, pill_y1, radius=18,
                                      fill_color=theme["pill_active_fill"], border_color=theme["pill_active_border"], blur_radius=4)
            elif is_nxt:
                self._draw_glass_card(img, px0, pill_y0, px1, pill_y1, radius=18,
                                      fill_color=(28, 48, 76, 195), border_color=(130, 240, 255, 230), blur_radius=4)
            else:
                self._draw_glass_card(img, px0, pill_y0, px1, pill_y1, radius=18,
                                      fill_color=theme["pill_inactive_fill"], border_color=theme["card_border"], blur_radius=4)
            
            draw = ImageDraw.Draw(img)
            pcx = (px0 + px1) // 2
            
            if is_act:
                t_col = (255, 255, 255, 255)
            elif is_nxt:
                t_col = (130, 240, 255, 255)
            else:
                t_col = (210, 225, 255, 205)
                
            draw.text((pcx, pill_y0 + 10), s["time"], font=self.font_pill_time, fill=t_col, anchor="mt")
            self._draw_weather_icon(draw, pcx, pill_y0 + 48, s.get("icon", "Dry"), size=28)
            
            if is_act:
                p_col = (130, 240, 255, 255)
            elif is_nxt:
                p_col = (255, 225, 140, 255)
            else:
                p_col = (170, 210, 255, 185)
                
            draw.text((pcx, pill_y0 + 74), s.get("prob", "0%"), font=self.font_small_bold if is_nxt else self.font_small, fill=p_col, anchor="mt")
            draw.text((pcx, pill_y0 + 98), s.get("temp", "30°"), font=self.font_small_bold if is_nxt else self.font_pill_temp, fill=(255, 255, 255, 255), anchor="mt")

        # 2. Market & Active Modifiers Card (Clean Full-Width Center Card)
        mod_y0 = hour_y1 + 18
        mod_y1 = mod_y0 + 225
        self._draw_glass_card(img, right_x0, mod_y0, right_x1, mod_y1, radius=24,
                              fill_color=theme["card_fill"], border_color=theme["card_border"], blur_radius=6)
        draw = ImageDraw.Draw(img)
        draw.text((right_x0 + 36, mod_y0 + 18), "MARKET & ADVENTURER MODIFIERS", font=self.font_title, fill=(255, 255, 255, 245))
        draw.text((right_x1 - 36, mod_y0 + 22), "Active Realm Buffs & Prices", font=self.font_small, fill=theme["sub_text"], anchor="ra")

        active_mods = data.get("active_modifiers", [])
        if active_mods:
            # 2-column grid layout for 3+ buffs; full width for 1-2 long buffs
            is_single_col = len(active_mods) <= 2
            col_gap = 16
            col_w = (right_x1 - right_x0 - 72) if is_single_col else ((right_x1 - right_x0 - 72 - col_gap) // 2)
            col1_x = right_x0 + 36
            col2_x = col1_x + col_w + col_gap
            
            for idx, mod_str in enumerate(active_mods[:8]):
                if is_single_col:
                    bx = col1_x
                    by = mod_y0 + 58 + idx * 42
                else:
                    col_idx = idx % 2
                    row_idx = idx // 2
                    bx = col2_x if col_idx == 1 else col1_x
                    by = mod_y0 + 58 + row_idx * 38
                
                m_low = mod_str.lower()
                if any(k in m_low for k in ["auto-water", "lumen", "upgrade", "exp", "monster", "mining", "mineral", "fish", "unlocked", "sale", "+"]):
                    if "shop +" in m_low or "inflation" in m_low:
                        b_type = "negative"
                    else:
                        b_type = "positive"
                elif "-" in mod_str or "shop +" in m_low or "inflation" in m_low or "hazard" in m_low:
                    b_type = "negative"
                else:
                    b_type = "positive"
                
                self._draw_buff_chip(img, draw, bx, by, mod_str, buff_type=b_type, max_width=col_w)
        else:
            col_gap = 16
            col_w = (right_x1 - right_x0 - 72 - col_gap) // 2
            col1_x = right_x0 + 36
            col2_x = col1_x + col_w + col_gap
            
            price_val = data.get("price_val", 0)
            if price_val > 0:
                self._draw_buff_chip(img, draw, col1_x, mod_y0 + 58, f"Shop +{price_val}% (Surcharge)", buff_type="negative", max_width=col_w)
            elif price_val < 0:
                self._draw_buff_chip(img, draw, col1_x, mod_y0 + 58, f"Shop {price_val}% Sale", buff_type="positive", max_width=col_w)
            else:
                self._draw_buff_chip(img, draw, col1_x, mod_y0 + 58, "Shop 1.0x Normal (Standard Prices)", buff_type="neutral", max_width=col_w)
            
            dmg_val = data.get("damage_val", 0)
            if dmg_val > 0:
                self._draw_buff_chip(img, draw, col2_x, mod_y0 + 58, f"Damage +{dmg_val}%", buff_type="positive", max_width=col_w)
            elif dmg_val < 0:
                self._draw_buff_chip(img, draw, col2_x, mod_y0 + 58, f"Damage {dmg_val}%", buff_type="negative", max_width=col_w)
            else:
                self._draw_buff_chip(img, draw, col2_x, mod_y0 + 58, "Combat Multipliers: 1.0x Normal", buff_type="neutral", max_width=col_w)

            spd_val = data.get("speed_val", 0)
            if spd_val > 0:
                self._draw_buff_chip(img, draw, col1_x, mod_y0 + 98, f"Speed +{spd_val}%", buff_type="positive", max_width=col_w)
            elif spd_val < 0:
                self._draw_buff_chip(img, draw, col1_x, mod_y0 + 98, f"Speed {spd_val}%", buff_type="negative", max_width=col_w)
            else:
                self._draw_buff_chip(img, draw, col1_x, mod_y0 + 98, "Movement Speed: 1.0x Normal", buff_type="neutral", max_width=col_w)

        # 3. 24H Weather Gacha Forecast (2H, 4H, 8H, 12H, 24H Multi-Horizon Stats)
        gacha_y0 = mod_y1 + 18
        gacha_y1 = right_y1
        self._draw_glass_card(img, right_x0, gacha_y0, right_x1, gacha_y1, radius=24,
                              fill_color=theme["card_fill"], border_color=theme["card_border"], blur_radius=6)
        draw = ImageDraw.Draw(img)
        draw.text((right_x0 + 36, gacha_y0 + 16), "24H Weather Gacha Forecast", font=self.font_title, fill=(255, 255, 255, 245))
        draw.text((right_x1 - 36, gacha_y0 + 20), "Roll Odds: 2H • 4H • 8H • 12H • 24H", font=self.font_small_bold, fill=(130, 240, 255, 245), anchor="ra")

        # Table Column Geometry across 763px usable card width
        tbl_x0 = right_x0 + 36
        tbl_x1 = right_x1 - 36
        name_col_w = 215
        
        time_cols = [
            ("2 Hours", 1),
            ("4 Hours", 2),
            ("8 Hours", 4),
            ("12 Hours", 6),
            ("24 Hours", 12),
        ]
        num_time = len(time_cols)
        col_w = (tbl_x1 - (tbl_x0 + name_col_w)) // num_time
        time_centers = [tbl_x0 + name_col_w + i * col_w + (col_w // 2) for i in range(num_time)]

        # Header Bar
        hdr_y0 = gacha_y0 + 48
        hdr_y1 = hdr_y0 + 26
        draw.rounded_rectangle([tbl_x0, hdr_y0, tbl_x1, hdr_y1], radius=6, fill=(20, 34, 58, 195), outline=(75, 120, 185, 90), width=1)
        draw.text((tbl_x0 + 16, hdr_y0 + 5), "WEATHER EVENT", font=self.font_stat_hdr, fill=(175, 210, 255, 235))
        
        for i, (col_label, _) in enumerate(time_cols):
            cx = time_centers[i]
            draw.text((cx, hdr_y0 + 5), col_label.upper(), font=self.font_stat_hdr, fill=(175, 210, 255, 235), anchor="mt")

        # Odds Data
        odds = data.get("odds", [
            ["Rain", "Rain", 30],
            ["Heavy Rain", "HeavyRain", 22],
            ["Drizzle", "Drizzle", 14],
            ["Windy", "Windy", 12],
            ["Dry", "Dry", 10],
            ["Gale", "Gale", 6],
            ["Nightmare", "Nightmare", 10]
        ])

        cur_w_low = weather_type.lower()
        cur_season_low = str(data.get("season", "")).lower()

        # Cumulative probability: P_n = 1 - (1 - p)^n
        def calc_cum_pct(p_pct, rolls):
            p = max(0.0, min(100.0, float(p_pct))) / 100.0
            if p <= 0:
                return 0
            return int(round((1.0 - math.pow(1.0 - p, rolls)) * 100.0))

        # Render Weather Rows (up to 7 weathers)
        row_start_y = hdr_y1 + 6
        row_h = 34
        row_gap = 4
        
        for idx, (label, key, pct) in enumerate(odds[:7]):
            ry0 = row_start_y + idx * (row_h + row_gap)
            ry1 = ry0 + row_h
            
            k_low = str(key).lower()
            is_active_now = (k_low in cur_w_low or cur_w_low in k_low)
            
            pct_val = int(pct) if isinstance(pct, (int, float)) else 0
            if "nightmare" in k_low and ("autumn" in cur_season_low or pct_val <= 0):
                pct_val = 10
            elif "northern" in k_low and ("summer" in cur_season_low or pct_val <= 0):
                pct_val = 10
                
            # Row Background styling
            if is_active_now:
                if "nightmare" in k_low:
                    r_fill, r_bord = (85, 18, 30, 205), (255, 75, 95, 225)
                elif "northern" in k_low:
                    r_fill, r_bord = (16, 68, 62, 205), (0, 255, 195, 225)
                else:
                    r_fill, r_bord = (32, 72, 130, 205), (130, 240, 255, 225)
                draw.rounded_rectangle([tbl_x0, ry0, tbl_x1, ry1], radius=8, fill=r_fill, outline=r_bord, width=1)
            else:
                bg_col = (20, 32, 54, 115) if idx % 2 == 1 else (15, 24, 42, 65)
                draw.rounded_rectangle([tbl_x0, ry0, tbl_x1, ry1], radius=8, fill=bg_col)

            # Weather Icon & Label
            self._draw_weather_icon(draw, tbl_x0 + 16, ry0 + 17, key, size=22)
            lbl_col = (255, 255, 255, 255) if is_active_now else (230, 242, 255, 235)
            draw.text((tbl_x0 + 34, ry0 + 7), str(label), font=self.font_small_bold, fill=lbl_col)
            
            if is_active_now:
                # Small LIVE badge next to label
                badge_bg = (255, 60, 85, 230) if "nightmare" in k_low else (0, 230, 175, 230)
                badge_x0 = tbl_x0 + 148
                draw.rounded_rectangle([badge_x0, ry0 + 8, badge_x0 + 44, ry0 + 26], radius=4, fill=badge_bg)
                draw.text((badge_x0 + 22, ry0 + 10), "LIVE", font=self.font_micro_bold, fill=(255, 255, 255, 255), anchor="mt")

            # Render 5 Probability Horizon Columns: 2h, 4h, 8h, 12h, 24h
            for i, (_, rolls) in enumerate(time_cols):
                cx = time_centers[i]
                c_pct = calc_cum_pct(pct_val, rolls)
                
                # Dynamic text color scaling
                if is_active_now:
                    v_col = (255, 225, 120, 255) if i == 0 else (255, 255, 255, 255)
                elif c_pct >= 80:
                    v_col = (110, 255, 180, 255)
                elif c_pct >= 50:
                    v_col = (130, 240, 255, 255)
                elif c_pct >= 25:
                    v_col = (180, 225, 255, 235)
                else:
                    v_col = (195, 215, 240, 205)
                
                draw.text((cx, ry0 + 5), f"{c_pct}%", font=self.font_stat_val, fill=v_col, anchor="mt")
                
                # Micro Progress Fill Bar beneath percentage
                bar_w = 48
                bar_h = 4
                bx0 = cx - (bar_w // 2)
                by0 = ry0 + 24
                draw.rectangle([bx0, by0, bx0 + bar_w, by0 + bar_h], fill=(35, 52, 78, 170))
                
                fill_len = max(2, int(bar_w * (c_pct / 100.0)))
                if "northern" in k_low:
                    b_col = (0, 245, 185, 230)
                elif "nightmare" in k_low:
                    b_col = (255, 65, 90, 230)
                elif c_pct >= 75:
                    b_col = (80, 240, 160, 220)
                else:
                    b_col = (100, 200, 255, 220)
                draw.rectangle([bx0, by0, bx0 + fill_len, by0 + bar_h], fill=b_col)

        return img
