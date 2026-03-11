"""Hugging Face Daily Papers — Community-curated top papers with full details."""

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

            # Authors (up to 10)
            raw_authors = p.get("authors", [])[:10]
            author_names = []
            for a in raw_authors:
                name = a.get("name", "")
                if name:
                    author_names.append(name)

            author_str = " · ".join(author_names)
            author_count = len(p.get("authors", []))

            # Full abstract
            abstract = p.get("summary", "").replace("\n", " ").strip()

            items.append({
                "source": "HF Daily Papers",
                "category": "research",
                "title": p.get("title", "").replace("\n", " ").strip(),
                "url": f"https://huggingface.co/papers/{p.get('id', '')}",
                "abstract": abstract,  # Full abstract
                "authors": author_str,
                "author_count": author_count,
                "published": p.get("publishedAt", "")[:10],
                "tags": ["HF Daily"],
                "upvotes": paper.get("numUpvotes", 0),
            })
    except Exception as e:
        print(f"  [HF Papers] Fetch failed: {e}")

    print(f"  [HF Papers] Fetched {len(items)} papers")
    return items
