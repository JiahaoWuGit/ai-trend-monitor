"""arXiv Custom Feed — Agent safety, sandbox, permission, governance, eval, computer use, memory"""

import arxiv
from datetime import datetime, timedelta
# from typing import list

# ===== 自定义关键词（按你的研究方向修改）=====
QUERIES = [
    'abs:"LLM agent" AND (safety OR sandbox OR permission)',
    'abs:"autonomous agent" AND (governance OR evaluation OR eval)',
    'abs:"computer use" AND (agent OR LLM OR language model)',
    'abs:"tool use" AND (safety OR permission OR sandbox) AND agent',
    'abs:agent AND (memory OR "persistent state") AND "language model"',
    'abs:"agent evaluation" OR abs:"agent benchmark"',
    'abs:"AI governance" AND (agent OR LLM)',
]

MAX_RESULTS_PER_QUERY = 5
LOOKBACK_DAYS = 2


def fetch():
    """Fetch recent arXiv papers matching agent-related queries."""
    items = []
    seen_ids = set()
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)

    client = arxiv.Client()

    for q in QUERIES:
        try:
            search = arxiv.Search(
                query=q,
                max_results=MAX_RESULTS_PER_QUERY,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            for result in client.results(search):
                if result.entry_id in seen_ids:
                    continue
                if result.published.replace(tzinfo=None) < cutoff:
                    continue
                seen_ids.add(result.entry_id)
                items.append({
                    "source": "arXiv",
                    "category": "research",
                    "title": result.title.replace("\n", " ").strip(),
                    "url": result.entry_id,
                    "abstract": result.summary[:500].replace("\n", " ").strip(),
                    "authors": ", ".join(a.name for a in result.authors[:3]),
                    "published": result.published.strftime("%Y-%m-%d"),
                    "tags": _extract_tags(result.title + " " + result.summary),
                })
        except Exception as e:
            print(f"  [arXiv] Query failed: {q[:50]}... — {e}")

    print(f"  [arXiv] Fetched {len(items)} papers")
    return items


def _extract_tags(text: str) -> list:
    """Simple keyword-based tagging."""
    tag_keywords = {
        "Safety": ["safety", "safe ", "harmful", "risk"],
        "Sandbox": ["sandbox", "sandboxed", "isolated environment"],
        "Permission": ["permission", "access control", "authorization"],
        "Governance": ["governance", "regulation", "policy", "compliance"],
        "Eval": ["evaluation", "benchmark", "eval ", "leaderboard"],
        "Computer Use": ["computer use", "gui agent", "web agent", "browser"],
        "Memory": ["memory", "persistent state", "long-term", "retrieval"],
        "Tool Use": ["tool use", "tool-augmented", "function calling"],
        "Agent": ["agent", "autonomous", "agentic"],
    }
    text_lower = text.lower()
    return [tag for tag, keywords in tag_keywords.items()
            if any(kw in text_lower for kw in keywords)]
