"""
image_generator.py
Generates Facebook post images for finance/wealth content.
Priority: HuggingFace SDXL → HuggingFace SD 2.1 → Pollinations → solid colour fallback.
Visual style: aspirational wealth, professional, warm gold tones.
"""

import requests
import time
import os
import hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ── Config ─────────────────────────────────────────────────────────────────
IMAGE_WIDTH  = 1200
IMAGE_HEIGHT = 632   # divisible by 8 (required by HuggingFace)
TIMEOUT_SECS = 120
MAX_RETRIES  = 3

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# Primary HF model — SDXL (best quality)
HF_API_URL_PRIMARY  = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
# Secondary HF model — SD 2.1 (faster, reliable fallback)
HF_API_URL_FALLBACK = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-2-1"

SAFE_FALLBACK_PROMPT = (
    "aspirational wealth lifestyle, laptop coffee modern desk, "
    "warm golden tones, professional, clean background, no text, no words"
)

FONT_PATHS_BOLD = [
    "arialbd.ttf",
    "Arial_Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_PATHS_REGULAR = [
    "arial.ttf",
    "Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(paths: list, size: int):
    win_fonts = os.path.join(os.environ.get("WINDIR", ""), "Fonts")
    for path in paths:
        for candidate in [path, os.path.join(win_fonts, path)]:
            if os.path.exists(candidate):
                try:
                    return ImageFont.truetype(candidate, size)
                except Exception:
                    pass
    return ImageFont.load_default()


def _build_prompt(headline: str, category: str = "default") -> str:
    """
    Build prompt with high visual variety — 32 styles rotating by date + headline.
    Finance-specific styles: wealth, professional, aspirational.
    """
    STYLE_POOL = [
        # Professional & wealth
        "successful professional at modern office desk, city skyline view, warm golden hour, no text",
        "luxury minimalist home office setup, natural light, aspirational lifestyle, no text",
        "aerial city financial district at golden hour, warm tones, ambitious, no text",
        "entrepreneur working laptop in sleek modern cafe, warm ambient light, no text",
        "professional Asian woman reviewing charts, modern office, confident, aspirational, no text",
        "glass skyscraper exterior reflecting sunset, financial district, no text",
        "modern coworking space, diverse professionals, bright natural light, no text",
        "executive boardroom with city view, professional, clean lines, warm tones, no text",
        # Investment & wealth symbols
        "golden coins and growing plant on marble, wealth growth concept, clean minimal, no text",
        "upward trending abstract chart, gold and navy tones, financial success, no text",
        "stack of books and laptop, self-improvement, warm lighting, professional desk, no text",
        "piggy bank with coins and plants, savings growth, bright optimistic tones, no text",
        "clock and coins concept, time and money, clean minimal, professional, no text",
        "calculator and financial documents, professional, clean white desk, no text",
        "keys and miniature house model, property investment concept, warm light, no text",
        "chess pieces on board, strategic thinking, business metaphor, dark elegant, no text",
        # Freedom & lifestyle
        "person working laptop on tropical beach, digital nomad lifestyle, no text",
        "convertible car on coastal road, freedom lifestyle, golden hour, aspirational, no text",
        "luxury travel first class seat, business success lifestyle, clean, no text",
        "rooftop terrace with city view, successful lifestyle, evening golden light, no text",
        "person hiking mountain summit, achievement metaphor, dramatic landscape, no text",
        "sailboat on calm blue ocean, financial freedom concept, bright clear sky, no text",
        # Abstract & conceptual
        "geometric gold lines on dark background, wealth abstraction, elegant minimal, no text",
        "light through prism creating spectrum, opportunity concept, clean studio, no text",
        "compass on world map, navigation success, warm leather tones, no text",
        "ladder leading to bright sky, growth opportunity, clean concept, no text",
        "bridge over calm water, connection progress, sunrise golden tones, no text",
        "seeds growing into plants in glass jars, wealth cultivation, bright clean, no text",
        # Asian professional context
        "Singapore financial district skyline, Marina Bay, golden hour, no text",
        "Manila Makati business district, modern towers, evening lights, no text",
        "Asian professional in smart casual, confident pose, neutral background, no text",
        "team of diverse Asian professionals, modern office, collaborative, no text",
    ]

    date_str  = datetime.now().strftime("%Y-%m-%d")
    hash_seed = int(hashlib.md5((date_str + headline[:30]).encode()).hexdigest(), 16)
    style     = STYLE_POOL[hash_seed % len(STYLE_POOL)]

    return f"{style}, high resolution, photorealistic, vibrant"


def _call_huggingface(prompt: str, width: int, height: int, api_url: str):
    """Call a single HuggingFace model. Returns Image or None."""
    if not HF_API_TOKEN:
        return None
    # Enforce divisible-by-8
    width  = (min(width,  1024) // 8) * 8
    height = (min(height, 1024) // 8) * 8
    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={
                "inputs": prompt,
                "parameters": {
                    "width":               width,
                    "height":              height,
                    "num_inference_steps": 30,
                    "guidance_scale":      7.5,
                }
            },
            timeout=120,
        )
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
            return img
        elif resp.status_code == 503:
            print(f"  ⏳ HF model loading, waiting 25s...")
            time.sleep(25)
            resp = requests.post(
                api_url,
                headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
                json={"inputs": prompt},
                timeout=120,
            )
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
                return img
        print(f"  ⚠️  HF HTTP {resp.status_code}: {resp.text[:150]}")
        return None
    except Exception as e:
        print(f"  ❌ HF error: {e}")
        return None


def _generate_via_huggingface(prompt: str, width: int, height: int):
    """Try SDXL first, fall back to SD 2.1."""
    if not HF_API_TOKEN:
        print("  ⚠️  HF_API_TOKEN not set — skipping HuggingFace.")
        return None

    print("  🤗 Trying HuggingFace SDXL (primary)...")
    img = _call_huggingface(prompt, width, height, HF_API_URL_PRIMARY)
    if img:
        print(f"  ✅ SDXL image received ({img.size[0]}x{img.size[1]}px)")
        return img

    print("  🤗 Trying HuggingFace SD 2.1 (secondary)...")
    img = _call_huggingface(prompt, width, height, HF_API_URL_FALLBACK)
    if img:
        print(f"  ✅ SD 2.1 image received ({img.size[0]}x{img.size[1]}px)")
        return img

    print("  ❌ Both HuggingFace models failed.")
    return None


def _generate_via_pollinations(prompt: str, width: int, height: int):
    """Last resort — try Pollinations."""
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    params = {
        "width":   width,
        "height":  height,
        "nologo":  "true",
        "enhance": "true",
        "seed":    str(int(time.time()) % 99999),
        "model":   "flux",
    }
    for attempt in range(1, 3):
        try:
            print(f"  🎨 Pollinations attempt {attempt}/2...")
            resp = requests.get(url, params=params, timeout=90)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                print(f"  ✅ Pollinations image received ({img.size[0]}x{img.size[1]}px)")
                return img
            print(f"  ⚠️  Pollinations HTTP {resp.status_code}, retrying...")
        except requests.exceptions.ReadTimeout:
            print(f"  ⏱️  Pollinations timeout on attempt {attempt}...")
        except Exception as e:
            print(f"  ❌ Pollinations error: {e}")
        time.sleep(5)
    return None


def generate_background(prompt: str, width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT):
    """
    Generate background image.
    Priority: HuggingFace SDXL → HuggingFace SD 2.1 → Pollinations → None
    """
    # 1. Try HuggingFace (primary + secondary)
    img = _generate_via_huggingface(prompt, width, height)
    if img:
        return img

    # 2. Retry HuggingFace with safe prompt
    if prompt != SAFE_FALLBACK_PROMPT:
        print("  ⚠️  Retrying HuggingFace with safe generic prompt...")
        img = _generate_via_huggingface(SAFE_FALLBACK_PROMPT, width, height)
        if img:
            return img

    # 3. Last resort: Pollinations
    print("  ⚠️  HuggingFace failed — trying Pollinations as last resort...")
    img = _generate_via_pollinations(SAFE_FALLBACK_PROMPT, width, height)
    if img:
        return img

    print("  ❌ All image generation methods failed.")
    return None


def _draw_gradient_overlay(image: Image.Image) -> Image.Image:
    """Dark gradient at bottom + subtle warm gold tint at top."""
    img_rgba = image.convert("RGBA")
    overlay  = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    draw     = ImageDraw.Draw(overlay)
    w, h     = img_rgba.size

    # Dark gradient bottom 60%
    grad_h = int(h * 0.60)
    for i in range(grad_h):
        alpha = int(200 * (i / grad_h))
        y     = h - grad_h + i
        draw.rectangle([(0, y), (w, y + 1)], fill=(0, 0, 0, alpha))

    # Subtle gold tint top strip
    for i in range(80):
        alpha = int(40 * (1 - i / 80))
        draw.rectangle([(0, i), (w, i + 1)], fill=(180, 140, 30, alpha))

    return Image.alpha_composite(img_rgba, overlay)


def _wrap_text(draw, text: str, font, max_width: int) -> list:
    words, lines, current = text.split(), [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def add_text_overlay(image: Image.Image, headline: str,
                     source: str = "", tag: str = "MONEY & FREEDOM") -> Image.Image:
    image = _draw_gradient_overlay(image)
    draw  = ImageDraw.Draw(image)
    w, h  = image.size
    pad   = 50

    font_tag      = _load_font(FONT_PATHS_BOLD,    26)
    font_headline = _load_font(FONT_PATHS_BOLD,    56)
    font_source   = _load_font(FONT_PATHS_REGULAR, 28)

    # ── Gold tag badge (top left) ──────────────────────────────────
    tag_text = f"  {tag}  "
    tag_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
    tag_w    = tag_bbox[2] - tag_bbox[0] + 20
    tag_h    = tag_bbox[3] - tag_bbox[1] + 14
    draw.rounded_rectangle([(pad, pad), (pad + tag_w, pad + tag_h)],
                            radius=6, fill=(180, 140, 20, 230))
    draw.text((pad + 10, pad + 7), tag_text, font=font_tag, fill=(255, 255, 255))

    # ── Headline (pixel-aware word wrap) ──────────────────────────
    max_text_w = w - pad * 2

    def wrap_by_pixels(text, font, max_px):
        words, lines, current = text.split(), [], ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] > max_px and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    lines       = wrap_by_pixels(headline, font_headline, max_text_w)
    line_height = 68
    total_h     = len(lines) * line_height + (45 if source else 0)
    y           = h - pad - total_h

    for line in lines:
        draw.text((pad + 2, y + 2), line, font=font_headline, fill=(0, 0, 0, 180))
        draw.text((pad,     y),     line, font=font_headline, fill=(255, 255, 255))
        y += line_height

    if source:
        draw.text((pad + 1, y + 1), source, font=font_source, fill=(0, 0, 0, 160))
        draw.text((pad,     y),     source, font=font_source, fill=(220, 200, 120))

    return image.convert("RGB")


def create_post_image(headline: str, output_path: str, category: str = "finance",
                      source: str = "", tag: str = "MONEY & FREEDOM",
                      fallback_color: tuple = (15, 30, 70)) -> str | None:
    print(f"\n📸 Creating image for: \"{headline[:60]}...\"")

    prompt = _build_prompt(headline, category)
    bg     = generate_background(prompt)

    if bg is None:
        print("  ⚠️  Using solid colour fallback background.")
        bg = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), fallback_color)

    final = add_text_overlay(bg, headline, source=source, tag=tag)
    final.save(output_path, quality=92)
    print(f"  💾 Saved → {output_path}")
    return output_path


if __name__ == "__main__":
    test_cases = [
        {
            "headline": "Why High-Earning Professionals Still Struggle to Build Wealth",
            "category": "finance",
            "source":   "Forbes",
            "output":   "test_finance.jpg",
        },
        {
            "headline": "5 Income Streams Every Professional Should Build in Their 30s",
            "category": "sideincome",
            "source":   "Entrepreneur",
            "output":   "test_sideincome.jpg",
        },
    ]
    for tc in test_cases:
        create_post_image(headline=tc["headline"], output_path=tc["output"],
                          category=tc["category"], source=tc["source"])
