"""
main.py
Finance & Income Freedom Auto-Poster pipeline.

Flow:
  1. news_fetcher.py    — fetch finance/business articles
  2. ai_selector.py     — pick most viral article for Filipino audience
  3. hook_writer.py     — write Facebook hook caption
  4. image_generator.py — generate aspirational wealth image
  5. fb_poster.py       — post to Facebook Page, article URL as first comment

Run modes:
  python main.py             → full pipeline
  python main.py --dry-run   → everything except FB post
  python main.py --image-only → image generation test only
"""

import argparse
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from news_fetcher    import fetch_top_articles
from ai_selector     import select_best_article, save_posted_article
from hook_writer     import generate_hook
from image_generator import create_post_image

try:
    from fb_poster import post_to_facebook
    FB_AVAILABLE = True
except ImportError:
    FB_AVAILABLE = False

OUTPUT_DIR = "output_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_pipeline(dry_run: bool = False, image_only: bool = False):
    print("\n" + "=" * 60)
    print("  💰  Finance & Income Freedom Auto-Poster")
    print("  📅  " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 60)

    # ── Step 1: Fetch articles ────────────────────────────────────
    print("\n[1/5] Fetching top finance articles...")
    articles = fetch_top_articles()
    if not articles:
        print("❌ No articles fetched. Exiting.")
        sys.exit(1)
    print(f"  ✅ {len(articles)} articles fetched.")

    # ── Step 2: Select best article ───────────────────────────────
    print("\n[2/5] AI selecting most viral article for Filipino audience...")
    best = select_best_article(articles)
    if not best:
        best = articles[0]
        print("  ⚠️  AI selection failed — using first article as fallback.")
    print(f"  ✅ Selected: \"{best['title'][:70]}\"")
    print(f"     Source  : {best.get('source', 'unknown')}")
    print(f"     URL     : {best.get('url', '')}")

    if image_only:
        _test_image_only(best)
        return

    # ── Step 3: Generate hook caption ────────────────────────────
    print("\n[3/5] Generating Facebook hook caption...")
    hook = generate_hook(best)
    print(f"  ✅ Hook ready ({len(hook)} chars)")
    print(f"  📝 {hook[:120]}...")

    # ── Step 4: Generate post image ──────────────────────────────
    print("\n[4/5] Generating post image...")
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(OUTPUT_DIR, f"finance_post_{timestamp}.jpg")
    result_path = create_post_image(
        headline    = best["title"],
        output_path = image_path,
        category    = best.get("category", "finance"),
        source      = best.get("source", ""),
        tag         = "MONEY & FREEDOM",
    )
    if not result_path:
        print("❌ Image generation failed. Exiting.")
        sys.exit(1)

    # ── Step 5: Post to Facebook ──────────────────────────────────
    if dry_run:
        print("\n[5/5] DRY RUN — skipping Facebook post.")
        print(f"  📄 Caption : {hook[:120]}...")
        print(f"  🖼️  Image   : {result_path}")
        print(f"  🔗 URL     : {best.get('url', '')}")
        print("\n✅ Dry run complete!")
        return

    print("\n[5/5] Posting to Facebook...")
    if not FB_AVAILABLE:
        print("  ⚠️  fb_poster.py not available — skipping.")
        return

    success = post_to_facebook(
        image_path  = result_path,
        caption     = hook,
        article_url = best.get("url", ""),
    )
    if success:
        print("  🎉 Posted successfully to Facebook!")
        save_posted_article(best)
    else:
        print("  ❌ Facebook post failed.")


def _test_image_only(article: dict):
    print("\n[IMAGE TEST] Generating test image...")
    path = os.path.join(OUTPUT_DIR, "test_finance_image.jpg")
    create_post_image(
        headline    = article["title"],
        output_path = path,
        category    = article.get("category", "finance"),
        source      = article.get("source", ""),
        tag         = "MONEY & FREEDOM",
    )
    print(f"\n✅ Image saved to: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finance & Income Freedom Auto-Poster")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--image-only", action="store_true")
    args = parser.parse_args()
    run_pipeline(dry_run=args.dry_run, image_only=args.image_only)
