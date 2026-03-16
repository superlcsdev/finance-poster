# 💰 Finance & Income Freedom Auto-Poster

Automated Facebook posting pipeline that shares finance and side-income content 
targeted at Filipinos in Singapore and the Philippines, with a subtle nudge 
toward building multiple income streams.

## Who this is for

- OFWs and overseas workers thinking about financial security
- Employees relying on a single income who want to do more
- Anyone in Singapore or the Philippines exploring side income options

## Content strategy

Posts are automatically selected to resonate with:
- Financial struggle and aspiration relatable to Filipinos
- Side income, passive income, and financial freedom topics
- Local context: cost of living, OFW life, sending money home
- Subtle (never pushy) nudges toward exploring alternative income

## Architecture

```
news_fetcher.py     → fetch finance articles (RSS + optional NewsAPI)
ai_selector.py      → Gemini picks most viral article for Filipino audience
hook_writer.py      → writes relatable hook caption with subtle side-income nudge
image_generator.py  → Pollinations.ai wealth/freedom background + Pillow text overlay
fb_poster.py        → posts to Facebook Page, article URL as first comment
main.py             → orchestrates all steps
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Test image generation only (no keys needed)
python image_generator.py

# 4. Test full pipeline without posting
python main.py --dry-run

# 5. Run full pipeline
python main.py
```

## API Keys

All keys are shared with your health poster repo — no new signups needed!

| Key | Required for |
|-----|-------------|
| `GEMINI_API_KEY` | AI article selection + hook writing |
| `FB_PAGE_ID` | Facebook posting |
| `FB_ACCESS_TOKEN` | Facebook posting |
| `HF_API_TOKEN` | Image generation fallback |
| `NEWS_API_KEY` | Extra article sources (optional) |

## Posting schedule

Runs daily at **7:00 PM SGT** — prime evening browsing time for Filipino workers 
finishing their shift and scrolling Facebook.

Health poster runs at 9:00 AM, so both posts never clash on the same page.

## GitHub Secrets

Add the same secrets from your health poster repo:
- `GEMINI_API_KEY`
- `FB_PAGE_ID`
- `FB_ACCESS_TOKEN`
- `HF_API_TOKEN`
- `NEWS_API_KEY` (optional)
