"""Hugging Face Daily Papers — Community-curated top papers."""

import requests
from datetime import datetime

HF_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def fetch():
    """Fetch today's top papers from HF Daily Papers."""
    items = []
    try:
        resp = requests.get(HF_PAPERS_URL, timeout=15)
        resp.raise_for_status()
        papers = resp.json()

        for paper in papers[:15]:  # Top 15
            p = paper.get("paper", {})
            items.append({
                "source": "HF Daily Papers",
                "category": "research",
                "title": p.get("title", "").replace("\n", " ").strip(),
                "url": f"https://huggingface.co/papers/{p.get('id', '')}",
                "abstract": p.get("summary", "")[:500].replace("\n", " ").strip(),
                "authors": ", ".join(
                    a.get("name", "") for a in p.get("authors", [])[:3]
                ),
                "published": p.get("publishedAt", "")[:10],
                "tags": ["HF Daily"],
                "upvotes": paper.get("numUpvotes", 0),
            })
    except Exception as e:
        print(f"  [HF Papers] Fetch failed: {e}")

    print(f"  [HF Papers] Fetched {len(items)} papers")
    return items
