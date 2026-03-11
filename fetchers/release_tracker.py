"""Model Provider Release Notes — OpenAI, Anthropic, Google, Meta, Mistral.

Uses a combination of RSS feeds and direct blog page scraping as fallback.
Some providers don't have reliable RSS, so we check multiple sources.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser as dateparser

LOOKBACK_DAYS = 7

# ===== RSS Feeds that actually work =====
RSS_FEEDS = {
    "Mistral": "https://mistral.ai/feed.xml",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
}

# ===== Blog pages to scrape (when RSS doesn't exist/work) =====
BLOG_PAGES = [
    {
        "provider": "OpenAI",
        "url": "https://openai.com/news/",
        "selectors": ["article a", "a[href*='/index/']", "a[href*='/research/']"],
    },
    {
        "provider": "Anthropic",
        "url": "https://www.anthropic.com/research",
        "selectors": ["a[href*='/research/']", "article a"],
    },
    {
        "provider": "Google DeepMind",
        "url": "https://deepmind.google/discover/blog/",
        "selectors": ["a[href*='/blog/']", "article a"],
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; AI-Trend-Monitor/1.0)"}

RELEASE_KEYWORDS = [
    "release", "launch", "announc", "model", "api", "update", "new",
    "claude", "gpt", "gemini", "llama", "mistral", "agent", "tool",
    "safety", "eval", "benchmark", "enterprise", "deploy", "o1", "o3",
    "sonnet", "opus", "haiku", "flash", "pro", "reasoning", "thinking",
]


def fetch():
    """Fetch recent release-related posts from model providers."""
    items = []
    seen_urls = set()

    # ── Part 1: RSS feeds ──
    for provider, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)

            for entry in feed.entries[:10]:
                pub_date = _parse_date(entry)
                if pub_date and pub_date.replace(tzinfo=None) < cutoff:
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:400].strip()

                if link in seen_urls:
                    continue

                text = f"{title} {summary}".lower()
                if not any(kw in text for kw in RELEASE_KEYWORDS):
                    continue

                seen_urls.add(link)
                items.append({
                    "source": f"{provider} Release",
                    "category": "research",
                    "title": title,
                    "url": link,
                    "abstract": _clean_html(summary),
                    "published": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                    "tags": [provider],
                })
        except Exception as e:
            print(f"  [Releases] RSS failed for {provider}: {e}")

    # ── Part 2: Blog page scraping (fallback) ──
    for blog in BLOG_PAGES:
        provider = blog["provider"]
        try:
            resp = requests.get(blog["url"], headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            found = 0
            for selector in blog["selectors"]:
                for link_el in soup.select(selector)[:15]:
                    href = link_el.get("href", "")
                    if not href or href == "#":
                        continue

                    # Make absolute URL
                    if href.startswith("/"):
                        from urllib.parse import urlparse
                        base = urlparse(blog["url"])
                        href = f"{base.scheme}://{base.netloc}{href}"

                    if href in seen_urls:
                        continue

                    title = link_el.get_text(strip=True)
                    if len(title) < 10 or len(title) > 200:
                        continue

                    text = title.lower()
                    if not any(kw in text for kw in RELEASE_KEYWORDS):
                        continue

                    seen_urls.add(href)
                    items.append({
                        "source": f"{provider} Blog",
                        "category": "research",
                        "title": title,
                        "url": href,
                        "abstract": "",
                        "published": "",
                        "tags": [provider],
                    })
                    found += 1
                    if found >= 5:
                        break
                if found >= 5:
                    break

            if found > 0:
                print(f"  [Releases] {provider} blog: {found} posts")

        except Exception as e:
            print(f"  [Releases] Blog scrape failed for {provider}: {e}")

    print(f"  [Releases] Fetched {len(items)} total items")
    return items


def _parse_date(entry):
    for field in ["published", "updated", "created"]:
        val = getattr(entry, field, None)
        if val:
            try:
                return dateparser.parse(val)
            except Exception:
                pass
    return None


def _clean_html(text: str) -> str:
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()[:400]
