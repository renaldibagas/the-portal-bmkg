import asyncio
from PIL import Image, ImageOps, ImageEnhance
from typing import Optional
import winocr

class OCREngine:
    def __init__(self, lang: str = "en"):
        self.lang = lang

    def preprocess_image(self, pil_image: Image.Image) -> Image.Image:
        """
        Converts to grayscale and applies autocontrast to make green text on
        beige parchment 100% sharp and legible for Windows OCR.
        """
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # 1. Grayscale conversion (separates green font cleanly from parchment)
        gray = pil_image.convert("L")

        # 2. Normalize contrast across the parchment
        autoc = ImageOps.autocontrast(gray, cutoff=1)

        # 3. 1.5x Resize with bicubic interpolation
        w, h = autoc.size
        resized = autoc.resize((int(w * 1.5), int(h * 1.5)), Image.Resampling.BICUBIC)

        return resized

    async def extract_text_async(self, pil_image: Image.Image) -> str:
        """
        Extracts text using Windows Native OCR engine (Windows.Media.Ocr).
        Consumes virtually 0% CPU and zero GPU.
        """
        try:
            processed = self.preprocess_image(pil_image)
            result = await winocr.recognize_pil(processed, lang=self.lang)
            return result.text if result else ""
        except Exception as e:
            try:
                result = await winocr.recognize_pil(pil_image.convert("L"), lang=self.lang)
                return result.text if result else ""
            except Exception as e2:
                print(f"[OCREngine] OCR Error: {e2}")
                return ""

    def extract_text_sync(self, pil_image: Image.Image) -> str:
        """Synchronous wrapper for extract_text_async"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.extract_text_async(pil_image))
