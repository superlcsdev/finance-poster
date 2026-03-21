"""
hook_writer.py
Writes Facebook hook captions for finance/side-income posts.
Audience: Filipinos in Singapore and Philippines + general Asian audience.
Tone: Relatable, aspirational, subtle nudge toward side income — not salesy.
"""

import os
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

HOOK_PROMPT = """You are a Facebook finance content writer for an audience of Filipino professionals 
— nurses, IT professionals, engineers, architects, pharmacists, statisticians, and other 
degree-holding career-driven individuals based in Singapore and the Philippines.

Write a compelling Facebook post caption for this finance/business article.

Tone guidelines:
- Speak to their professional identity and financial ambition — not hardship
- Frame around opportunity cost: they earn well but may not be building wealth optimally
- Peer-to-peer voice — like a financially savvy colleague sharing insight
- Use data, percentages, or surprising stats when relevant — this audience is analytical
- Connect to their professional context: high skills, demanding careers, good income
- Very occasional Filipino word for warmth (max 1 per post, only if completely natural)
  e.g. "Tayo na." or "Kaya natin ito." — never heavy Taglish
- Never mention remittance, OFW hardship, or domestic worker framing
- Subtle nudge toward multiple income streams — not pushy, just thought-provoking

Structure:
- Line 1: Hook — sharp observation, surprising stat, or professional angle. NO emoji on first line.
- Lines 2–3: Brief insight relevant to a high-earning professional
- Last line: Thought-provoking CTA that respects their intelligence

Use 2–3 emojis naturally. Max 4 sentences. Do NOT mention source website.

Article title  : {title}
Article summary: {summary}

Write ONLY the caption. No preamble, no quotes."""


def _call_gemini(prompt: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"  ⚠️  Gemini hook error: {e}")
        print(f"  ⚠️  Gemini response: {resp.text[:300] if 'resp' in locals() else 'no response'}")
        return None


def _call_openrouter(prompt: str) -> str | None:
    if not OPENROUTER_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "model":    "mistralai/mistral-7b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️  OpenRouter hook error: {e}")
        return None


def _template_hook(article: dict) -> str:
    """Professional-tone fallback templates for Filipino professionals."""
    title = article["title"]
    templates = [
        f"Most professionals with good salaries still retire with very little to show for it. 📊\n\n"
        f"{title}\n\n"
        f"A high income is a starting point — not a destination. The gap between earning well and building wealth "
        f"is almost always a strategy problem, not an income problem. 💡\n\n"
        f"What's one financial habit you've built this year? Drop it below 👇",

        f"Your degree got you the salary. What's building your wealth? 🎯\n\n"
        f"{title}\n\n"
        f"The most overlooked financial risk for professionals isn't market volatility — "
        f"it's over-dependence on a single income source in a world that's increasingly unpredictable. "
        f"Tayo na. The best time to diversify was five years ago. The second best time is now. 🌱\n\n"
        f"Are you building a second income stream? Share where you are in the journey 👇",

        f"High earners and low earners often retire at the same financial level. Here's why. 💸\n\n"
        f"{title}\n\n"
        f"It's not about how much you make — it's about the systems you build around what you make. "
        f"For professionals in demanding careers, the window to build those systems is now, not later. 🔑\n\n"
        f"Save this and share it with a colleague who needs to hear it 👇",
    ]
    idx = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(templates)
    return templates[idx]


def generate_hook(article: dict) -> str:
    prompt = HOOK_PROMPT.format(
        title   = article.get("title", ""),
        summary = article.get("summary", "No summary available."),
    )

    hook = None
    if GEMINI_API_KEY:
        hook = _call_gemini(prompt)
    elif OPENROUTER_API_KEY:
        hook = _call_openrouter(prompt)

    if not hook:
        print("  ⚠️  Using template hook (no AI key configured).")
        hook = _template_hook(article)

    return hook


if __name__ == "__main__":
    test_article = {
        "title":   "Most OFWs Return Home With No Savings After 10 Years Abroad, Study Finds",
        "summary": "A new survey reveals that despite high remittances, many overseas Filipino workers struggle to build lasting wealth.",
        "url":     "https://example.com/ofw-savings",
        "source":  "PhilStar Business",
    }
    print(generate_hook(test_article))
