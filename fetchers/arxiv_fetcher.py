"""arXiv Custom Feed — Agent safety, sandbox, permission, governance, eval, computer use, memory.

Full abstracts, up to 10 authors with affiliations, topic-based tagging.
"""

import arxiv
import re
from datetime import datetime, timedelta

# ===== 自定义关键词（按你的研究方向修改）=====
QUERIES = [
    'abs:"LLM agent" AND (safety OR sandbox OR permission)',
    'abs:"autonomous agent" AND (governance OR evaluation OR eval)',
    'abs:"computer use" AND (agent OR LLM OR language model)',
    'abs:"tool use" AND (safety OR permission OR sandbox) AND agent',
    'abs:agent AND (memory OR "persistent state") AND "language model"',
    'abs:"agent evaluation" OR abs:"agent benchmark"',
    'abs:"AI governance" AND (agent OR LLM)',
    'abs:"LLM agent" AND (tool OR function OR API)',
    'abs:"multi-agent" AND (safety OR coordination OR protocol)',
]

MAX_RESULTS_PER_QUERY = 8
LOOKBACK_DAYS = 4


# ===== Topic 定义（用于按主题分组）=====
TOPIC_DEFINITIONS = {
    "Safety & Alignment": {
        "keywords": ["safety", "safe ", "harmful", "risk", "alignment", "red team", "jailbreak", "adversarial", "attack"],
        "color": "#ef4444",
        "icon": "🛡️",
    },
    "Sandbox & Isolation": {
        "keywords": ["sandbox", "sandboxed", "isolated environment", "containeriz", "execution environment"],
        "color": "#f59e0b",
        "icon": "📦",
    },
    "Permission & Access Control": {
        "keywords": ["permission", "access control", "authorization", "privilege", "credential"],
        "color": "#d946ef",
        "icon": "🔐",
    },
    "Governance & Policy": {
        "keywords": ["governance", "regulation", "policy", "compliance", "audit", "accountab"],
        "color": "#10b981",
        "icon": "⚖️",
    },
    "Eval & Benchmarks": {
        "keywords": ["evaluation", "benchmark", "eval ", "leaderboard", "scoring", "metric", "test suite"],
        "color": "#f97316",
        "icon": "📊",
    },
    "Computer Use & GUI Agent": {
        "keywords": ["computer use", "gui agent", "web agent", "browser", "screenshot", "desktop", "ui agent"],
        "color": "#3b82f6",
        "icon": "🖥️",
    },
    "Memory & State": {
        "keywords": ["memory", "persistent state", "long-term", "retrieval augment", "episodic", "working memory"],
        "color": "#8b5cf6",
        "icon": "🧠",
    },
    "Tool Use & Function Calling": {
        "keywords": ["tool use", "tool-augmented", "function calling", "api call", "tool selection", "mcp"],
        "color": "#06b6d4",
        "icon": "🔧",
    },
    "Multi-Agent Systems": {
        "keywords": ["multi-agent", "multi agent", "cooperative", "coordination", "negotiat", "swarm"],
        "color": "#ec4899",
        "icon": "👥",
    },
    "Agent (General)": {
        "keywords": ["agent", "autonomous", "agentic"],
        "color": "#6366f1",
        "icon": "🤖",
    },
}


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

                # Extract authors (up to 10) with affiliations
                authors_info = []
                for a in result.authors[:10]:
                    name = a.name
                    # arxiv library stores affiliations in a.affiliations (list of str) if available
                    affiliations = getattr(a, 'affiliations', []) or []
                    if affiliations:
                        aff_str = ", ".join(affiliations[:2])  # max 2 affiliations per author
                        authors_info.append(f"{name} ({aff_str})")
                    else:
                        authors_info.append(name)

                # Full abstract (clean up)
                full_abstract = result.summary.replace("\n", " ").strip()
                full_abstract = re.sub(r'\s+', ' ', full_abstract)

                # Determine topic tags
                tags = _extract_tags(result.title + " " + result.summary)
                primary_topic = tags[0] if tags else "Agent (General)"

                items.append({
                    "source": "arXiv",
                    "category": "research",
                    "title": result.title.replace("\n", " ").strip(),
                    "url": result.entry_id,
                    "abstract": full_abstract,  # Full abstract
                    "authors": " · ".join(authors_info),  # Up to 10 authors
                    "author_count": len(result.authors),
                    "published": result.published.strftime("%Y-%m-%d"),
                    "tags": tags,
                    "primary_topic": primary_topic,
                    "arxiv_id": result.entry_id.split("/")[-1],
                })
        except Exception as e:
            print(f"  [arXiv] Query failed: {q[:50]}... — {e}")

    print(f"  [arXiv] Fetched {len(items)} papers")
    return items


def _extract_tags(text: str) -> list:
    """Extract topic tags, ordered by specificity (most specific first)."""
    text_lower = text.lower()
    tags = []

    # Check specific topics first, general topics last
    specificity_order = [
        "Safety & Alignment", "Sandbox & Isolation", "Permission & Access Control",
        "Governance & Policy", "Eval & Benchmarks", "Computer Use & GUI Agent",
        "Memory & State", "Tool Use & Function Calling", "Multi-Agent Systems",
        "Agent (General)",
    ]

    for topic_name in specificity_order:
        topic = TOPIC_DEFINITIONS[topic_name]
        if any(kw in text_lower for kw in topic["keywords"]):
            tags.append(topic_name)

    # Don't add "Agent (General)" if we already have more specific tags
    if len(tags) > 1 and "Agent (General)" in tags:
        tags.remove("Agent (General)")

    return tags if tags else ["Agent (General)"]


def get_topic_definitions():
    """Export topic definitions for use in email template rendering."""
    return TOPIC_DEFINITIONS
