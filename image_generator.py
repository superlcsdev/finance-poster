"""
image_generator.py — finance-poster
Format : 1080x1080 square
Pipeline:
  1. HuggingFace SDXL-Lightning  (fast, free with token)
  2. HuggingFace SD 1.5          (reliable fallback)
  3. Local stock image            (stock/finance/ folder)
  4. Dark card (30,30,30)         (absolute last resort)
Branding: LAWRENCE SIA / YOUR PERSONAL COACH
Font    : Montserrat (fonts/ folder) → Liberation/DejaVu fallback
"""

import os
import time
import hashlib
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

IMAGE_WIDTH  = 1080
IMAGE_HEIGHT = 1080

HF_API_TOKEN      = os.getenv("HF_API_TOKEN", "")
HF_SDXL_LIGHTNING = "https://router.huggingface.co/hf-inference/models/ByteDance/SDXL-Lightning"
HF_SD15           = "https://router.huggingface.co/hf-inference/models/stable-diffusion-v1-5/stable-diffusion-v1-5"

SAFE_FALLBACK_PROMPT = (
    "aspirational wealth lifestyle, laptop coffee modern desk, "
    "warm golden tones, professional, clean background, square composition, no text, no words"
)

_BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
STOCK_DIR  = os.path.join(_BASE_DIR, "stock", "finance")
_FONTS_DIR = os.path.join(_BASE_DIR, "fonts")

FONT_EXTRABOLD = [
    os.path.join(_FONTS_DIR, "Montserrat-ExtraBold.ttf"),
    os.path.join(_FONTS_DIR, "Montserrat-Bold.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_BOLD = [
    os.path.join(_FONTS_DIR, "Montserrat-Bold.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_MEDIUM = [
    os.path.join(_FONTS_DIR, "Montserrat-Medium.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Image prompt generator ─────────────────────────────────────────────────────
IMAGE_PROMPT_REQUEST = """You are a creative director for a finance and wealth-building Facebook page.
Write ONE image generation prompt for this article headline.

Headline: "{headline}"

RULES:
- The image must be DIRECTLY related to the topic in the headline
- Be specific and visual — describe what you actually see in the image
- Avoid generic warm-yellow laptop scenes unless the article is literally about remote work
- Use varied visual styles: dramatic cityscapes, abstract finance concepts, real people making decisions, infographic-style visuals, outdoor professional settings
- No text, no words, no letters in the image
- Always end with: "square composition, 1080x1080, photorealistic, high resolution, no text, no words"
- Max 20 words total in the prompt

Examples of GOOD prompts for finance headlines:
- "Most Filipino Professionals Retire Broke Despite Good Salaries" → "elderly couple sitting on bench looking at empty wallet, muted blue tones, realistic, candid"
- "AI-Powered Tool Helps Entrepreneurs Write Books Faster" → "futuristic robot writing with pen on glowing paper, dark studio, dramatic blue light"
- "Singapore Property Prices Hit Record High in 2025" → "aerial view Singapore skyline luxury condos, golden hour, dramatic perspective"
- "How to Build a Second Income Stream on a Nurse's Salary" → "nurse in scrubs holding piggy bank and stethoscope, confident smile, clean white studio"
- "Stock Market Hits New High as Inflation Cools" → "dramatic upward arrow made of coins against dark background, gold and black, sharp"

Write ONLY the image prompt. No preamble. No explanation."""

# Fallback style pool — diverse finance visuals across multiple colour palettes
STYLE_POOL = [
    # Bold / dramatic finance
    "dramatic upward arrow made of golden coins, dark background, sharp focus, square, no text",
    "stack of SGD banknotes fanning out, clean white background, overhead shot, square, no text",
    "chess king piece on financial chart background, dark moody strategic, square, no text",
    "hands breaking chains representing financial freedom, dramatic lighting, square, no text",
    "glass jar overflowing with coins, bright white studio, concept wealth growth, square, no text",
    # Urban / professional
    "Singapore Marina Bay skyline at night, reflections on water, dramatic, square, no text",
    "Manila Makati skyline at golden hour, ambitious mood, warm tones, square, no text",
    "confident professional in suit on rooftop, city view behind, square, no text",
    "diverse team of Asian professionals in modern boardroom, energetic, square, no text",
    "close-up of signing a business contract, confident hands, clean desk, square, no text",
    # Investment concepts
    "growing plant emerging from coins on dark soil, wealth cultivation concept, square, no text",
    "hourglass with golden sand and coins, time is money concept, dramatic, square, no text",
    "compass pointing north on financial newspaper, decision concept, square, no text",
    "ladder leaning against building reaching into bright sky, ambition, square, no text",
    "bridge made of money crossing a gap, financial bridge concept, dramatic, square, no text",
    # Digital / modern
    "holographic stock chart floating in dark space, blue glowing tones, square, no text",
    "smartphone showing green upward chart, clean minimal white, sharp, square, no text",
    "credit card with rainbow reflection, clean dark background, premium feel, square, no text",
    "laptop showing financial dashboard with green numbers, modern office, square, no text",
    "abstract network of glowing golden nodes, financial connections, dark, square, no text",
    # Real people
    "young Filipino nurse holding piggy bank, white studio, confident smile, square, no text",
    "engineer reviewing blueprints with calculator, professional, warm light, square, no text",
    "couple reviewing documents together at kitchen table, focused, warm, square, no text",
    "person holding small plant sprouting from coin, hope concept, bright, square, no text",
    # Abstract wealth
    "golden coins raining from dark sky, dramatic lighting, abundance concept, square, no text",
    "crystal ball showing city skyline, future planning concept, dark moody, square, no text",
    "two paths diverging in forest, choice and opportunity, cool morning, square, no text",
    "sunrise over city horizon with silhouette professional, ambitious, square, no text",
    "open treasure chest with glowing light, opportunity concept, dramatic, square, no text",
    "rolled banknotes arranged as bar chart, financial data art, clean, square, no text",
    "broken piggy bank with money flowing out, financial crisis concept, muted, square, no text",
    "key unlocking glowing door, financial breakthrough concept, dark dramatic, square, no text",
]


def _load_font(paths: list, size: int) -> ImageFont.FreeTypeFont:
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _build_prompt_via_gemini(headline: str) -> str | None:
    """Ask Gemini to write a specific image prompt based on the actual headline."""
    if not GEMINI_API_KEY:
        return None
    try:
        prompt = IMAGE_PROMPT_REQUEST.format(headline=headline)
        resp   = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15,
        )
        result = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if "no text" not in result.lower():
            result += ", square composition, photorealistic, high resolution, no text, no words"
        print(f"  🎨 Gemini image prompt: {result[:80]}...")
        return result
    except Exception as e:
        print(f"  ⚠️  Gemini image prompt error: {e}")
        return None


def _build_prompt(headline: str, category: str = "default") -> str:
    """Try Gemini first for a headline-specific prompt, fall back to style pool."""
    gemini_prompt = _build_prompt_via_gemini(headline)
    if gemini_prompt:
        return gemini_prompt
    # Fallback: rotate through diverse style pool
    date_str  = datetime.now().strftime("%Y-%m-%d")
    hash_seed = int(hashlib.md5((date_str + headline[:30]).encode()).hexdigest(), 16)
    style     = STYLE_POOL[hash_seed % len(STYLE_POOL)]
    print(f"  🎨 Fallback style: {style[:60]}...")
    return f"{style}, high resolution, photorealistic, vibrant"


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


def _hf_call(prompt: str, api_url: str) -> Image.Image | None:
    if not HF_API_TOKEN:
        return None
    w = (min(IMAGE_WIDTH,  1024) // 8) * 8
    h = (min(IMAGE_HEIGHT, 1024) // 8) * 8
    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": prompt, "parameters": {
                "width": w, "height": h,
                "num_inference_steps": 4,
                "guidance_scale": 0,
            }},
            timeout=120,
        )
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            return img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
        if resp.status_code == 503:
            print("  ⏳ HF model loading, waiting 20s...")
            time.sleep(20)
            resp2 = requests.post(api_url,
                headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
                json={"inputs": prompt}, timeout=120)
            if resp2.status_code == 200:
                img = Image.open(BytesIO(resp2.content)).convert("RGB")
                return img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
        print(f"  ⚠️  HF HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  ⚠️  HF error: {e}")
    return None


def _stock_image(headline: str) -> Image.Image | None:
    """Pick a stock photo from stock/finance/ rotating by date+headline hash."""
    if not os.path.isdir(STOCK_DIR):
        return None
    files = sorted([f for f in os.listdir(STOCK_DIR)
                    if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    if not files:
        return None
    date_str  = datetime.now().strftime("%Y-%m-%d")
    hash_seed = int(hashlib.md5((date_str + headline[:20]).encode()).hexdigest(), 16)
    chosen    = files[hash_seed % len(files)]
    try:
        img = Image.open(os.path.join(STOCK_DIR, chosen)).convert("RGB")
        img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
        print(f"  🖼️  Stock image: {chosen}")
        return img
    except Exception as e:
        print(f"  ⚠️  Stock image error: {e}")
    return None


def generate_background(prompt: str, headline: str = "") -> Image.Image | None:
    print("  🤗 Trying HuggingFace SDXL-Lightning...")
    img = _hf_call(prompt, HF_SDXL_LIGHTNING)
    if img:
        print(f"  ✅ SDXL-Lightning ({img.size[0]}x{img.size[1]}px)")
        return img

    print("  🤗 Trying HuggingFace SD 1.5...")
    img = _hf_call(SAFE_FALLBACK_PROMPT, HF_SD15)
    if img:
        print(f"  ✅ SD 1.5 ({img.size[0]}x{img.size[1]}px)")
        return img

    print("  ⚠️  HF failed — trying stock image...")
    img = _stock_image(headline)
    if img:
        return img

    print("  ❌ All providers failed.")
    return None


def _draw_logo_bar(draw, w: int, y_top: int, bar_h: int = 56) -> None:
    draw.rectangle([(0, y_top), (w, y_top + bar_h)], fill=(12, 12, 16, 220))
    fb = _load_font(FONT_BOLD,   20)
    fs = _load_font(FONT_MEDIUM, 11)
    bt, st = "LAWRENCE SIA", "YOUR PERSONAL COACH"
    bb = draw.textbbox((0, 0), bt, font=fb)
    sb = draw.textbbox((0, 0), st, font=fs)
    draw.text(((w-(bb[2]-bb[0]))//2, y_top+7),  bt, font=fb, fill=(255, 255, 255))
    draw.text(((w-(sb[2]-sb[0]))//2, y_top+33), st, font=fs, fill=(155, 155, 155))
    draw.rectangle([(0, y_top), (w, y_top+2)], fill=(180, 120, 40))


def add_text_overlay(image: Image.Image, headline: str,
                     source: str = "", tag: str = "MONEY & FREEDOM") -> Image.Image:
    w, h       = image.size
    SIDE_PAD   = 50
    BOTTOM_PAD = 36
    LOGO_BAR_H = 56
    CAP_GAP    = 16

    font      = _load_font(FONT_EXTRABOLD, 54)
    temp_draw = ImageDraw.Draw(image)
    max_w     = w - SIDE_PAD * 2

    def pw(text, fnt, mx):
        words, lines, cur = text.split(), [], ""
        for word in words:
            test = f"{cur} {word}".strip()
            if temp_draw.textbbox((0, 0), test, font=fnt)[2] > mx and cur:
                lines.append(cur); cur = word
            else:
                cur = test
        if cur: lines.append(cur)
        return lines

    lines = pw(headline, font, max_w)
    if len(lines) > 2: font = _load_font(FONT_EXTRABOLD, 44); lines = pw(headline, font, max_w)
    if len(lines) > 3: font = _load_font(FONT_EXTRABOLD, 36); lines = pw(headline, font, max_w)

    line_h      = int(font.size * 1.28)
    total_cap_h = len(lines) * line_h
    cap_y_start = h - BOTTOM_PAD - total_cap_h
    logo_y_top  = cap_y_start - CAP_GAP - LOGO_BAR_H
    grad_h      = (h - logo_y_top) + 60

    rgba    = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    od      = ImageDraw.Draw(overlay)
    for i in range(grad_h):
        od.rectangle([(0, h-grad_h+i), (w, h-grad_h+i+1)],
                     fill=(0, 0, 0, int(240*i/grad_h)))
    image = Image.alpha_composite(rgba, overlay).convert("RGB")
    draw  = ImageDraw.Draw(image)

    # Gold tag badge for finance
    font_tag = _load_font(FONT_BOLD, 22)
    tag_text = f"  {tag}  "
    tb       = draw.textbbox((0, 0), tag_text, font=font_tag)
    tw, th   = tb[2]-tb[0]+20, tb[3]-tb[1]+14
    draw.rounded_rectangle([(SIDE_PAD, SIDE_PAD), (SIDE_PAD+tw, SIDE_PAD+th)],
                           radius=6, fill=(180, 140, 20, 230))
    draw.text((SIDE_PAD+10, SIDE_PAD+7), tag_text, font=font_tag, fill=(255, 255, 255))

    _draw_logo_bar(draw, w, logo_y_top, LOGO_BAR_H)

    y = cap_y_start
    for line in lines:
        draw.text((SIDE_PAD+2, y+2), line, font=font, fill=(0, 0, 0, 150))
        draw.text((SIDE_PAD,   y),   line, font=font, fill=(255, 255, 255))
        y += line_h
    return image


def _create_dark_card(headline: str, tag: str = "MONEY & FREEDOM") -> Image.Image:
    img  = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    w, h = img.size
    PAD  = 60
    LBH  = 56

    font_tag = _load_font(FONT_BOLD, 22)
    tag_text = f"  {tag}  "
    tb = draw.textbbox((0, 0), tag_text, font=font_tag)
    tw, th = tb[2]-tb[0]+20, tb[3]-tb[1]+14
    draw.rounded_rectangle([(PAD, PAD), (PAD+tw, PAD+th)], radius=6, fill=(180, 140, 20, 230))
    draw.text((PAD+10, PAD+7), tag_text, font=font_tag, fill=(255, 255, 255))

    lyt = h - 30 - LBH
    _draw_logo_bar(draw, w, lyt, LBH)

    usable_top = PAD + th + 40
    usable_h   = (lyt - 20) - usable_top
    max_w      = w - PAD * 2
    font       = _load_font(FONT_EXTRABOLD, 64)
    lines      = _wrap_text(draw, headline, font, max_w)
    if len(lines) > 3: font = _load_font(FONT_EXTRABOLD, 52); lines = _wrap_text(draw, headline, font, max_w)
    if len(lines) > 4: font = _load_font(FONT_EXTRABOLD, 42); lines = _wrap_text(draw, headline, font, max_w)

    lh = int(font.size * 1.38)
    y  = usable_top + (usable_h - len(lines)*lh) // 2
    for line in lines:
        draw.text((PAD, y), line, font=font, fill=(255, 255, 255))
        y += lh
    return img


def create_post_image(headline: str, output_path: str, category: str = "finance",
                      source: str = "", tag: str = "MONEY & FREEDOM",
                      fallback_color: tuple = (30, 30, 30)) -> str | None:
    print(f'\n📸 Creating image: "{headline[:60]}..."')
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    prompt = _build_prompt(headline, category)
    bg     = generate_background(prompt, headline=headline)
    final  = add_text_overlay(bg, headline, tag=tag) if bg else _create_dark_card(headline, tag=tag)
    if bg is None:
        print("  ⚠️  Using dark card fallback.")
    final.save(output_path, quality=92)
    print(f"  💾 Saved → {output_path}")
    return output_path


if __name__ == "__main__":
    os.makedirs("output_images", exist_ok=True)
    create_post_image("Why Engineers With Good Salaries Still Can't Retire Early",
                      "output_images/test_finance.jpg")
