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

HOOK_PROMPT = """You are writing a Facebook post caption for Filipino professionals — nurses, 
IT workers, engineers, architects, pharmacists — based in Singapore and the Philippines.

Write a caption for this finance article that sounds like a real person wrote it, not AI.

LANGUAGE RULES — very important:
- Use simple, everyday English. Short sentences. Max 15 words per sentence.
- Write like you're messaging a smart friend — casual but not sloppy
- Contractions always: "you're" not "you are", "it's" not "it is", "don't" not "do not"
- Be specific: "engineers with good salaries" not "high-income individuals"
- NEVER use these words: leverage, optimise, empower, unlock, holistic, sustainable,
  transformative, actionable, synergy, catalyse, utilise, impactful, robust, wealth-building
- Never start with "Are you..." or "Did you know..." — too generic, sounds like AI
- One idea per sentence. Break any sentence over 15 words into two.
- Very occasional Filipino word (max 1 per post, only if natural): "Tayo na." / "Kaya natin."

CONTENT RULES:
- Speak to the gap between earning well and actually building wealth
- Nudge them toward thinking about multiple income streams — subtle, not pushy
- No hardship framing. No OFW struggle. No remittance mentions.
- A surprising stat or an uncomfortable truth lands better than motivation

Structure:
- Line 1: One sharp opening line. No emoji. Not a question. Something that makes them think.
- Lines 2–3: Two short sentences with real context. No fluff.
- Last line: Short honest CTA. Something a real colleague would say.

Use 2–3 emojis. Max 4 sentences. Don't mention the source website.

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
    """Simple, human-sounding fallback templates for Filipino professionals."""
    title = article["title"]
    templates = [
        f"A good salary and a growing bank account are two different things. 📊\n"
        f"{title}.\n"
        f"Most professionals close the income gap but never close the wealth gap. It's a strategy problem, not an income problem. 💡\n"
        f"What's one financial habit you're building right now? Drop it below 👇",

        f"Your degree got you the job. What's building your future? 🎯\n"
        f"{title}.\n"
        f"One income is fine — until it isn't. The professionals who feel secure are usually the ones who built a second stream before they needed it. 🌱\n"
        f"Tayo na. Where are you in this journey? Comment below 👇",

        f"Most people with good salaries retire with very little. Here's why. 💸\n"
        f"{title}.\n"
        f"It's not about earning more. It's about what you build with what you already earn. 🔑\n"
        f"Save this — and share it with a colleague who needs a reset.",
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
