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

HOOK_PROMPT = """You are a Facebook content writer specialising in personal finance posts 
targeting Filipinos working in Singapore and the Philippines, as well as general Asian audiences.

Write a compelling Facebook post caption for this finance/business article.

Tone guidelines:
- Warm, relatable, and conversational — like a trusted friend sharing advice
- Speak directly to someone who works hard but feels stuck financially
- Reference relatable situations: OFW life, single income, supporting family back home, rising costs
- Subtly hint that there are smarter ways to build income beyond a single job — WITHOUT being pushy or mentioning specific companies/products
- Use Taglish sparingly for warmth (1-2 Filipino words max, e.g. "Kaya natin ito!" or "Ano na?") — only if it feels natural
- End with a soft call to action that invites conversation (e.g. "Are you working on a second income? Drop a 💬 below!")

Structure:
- Line 1: Hook — surprising stat, uncomfortable truth, or relatable question. NO emojis on first line.
- Lines 2-3: Brief insight or context (2-3 sentences)
- Line 4: Subtle nudge — remind them that one income is risky, there are options
- Last line: Soft CTA that invites engagement

Use 2-4 emojis naturally. Keep it under 220 words. Sound human, NOT like a news article.

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
    """Fallback template hooks written for Filipino side-income audience."""
    title = article["title"]
    templates = [
        f"Most people work 20-30 years and still can't retire comfortably. 😔\n\n"
        f"{title}\n\n"
        f"The hard truth? One income is no longer enough — especially with the cost of living going up every year. "
        f"The good news is, there are ways to build a second stream without leaving your current job. 💪\n\n"
        f"Are you already working on a second income? Share your experience below! 👇",

        f"Nobody taught us this in school. 📚\n\n"
        f"{title}\n\n"
        f"So many of us work hard, send money home, and still feel like we're running on a treadmill — moving but not getting ahead. "
        f"It doesn't have to stay that way. Small steps toward a second income can change everything. 🌱\n\n"
        f"What's one financial goal you're working on this year? Drop it in the comments! 💬",

        f"This is something every working person needs to read. 👀\n\n"
        f"{title}\n\n"
        f"Whether you're an OFW, a local employee, or running your own small business — "
        f"relying on just one income in today's economy is a risk most of us can't afford. "
        f"Kaya natin ito — but we have to start thinking differently. 💡\n\n"
        f"Tag someone who needs to see this! ❤️",
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
