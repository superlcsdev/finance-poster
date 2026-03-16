"""
image_generator.py
Generates Facebook post images for finance/side-income content.
Uses Pollinations.ai (free) → Hugging Face fallback → solid colour fallback.
Visual style: aspirational wealth, freedom, warm gold tones.
"""

import requests
import time
import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# ── Config ─────────────────────────────────────────────────────────────────
IMAGE_WIDTH  = 1200
IMAGE_HEIGHT = 630
TIMEOUT_SECS = 120
MAX_RETRIES  = 3

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_API_URL   = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

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

# Finance-specific category backgrounds
CATEGORY_PROMPTS = {
    "finance":     "professional wealth lifestyle, successful entrepreneur at laptop, "
                   "city skyline window view, warm golden hour lighting, aspirational, no text",
    "sideincome":  "freedom lifestyle photography, laptop on beach or cafe, "
                   "passive income aesthetic, bright warm tones, aspirational, no text",
    "investment":  "financial growth concept, golden coins stacked, upward chart abstract, "
                   "dark navy and gold tones, professional, no text",
    "savings":     "piggy bank coins jar, warm soft lighting, hopeful aesthetic, "
                   "Filipino family home context, no text",
    "ofw":         "airplane window view, overseas worker lifestyle, "
                   "sending money home concept, warm emotional tones, no text",
    "default":     "aspirational finance lifestyle, successful Asian professional, "
                   "warm gold tones, modern office or city background, no text",
}

SAFE_FALLBACK_PROMPT = (
    "aspirational wealth lifestyle, laptop coffee modern desk, "
    "warm golden tones, professional, clean background, no text, no words"
)


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
    style = CATEGORY_PROMPTS.get(category.lower(), CATEGORY_PROMPTS["default"])
    return f"{style}, high resolution, photorealistic, no text, no words, no letters"


def _generate_via_huggingface(prompt: str, width: int, height: int):
    if not HF_API_TOKEN:
        print("  ⚠️  HF_API_TOKEN not set — skipping Hugging Face fallback.")
        return None
    try:
        print("  🤗 Trying Hugging Face fallback...")
        resp = requests.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": prompt, "parameters": {"width": width, "height": height, "num_inference_steps": 30}},
            timeout=120,
        )
        if resp.status_code == 200:
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            print(f"  ✅ Hugging Face image received ({img.size[0]}x{img.size[1]}px)")
            return img
        elif resp.status_code == 503:
            print("  ⏳ HF model loading, waiting 20s...")
            time.sleep(20)
            resp = requests.post(HF_API_URL, headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
                                 json={"inputs": prompt}, timeout=120)
            if resp.status_code == 200:
                return Image.open(BytesIO(resp.content)).convert("RGB")
        print(f"  ⚠️  Hugging Face HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ Hugging Face error: {e}")
        return None


def generate_background(prompt: str, width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    params = {"width": width, "height": height, "nologo": "true", "enhance": "true",
              "seed": str(int(time.time()) % 99999)}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  🎨 Pollinations attempt {attempt}/{MAX_RETRIES}...")
            resp = requests.get(url, params=params, timeout=TIMEOUT_SECS)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                print(f"  ✅ Pollinations image received ({img.size[0]}x{img.size[1]}px)")
                return img
            elif resp.status_code == 500 and attempt == 2:
                print("  ⚠️  HTTP 500 — switching to safe fallback prompt...")
                url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(SAFE_FALLBACK_PROMPT)}"
            else:
                print(f"  ⚠️  HTTP {resp.status_code}, retrying in 5s...")
        except requests.exceptions.ReadTimeout:
            print(f"  ⏱️  Timeout on attempt {attempt}, waiting 5s...")
        except Exception as e:
            print(f"  ❌ Pollinations error: {e}")
        time.sleep(5)

    # Hugging Face fallback
    print("  ⚠️  Pollinations failed — trying Hugging Face...")
    hf_img = _generate_via_huggingface(SAFE_FALLBACK_PROMPT, width, height)
    if hf_img:
        return hf_img

    print("  ❌ All image generation attempts failed.")
    return None


def _draw_gradient_overlay(image: Image.Image) -> Image.Image:
    """Dark gradient overlay at bottom + subtle warm gold tint at top."""
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

    # Subtle gold tint top strip for warmth
    for i in range(80):
        alpha = int(40 * (1 - i / 80))
        draw.rectangle([(0, i), (w, i + 1)], fill=(180, 140, 30, alpha))

    return Image.alpha_composite(img_rgba, overlay)


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
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

    # ── Gold tag badge (top left) ─────────────────────────────────
    tag_text = f"  {tag}  "
    tag_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
    tag_w    = tag_bbox[2] - tag_bbox[0] + 20
    tag_h    = tag_bbox[3] - tag_bbox[1] + 14
    draw.rounded_rectangle([(pad, pad), (pad + tag_w, pad + tag_h)],
                            radius=6, fill=(180, 140, 20, 230))
    draw.text((pad + 10, pad + 7), tag_text, font=font_tag, fill=(255, 255, 255))

    # ── Headline (bottom area) ────────────────────────────────────
    lines       = _wrap_text(draw, headline, font_headline, w - pad * 2)
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
            "headline": "Most OFWs Return Home With No Savings After 10 Years Abroad",
            "category": "ofw",
            "source":   "PhilStar Business",
            "output":   "test_ofw.jpg",
        },
        {
            "headline": "5 Side Hustles That Let You Earn an Extra $1,000 a Month",
            "category": "sideincome",
            "source":   "Entrepreneur",
            "output":   "test_sideincome.jpg",
        },
    ]
    for tc in test_cases:
        create_post_image(headline=tc["headline"], output_path=tc["output"],
                          category=tc["category"], source=tc["source"])
