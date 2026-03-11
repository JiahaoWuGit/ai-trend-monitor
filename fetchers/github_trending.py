"""GitHub Trending — AI, Agent, Inference, Eval, Safety repos."""

import requests
from bs4 import BeautifulSoup

# 追踪的 topic 关键词
TOPICS = [
    "machine-learning",
    "deep-learning",
    "llm",
    "ai-agent",
    "inference",
]

TRENDING_URL = "https://github.com/trending"
HEADERS = {"User-Agent": "Mozilla/5.0 (AI-Trend-Monitor/1.0)"}

# 额外过滤关键词，确保相关性
RELEVANCE_KEYWORDS = [
    "llm", "agent", "inference", "eval", "safety", "rag", "embedding",
    "transformer", "gpt", "claude", "gemini", "mistral", "llama",
    "langchain", "langgraph", "openai", "anthropic", "ai", "ml",
    "benchmark", "fine-tun", "lora", "rlhf", "alignment",
    "sandbox", "guardrail", "tool-use", "function-call",
]


def fetch():
    """Scrape GitHub trending repos and filter for AI/Agent relevance."""
    items = []
    seen = set()

    # Fetch general trending + language-specific
    urls = [
        f"{TRENDING_URL}?since=daily",
        f"{TRENDING_URL}/python?since=daily",
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for article in soup.select("article.Box-row"):
                # Repo name
                h2 = article.select_one("h2 a")
                if not h2:
                    continue
                repo_name = h2.get("href", "").strip("/")
                if repo_name in seen:
                    continue

                # Description
                p = article.select_one("p")
                desc = p.get_text(strip=True) if p else ""

                # Stars today
                spans = article.select("span.d-inline-block.float-sm-right")
                stars_today = ""
                if spans:
                    stars_today = spans[0].get_text(strip=True)

                # Language
                lang_span = article.select_one("[itemprop='programmingLanguage']")
                language = lang_span.get_text(strip=True) if lang_span else ""

                # Relevance check
                text_blob = f"{repo_name} {desc}".lower()
                if not any(kw in text_blob for kw in RELEVANCE_KEYWORDS):
                    continue

                seen.add(repo_name)
                items.append({
                    "source": "GitHub Trending",
                    "category": "research",
                    "title": repo_name,
                    "url": f"https://github.com/{repo_name}",
                    "abstract": desc[:300],
                    "stars_today": stars_today,
                    "language": language,
                    "tags": _infer_tags(text_blob),
                })
        except Exception as e:
            print(f"  [GitHub] Fetch failed for {url}: {e}")

    print(f"  [GitHub Trending] Fetched {len(items)} repos")
    return items


def _infer_tags(text: str) -> list:
    tag_map = {
        "Agent": ["agent", "agentic", "autonomous"],
        "Inference": ["inference", "serving", "vllm", "tgi", "deploy"],
        "Eval": ["eval", "benchmark", "leaderboard", "arena"],
        "Safety": ["safety", "guardrail", "alignment", "moderation"],
        "RAG": ["rag", "retrieval", "embedding", "vector"],
        "Fine-tuning": ["fine-tun", "lora", "rlhf", "sft"],
        "Framework": ["langchain", "langgraph", "llamaindex", "framework"],
    }
    return [tag for tag, kws in tag_map.items() if any(kw in text for kw in kws)]
