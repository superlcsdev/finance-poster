"""
ai_selector.py
Selects the most viral finance/side-income article for Filipino professional audience.
Tracks post history to prevent repeating articles within 30 days.
Uses Gemini → OpenRouter → heuristic fallback.
"""

import os
import json
import hashlib
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── History config ─────────────────────────────────────────────────────────────
HISTORY_FILE = "post_history.json"
HISTORY_DAYS = 30
MAX_HISTORY  = 200

SELECTION_PROMPT = """You are a finance content strategist for Facebook targeting Filipino professionals
— nurses, IT workers, engineers, architects, pharmacists — in Singapore and the Philippines.

Given these finance/business articles, select the ONE most likely to get high engagement.

Prioritise articles that:
- Speak to professionals with good salaries who aren't building wealth fast enough
- Highlight the gap between earning well and being financially free
- Cover side income, investing, or building wealth alongside a career
- Contain surprising stats or uncomfortable truths professionals can relate to
- Are relevant to someone earning SGD 3,000–6,000/month or PHP 50,000–120,000/month

Avoid:
- OFW hardship or remittance framing
- Articles targeting ultra-wealthy or very niche investors
- Political or conflict-related content
- Too technical or jargon-heavy for a general professional audience

Articles:
{articles_list}

Respond ONLY with valid JSON in this exact format (no other text):
{{
  "selected_index": <number 0-based>,
  "reason": "<one sentence why this article wins for Filipino professionals>"
}}"""

# Heuristic scoring keywords — tuned for professional wealth-building audience
VIRAL_KEYWORDS = [
    "side income", "passive income", "extra income", "financial freedom",
    "side hustle", "multiple income", "invest", "salary", "retire",
    "wealth", "savings", "income stream", "entrepreneur", "build wealth",
    "financial independence", "stock", "real estate", "debt free",
    "net worth", "study", "reveals", "warning", "truth", "most people",
    "professionals", "engineer", "nurse", "career", "high earner",
]

BLOCKED_KEYWORDS = [
    "war", "conflict", "attack", "killed", "shooting", "violence",
    "military", "explosion", "hostage", "terrorism", "casualties",
    "election fraud", "scandal", "arrested", "indicted",
]


# ── History management ─────────────────────────────────────────────────────────

def _article_hash(title: str) -> str:
    return hashlib.md5(title.lower().strip().encode()).hexdigest()[:12]


def _load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(history: list):
    cutoff = (datetime.now() - timedelta(days=HISTORY_DAYS)).isoformat()
    recent = [h for h in history if h.get("date", "") >= cutoff]
    recent = recent[-MAX_HISTORY:]
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(recent, f, indent=2)
    except Exception as e:
        print(f"  ⚠️  Could not save history: {e}")


def save_posted_article(article: dict):
    """Call after successfully posting to record the article."""
    history = _load_history()
    history.append({
        "hash":  _article_hash(article["title"]),
        "title": article["title"][:100],
        "date":  datetime.now().isoformat(),
    })
    _save_history(history)
    print(f"  📝 Saved to history: {article['title'][:60]}...")


def _filter_already_posted(articles: list) -> list:
    """Remove articles posted within the last HISTORY_DAYS days."""
    history     = _load_history()
    cutoff      = (datetime.now() - timedelta(days=HISTORY_DAYS)).isoformat()
    recent_hash = {h["hash"] for h in history if h.get("date", "") >= cutoff}

    filtered = [a for a in articles if _article_hash(a["title"]) not in recent_hash]
    removed  = len(articles) - len(filtered)

    if removed:
        print(f"  🚫 Filtered out {removed} recently posted articles.")
    if not filtered:
        print("  ⚠️  All articles were recently posted — resetting filter for today.")
        return articles

    return filtered


# ── Article selection ──────────────────────────────────────────────────────────

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

    # Filter blocked content
    suitable = [a for a in articles if _is_suitable(a)]
    if not suitable:
        print("  ⚠️  No suitable articles after content filter — using all.")
        suitable = articles
    print(f"  📊 {len(suitable)}/{len(articles)} articles passed content filter.")

    # Filter already posted
    fresh = _filter_already_posted(suitable)

    result = None
    if GEMINI_API_KEY:
        print("  🤖 Using Gemini to select article...")
        result = _select_via_gemini(fresh)
    elif OPENROUTER_API_KEY:
        print("  🤖 Using OpenRouter to select article...")
        result = _select_via_openrouter(fresh)
    else:
        print("  ⚠️  No AI key set — using heuristic selection.")

    if not result:
        result = _heuristic_select(fresh)

    idx    = result.get("selected_index", 0)
    reason = result.get("reason", "")
    print(f"  ✅ Selected index {idx}: {reason}")

    if 0 <= idx < len(fresh):
        return fresh[idx]
    return fresh[0]


if __name__ == "__main__":
    test_articles = [
        {"title": "Why Engineers With Good Salaries Still Can't Retire Early", "source": "Forbes", "summary": ""},
        {"title": "5 Income Streams Every Professional Should Build in Their 30s", "source": "Entrepreneur", "summary": ""},
        {"title": "The Investment Mistake Most High-Earning Nurses Make", "source": "MoneySmart SG", "summary": ""},
    ]
    best = select_best_article(test_articles)
    print(f"\nSelected: {best['title']}")
    save_posted_article(best)
    print("History saved.")
