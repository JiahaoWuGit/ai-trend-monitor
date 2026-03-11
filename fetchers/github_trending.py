"""GitHub Trending AI Repos — Reliable multi-strategy fetcher.

Uses fewer queries with delays to avoid rate limiting.
Falls back to scraping if API fails.
"""

import requests
import os
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Mozilla/5.0 (Macintosh; AI-Trend-Monitor/1.0)",
}

# Optional: set GITHUB_TOKEN to avoid rate limits (10 req/min unauthenticated → 30 with token)
TOKEN = os.environ.get("GITHUB_TOKEN", "")
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# Keep queries to 4 to stay within rate limits
SEARCH_QUERIES = [
    "llm agent safety eval",
    "ai agent framework tool",
    "llm inference serving benchmark",
    "rag retrieval coding agent",
]

RELEVANCE_KEYWORDS = [
    "llm", "agent", "inference", "eval", "safety", "rag", "embedding",
    "transformer", "gpt", "claude", "gemini", "mistral", "llama",
    "langchain", "langgraph", "openai", "anthropic", "ai", "ml",
    "benchmark", "fine-tun", "lora", "rlhf", "alignment",
    "sandbox", "guardrail", "tool-use", "function-call", "mcp",
    "vllm", "ollama", "cursor", "copilot", "code", "reasoning",
]

MAX_PER_QUERY = 8
LOOKBACK_DAYS = 7


def fetch():
    """Fetch trending AI repos — API first, scraping fallback."""
    items = _fetch_via_api()

    if len(items) < 3:
        print("  [GitHub] API returned few results, trying scraping fallback...")
        items.extend(_fetch_via_scraping())

    # Dedup
    seen = set()
    unique = []
    for item in items:
        key = item["title"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # Sort by stars descending
    unique.sort(key=lambda x: _parse_stars(x.get("stars_today", "")), reverse=True)
    unique = unique[:20]

    print(f"  [GitHub Trending] Fetched {len(unique)} repos total")
    return unique


def _parse_stars(s):
    try:
        return int(s.replace("★", "").replace(",", "").strip() or "0")
    except (ValueError, AttributeError):
        return 0


def _fetch_via_api():
    """GitHub Search API with rate-limit-friendly delays."""
    items = []
    seen = set()
    date_cutoff = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    for i, query in enumerate(SEARCH_QUERIES):
        if i > 0:
            time.sleep(3)  # Respect rate limits

        try:
            params = {
                "q": f"{query} pushed:>{date_cutoff} stars:>50",
                "sort": "stars",
                "order": "desc",
                "per_page": MAX_PER_QUERY,
            }
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params=params,
                headers=HEADERS,
                timeout=15,
            )

            if resp.status_code == 403:
                remaining = resp.headers.get("X-RateLimit-Remaining", "?")
                print(f"  [GitHub] Rate limited (remaining={remaining}), stopping")
                break
            if resp.status_code != 200:
                print(f"  [GitHub] API {resp.status_code} for '{query}'")
                continue

            data = resp.json()
            for repo in data.get("items", []):
                name = repo.get("full_name", "")
                if name in seen:
                    continue
                seen.add(name)

                desc = repo.get("description", "") or ""
                stars = repo.get("stargazers_count", 0)
                language = repo.get("language", "") or ""
                updated = repo.get("pushed_at", "")[:10]

                items.append({
                    "source": "GitHub Trending",
                    "category": "research",
                    "title": name,
                    "url": repo.get("html_url", ""),
                    "abstract": desc[:500],
                    "stars_today": f"★ {stars:,}",
                    "language": language,
                    "published": updated,
                    "tags": _infer_tags(f"{name} {desc}".lower()),
                })

            print(f"  [GitHub] API query '{query}': {len(data.get('items', []))} results")

        except Exception as e:
            print(f"  [GitHub] API error for '{query}': {e}")

    return items


def _fetch_via_scraping():
    """Fallback: scrape GitHub trending page."""
    items = []
    seen = set()

    for url in [
        "https://github.com/trending?since=daily",
        "https://github.com/trending/python?since=daily",
    ]:
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": HEADERS["User-Agent"]},
                timeout=15,
            )
            if resp.status_code != 200:
                print(f"  [GitHub] Scraping got {resp.status_code} for {url}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try multiple selector patterns (GitHub changes these)
            rows = (
                soup.select("article.Box-row")
                or soup.select("article[class*='Box-row']")
                or soup.select("div[data-hpc] > article")
                or soup.select("main article")
            )

            for article in rows:
                link = article.select_one("h2 a") or article.select_one("h1 a")
                if not link:
                    continue
                repo_name = link.get("href", "").strip("/")
                if not repo_name or repo_name in seen:
                    continue

                p = article.select_one("p")
                desc = p.get_text(strip=True) if p else ""

                # Stars
                stars_text = ""
                for span in article.select("span"):
                    t = span.get_text(strip=True).lower()
                    if "star" in t and any(c.isdigit() for c in t):
                        stars_text = "".join(c for c in t if c.isdigit() or c == ",")
                        break

                text_blob = f"{repo_name} {desc}".lower()
                if not any(kw in text_blob for kw in RELEVANCE_KEYWORDS):
                    continue

                seen.add(repo_name)
                items.append({
                    "source": "GitHub Trending",
                    "category": "research",
                    "title": repo_name,
                    "url": f"https://github.com/{repo_name}",
                    "abstract": desc[:500],
                    "stars_today": f"★ {stars_text}" if stars_text else "",
                    "language": "",
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "tags": _infer_tags(text_blob),
                })

            print(f"  [GitHub] Scraping {url}: {len(items)} AI repos found")

        except Exception as e:
            print(f"  [GitHub] Scraping failed: {e}")

    return items


def _infer_tags(text):
    tag_map = {
        "Agent": ["agent", "agentic", "autonomous"],
        "Inference": ["inference", "serving", "vllm", "tgi", "deploy", "ollama"],
        "Eval": ["eval", "benchmark", "leaderboard", "arena"],
        "Safety": ["safety", "guardrail", "alignment", "moderation"],
        "RAG": ["rag", "retrieval", "embedding", "vector"],
        "Fine-tuning": ["fine-tun", "lora", "rlhf", "sft"],
        "Framework": ["langchain", "langgraph", "llamaindex", "framework"],
        "Tool Use": ["tool", "function call", "mcp"],
        "Coding": ["code", "coding", "copilot", "cursor", "ide"],
    }
    return [tag for tag, kws in tag_map.items() if any(kw in text for kw in kws)]
