"""Model Provider Release Notes — OpenAI, Anthropic, Google, Meta, Mistral changelogs."""

import feedparser
from datetime import datetime, timedelta
from dateutil import parser as dateparser

# ===== RSS / Atom / Blog feeds for major providers =====
PROVIDER_FEEDS = {
    "OpenAI": [
        "https://openai.com/blog/rss.xml",
        "https://platform.openai.com/docs/changelog/rss.xml",
    ],
    "Anthropic": [
        "https://www.anthropic.com/rss.xml",
        "https://docs.anthropic.com/en/docs/about-claude/changelog.xml",
    ],
    "Google DeepMind": [
        "https://blog.google/technology/ai/rss/",
        "https://deepmind.google/blog/rss.xml",
    ],
    "Meta AI": [
        "https://ai.meta.com/blog/rss/",
    ],
    "Mistral": [
        "https://mistral.ai/feed.xml",
    ],
}

# 只看最近几天的更新
LOOKBACK_DAYS = 3

# 过滤关键词（release / model / API 相关）
RELEASE_KEYWORDS = [
    "release", "launch", "announc", "model", "api", "update", "new",
    "claude", "gpt", "gemini", "llama", "mistral", "agent", "tool",
    "safety", "eval", "benchmark", "enterprise", "deploy",
]


def fetch():
    """Fetch recent release-related posts from model provider blogs/changelogs."""
    items = []
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)

    for provider, feeds in PROVIDER_FEEDS.items():
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:
                    # Parse date
                    pub_date = None
                    for date_field in ["published", "updated", "created"]:
                        if hasattr(entry, date_field) and getattr(entry, date_field):
                            try:
                                pub_date = dateparser.parse(getattr(entry, date_field))
                                break
                            except Exception:
                                pass

                    if pub_date and pub_date.replace(tzinfo=None) < cutoff:
                        continue

                    title = entry.get("title", "").strip()
                    summary = entry.get("summary", "")[:400].strip()
                    link = entry.get("link", "")

                    # Relevance filter
                    text = f"{title} {summary}".lower()
                    if not any(kw in text for kw in RELEASE_KEYWORDS):
                        continue

                    items.append({
                        "source": f"{provider} Release",
                        "category": "research",
                        "title": title,
                        "url": link,
                        "abstract": summary,
                        "published": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                        "tags": [provider],
                    })
            except Exception as e:
                print(f"  [Releases] Failed {provider} ({feed_url[:40]}...): {e}")

    print(f"  [Releases] Fetched {len(items)} items")
    return items
