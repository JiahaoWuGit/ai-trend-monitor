"""Commercial / Startup Tech Blogs + Report Monitors.

Covers: RSS blog feeds + page-scrape monitors for YC, Stanford AI Index.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser as dateparser

# ===== Blog RSS Feeds =====
# 格式：(名称, RSS URL, 分类标签)
BLOG_FEEDS = [
    # --- Tier 1: Enterprise AI Reports ---
    ("Anthropic Blog", "https://www.anthropic.com/rss.xml", ["Enterprise", "Safety", "Agent Infra"]),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml", ["Enterprise", "Infrastructure"]),
    ("Together AI Blog", "https://www.together.ai/blog/rss.xml", ["Open Models", "Inference", "Infra"]),

    # --- Tier 2: Leading AI Startups ---
    ("Cursor Blog", "https://www.cursor.com/blog/rss.xml", ["Coding Agent", "IDE"]),
    ("Perplexity Blog", "https://blog.perplexity.ai/feed", ["Search", "RAG"]),
    ("Cohere Blog", "https://cohere.com/blog/rss.xml", ["Enterprise RAG", "Embeddings"]),
    ("Mistral Blog", "https://mistral.ai/feed.xml", ["Open Models", "Enterprise"]),
    ("Replit Blog", "https://blog.replit.com/feed.xml", ["Coding Agent", "Platform"]),
    ("LangChain Blog", "https://blog.langchain.dev/rss/", ["Agent Infra", "Framework"]),
    ("Anyscale Blog", "https://www.anyscale.com/blog/rss.xml", ["Distributed", "Ray", "Infra"]),
    ("Modal Blog", "https://modal.com/blog/feed.xml", ["GPU Infra", "Serverless"]),
    ("Vercel AI Blog", "https://vercel.com/blog/rss.xml", ["AI SDK", "Developer Tools"]),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", ["Open Source", "Models"]),

    # --- Tier 3: Research-Adjacent Startups ---
    ("Weights & Biases", "https://wandb.ai/fully-connected/rss.xml", ["MLOps", "Eval"]),
    ("Scale AI Blog", "https://scale.com/blog/rss.xml", ["Data", "RLHF", "Enterprise"]),
]

# ===== Page Monitors (no RSS — scrape for new content) =====
# 这些源没有 RSS feed，通过定期抓取页面检测更新
PAGE_MONITORS = [
    {
        "name": "YC Requests for Startups",
        "url": "https://www.ycombinator.com/blog",
        "backup_urls": [
            "https://www.ycombinator.com/rfs",
        ],
        "tags": ["AI-native", "Fintech", "Industrial"],
        "keywords": ["request for startups", "rfs", "ai-native", "startup", "batch", "yc"],
        "selectors": ["a[href*='rfs']", "a[href*='/blog/']", "h2 a", "h3 a"],
        "icon": "🚀",
    },
    {
        "name": "Stanford AI Index",
        "url": "https://aiindex.stanford.edu/report/",
        "backup_urls": [
            "https://hai.stanford.edu/news",
        ],
        "tags": ["Investment", "Adoption", "Policy"],
        "keywords": ["ai index", "artificial intelligence index", "ai report", "ai investment", "ai policy"],
        "selectors": ["a[href*='report']", "a[href*='ai-index']", "h2 a", "h3 a", "article a"],
        "icon": "🎓",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; AI-Trend-Monitor/1.0)"}

# 只看最近几天
LOOKBACK_DAYS = 7

# AI 相关性过滤
AI_KEYWORDS = [
    "ai", "llm", "agent", "model", "gpt", "claude", "inference", "rag",
    "fine-tun", "benchmark", "eval", "safety", "enterprise", "deploy",
    "embedding", "transformer", "gpu", "training", "prompt", "workflow",
    "automat", "copilot", "assistant", "reasoning", "tool use", "mcp",
]


def fetch():
    """Fetch recent posts from commercial/startup AI blogs."""
    items = []
    seen_urls = set()

    for blog_name, feed_url, default_tags in BLOG_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            count = 0

            for entry in feed.entries[:8]:
                # Parse date
                pub_date = None
                for date_field in ["published", "updated", "created"]:
                    if hasattr(entry, date_field) and getattr(entry, date_field):
                        try:
                            pub_date = dateparser.parse(getattr(entry, date_field))
                            break
                        except Exception:
                            pass

                cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
                if pub_date and pub_date.replace(tzinfo=None) < cutoff:
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:400].strip()

                if link in seen_urls:
                    continue

                # Relevance check (relaxed — most of these blogs are AI-focused)
                text = f"{title} {summary}".lower()
                is_ai_blog = any(kw in blog_name.lower() for kw in ["ai", "anthropic", "openai", "cursor", "perplexity", "cohere", "mistral", "replit", "langchain", "modal", "hugging"])
                if not is_ai_blog and not any(kw in text for kw in AI_KEYWORDS):
                    continue

                seen_urls.add(link)
                items.append({
                    "source": blog_name,
                    "category": "commercial",
                    "title": title,
                    "url": link,
                    "abstract": _clean_html(summary),
                    "published": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                    "tags": default_tags,
                })
                count += 1

            if count > 0:
                print(f"  [Blogs] {blog_name}: {count} posts")

        except Exception as e:
            print(f"  [Blogs] Failed {blog_name}: {e}")

    print(f"  [Startup Blogs] Fetched {len(items)} RSS posts")

    # ── Part 2: Page Monitors (YC, Stanford) ──
    for monitor in PAGE_MONITORS:
        monitor_items = _fetch_page_monitor(monitor, seen_urls)
        items.extend(monitor_items)

    print(f"  [Commercial Total] {len(items)} items")
    return items


def _fetch_page_monitor(monitor: dict, seen_urls: set) -> list:
    """Scrape a page for new links matching keywords."""
    items = []
    name = monitor["name"]

    all_urls = [monitor["url"]] + monitor.get("backup_urls", [])

    for page_url in all_urls:
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            found = 0

            for selector in monitor["selectors"]:
                for link_el in soup.select(selector)[:20]:
                    href = link_el.get("href", "")
                    if not href or href == "#":
                        continue

                    # Make absolute URL
                    if href.startswith("/"):
                        from urllib.parse import urlparse
                        base = urlparse(page_url)
                        href = f"{base.scheme}://{base.netloc}{href}"

                    if href in seen_urls:
                        continue

                    title = link_el.get_text(strip=True)
                    if len(title) < 8 or len(title) > 250:
                        continue

                    # Keyword relevance check
                    text = f"{title} {href}".lower()
                    if not any(kw in text for kw in monitor["keywords"] + AI_KEYWORDS[:10]):
                        continue

                    seen_urls.add(href)
                    items.append({
                        "source": name,
                        "category": "commercial",
                        "title": title,
                        "url": href,
                        "abstract": "",
                        "published": "",
                        "tags": monitor["tags"],
                    })
                    found += 1
                    if found >= 5:
                        break
                if found >= 5:
                    break

            if found > 0:
                print(f"  [Monitor] {name}: {found} items from {page_url}")
                break  # Got results, skip backup URLs

        except Exception as e:
            print(f"  [Monitor] {name} failed ({page_url[:50]}...): {e}")

    return items


def _clean_html(text: str) -> str:
    """Strip basic HTML tags from RSS summaries."""
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:400]
