"""
ai_selector.py
Selects the most viral finance/side-income article for Filipino audience.
Uses Gemini → OpenRouter → heuristic fallback.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

SELECTION_PROMPT = """You are a viral finance content strategist for Facebook targeting Filipinos 
in Singapore and the Philippines, as well as general Asian audiences.

Given these finance/business articles, select the ONE most likely to get high engagement 
(shares, reactions, comments) on Facebook.

Prioritise articles that:
- Speak to OFWs, overseas workers, or people with a single income source
- Highlight financial struggle, survival, or aspiration relatable to Filipinos
- Inspire people to think about side income or financial independence
- Contain surprising statistics or uncomfortable financial truths
- Are actionable and immediately useful for everyday people

Avoid:
- Too technical or stock market jargon-heavy articles
- Articles targeting ultra-wealthy or Western-specific audiences
- Political or conflict-related content

Articles:
{articles_list}

Respond ONLY with valid JSON in this exact format (no other text):
{{
  "selected_index": <number 0-based>,
  "reason": "<one sentence why this article wins for Filipino audience>"
}}"""

# Heuristic scoring keywords tuned for Filipino side-income audience
VIRAL_KEYWORDS = [
    "side income", "passive income", "extra income", "financial freedom",
    "side hustle", "multiple income", "single income", "paycheck",
    "savings", "invest", "ofw", "overseas", "retire", "quit your job",
    "earn online", "work from home", "small business", "entrepreneur",
    "broke", "debt", "struggle", "survive", "inflation", "salary",
    "simple", "easy", "proven", "secret", "reveals", "study", "warning",
    "you should", "everyone", "most people", "shocking", "truth",
]

BLOCKED_KEYWORDS = [
    "war", "conflict", "attack", "killed", "shooting", "violence",
    "military", "explosion", "hostage", "terrorism", "casualties",
    "election fraud", "scandal", "arrested", "indicted",
]


def _is_suitable(article: dict) -> bool:
    title_lower = article["title"].lower()
    return not any(kw in title_lower for kw in BLOCKED_KEYWORDS)


def _build_articles_list(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a.get("summary"):
            lines.append(f"   Summary: {a['summary'][:150]}")
    return "\n".join(lines)


def _select_via_gemini(articles: list[dict]) -> dict | None:
    if not GEMINI_API_KEY:
        return None
    try:
        prompt = SELECTION_PROMPT.format(articles_list=_build_articles_list(articles))
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception as e:
        print(f"  ⚠️  Gemini selector error: {e}")
        print(f"  ⚠️  Gemini response: {resp.text[:300] if 'resp' in locals() else 'no response'}")
        return None


def _select_via_openrouter(articles: list[dict]) -> dict | None:
    if not OPENROUTER_API_KEY:
        return None
    try:
        prompt = SELECTION_PROMPT.format(articles_list=_build_articles_list(articles))
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
        text = resp.json()["choices"][0]["message"]["content"]
        text = text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception as e:
        print(f"  ⚠️  OpenRouter selector error: {e}")
        return None


def _heuristic_select(articles: list[dict]) -> dict:
    best_idx, best_score = 0, -1
    for i, a in enumerate(articles):
        title_lower = a["title"].lower()
        score = sum(1 for kw in VIRAL_KEYWORDS if kw in title_lower)
        if len(a["title"]) < 90:
            score += 1
        if score > best_score:
            best_score = score
            best_idx   = i
    return {"selected_index": best_idx, "reason": "heuristic keyword scoring"}


def select_best_article(articles: list[dict]) -> dict | None:
    if not articles:
        return None

    suitable = [a for a in articles if _is_suitable(a)]
    if not suitable:
        print("  ⚠️  No suitable articles after filtering — using all.")
        suitable = articles
    print(f"  📊 {len(suitable)}/{len(articles)} articles passed content filter.")

    result = None
    if GEMINI_API_KEY:
        print("  🤖 Using Gemini to select article...")
        result = _select_via_gemini(suitable)
    elif OPENROUTER_API_KEY:
        print("  🤖 Using OpenRouter to select article...")
        result = _select_via_openrouter(suitable)
    else:
        print("  ⚠️  No AI key set — using heuristic selection.")

    if not result:
        result = _heuristic_select(suitable)

    idx    = result.get("selected_index", 0)
    reason = result.get("reason", "")
    print(f"  ✅ Selected index {idx}: {reason}")

    if 0 <= idx < len(suitable):
        return suitable[idx]
    return suitable[0]


if __name__ == "__main__":
    test_articles = [
        {"title": "OFW in Singapore: How to Save $1,000 a Month on a Regular Salary", "source": "MoneySmart SG", "summary": ""},
        {"title": "5 Side Hustles Filipinos Are Using to Double Their Income in 2026",  "source": "Entrepreneur",  "summary": ""},
        {"title": "Why Most People Will Never Retire Comfortably (And What To Do Now)", "source": "CNBC",          "summary": ""},
    ]
    best = select_best_article(test_articles)
    print(f"\nSelected: {best['title']}")
