"""
news_fetcher.py
Fetches top personal finance, side income, and entrepreneurship articles.
Tuned for Filipino audience in Singapore and Philippines.
"""

import os
import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Free RSS feeds — no key needed
RSS_FEEDS = [
    # Global personal finance
    {"url": "https://feeds.feedburner.com/entrepreneur/latest",             "source": "Entrepreneur"},
    {"url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",         "source": "CNBC Finance"},
    {"url": "https://feeds.forbes.com/forbesmagazine/tags/entrepreneur",    "source": "Forbes"},
    {"url": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=investopedia_rss_articles", "source": "Investopedia"},
    {"url": "https://www.thebalancemoney.com/rss",                          "source": "The Balance"},

    # Singapore / Asia focused
    {"url": "https://www.businesstimes.com.sg/rss/wealth",                  "source": "Business Times SG"},
    {"url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511", "source": "CNA Business"},
    {"url": "https://blog.moneysmart.sg/feed/",                             "source": "MoneySmart SG"},

    # Philippines focused
    {"url": "https://businessmirror.com.ph/feed/",                          "source": "Business Mirror PH"},
    {"url": "https://www.philstar.com/rss/business",                        "source": "PhilStar Business"},
    {"url": "https://mb.com.ph/category/business/feed/",                    "source": "Manila Bulletin Business"},
]

MAX_ARTICLES_PER_FEED = 5
MAX_TOTAL_ARTICLES    = 25

# Keywords to prioritise for Filipino OFW/side income audience
PRIORITY_KEYWORDS = [
    "side income", "passive income", "extra income", "financial freedom",
    "ofw", "remittance", "overseas", "savings", "investment", "entrepreneur",
    "online business", "freelance", "work from home", "multiple income",
    "retire early", "financial independence", "side hustle", "small business",
    "stock market", "real estate", "crypto", "inflation", "salary",
]

# Keywords to block — avoid political/conflict topics
BLOCKED_KEYWORDS = [
    "war", "conflict", "attack", "killed", "shooting", "violence",
    "military", "explosion", "hostage", "terrorism", "casualties",
    "election fraud", "scandal", "arrested", "indicted",
]


def _parse_feed(feed_info: dict) -> list[dict]:
    articles = []
    try:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            title = entry.get("title", "").strip()
            if not title:
                continue
            articles.append({
                "title":    title,
                "url":      entry.get("link", ""),
                "summary":  entry.get("summary", "")[:300],
                "source":   feed_info["source"],
                "category": "finance",
                "published": entry.get("published", ""),
            })
    except Exception as e:
        print(f"  ⚠️  RSS feed error ({feed_info['source']}): {e}")
    return articles


def _fetch_newsapi() -> list[dict]:
    if not NEWS_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        "side income OR passive income OR financial freedom OR entrepreneurship",
                "language": "en",
                "sortBy":   "popularity",
                "pageSize": 10,
                "apiKey":   NEWS_API_KEY,
            },
            timeout=15,
        )
        articles = []
        for a in resp.json().get("articles", []):
            if not a.get("title") or a["title"] == "[Removed]":
                continue
            articles.append({
                "title":    a["title"].strip(),
                "url":      a.get("url", ""),
                "summary":  (a.get("description") or "")[:300],
                "source":   a.get("source", {}).get("name", "NewsAPI"),
                "category": "finance",
                "published": a.get("publishedAt", ""),
            })
        return articles
    except Exception as e:
        print(f"  ⚠️  NewsAPI error: {e}")
        return []


def _score_article(article: dict) -> int:
    """Score article relevance for Filipino side-income audience."""
    title_lower   = (article["title"] + " " + article["summary"]).lower()
    # Block unsuitable articles
    if any(kw in title_lower for kw in BLOCKED_KEYWORDS):
        return -1
    # Score by priority keywords
    return sum(1 for kw in PRIORITY_KEYWORDS if kw in title_lower)


def fetch_top_articles() -> list[dict]:
    all_articles = []

    for feed in RSS_FEEDS:
        articles = _parse_feed(feed)
        all_articles.extend(articles)
        print(f"  📰 {feed['source']}: {len(articles)} articles")

    if NEWS_API_KEY:
        na = _fetch_newsapi()
        all_articles.extend(na)
        print(f"  📰 NewsAPI: {len(na)} articles")

    # Deduplicate
    seen, unique = set(), []
    for a in all_articles:
        key = a["title"].lower()[:60]
        if key not in seen and a["title"]:
            seen.add(key)
            unique.append(a)

    # Sort by relevance score, remove blocked
    scored = [(a, _score_article(a)) for a in unique]
    scored = [(a, s) for a, s in scored if s >= 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    result = [a for a, _ in scored]

    print(f"  📊 Total unique articles after scoring: {len(result)}")
    return result[:MAX_TOTAL_ARTICLES]


if __name__ == "__main__":
    articles = fetch_top_articles()
    for i, a in enumerate(articles, 1):
        print(f"{i:2}. [{a['source']}] {a['title'][:80]}")
