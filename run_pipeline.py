#!/usr/bin/env python3
"""
PhD AI/LLM/Agent Trend Monitor — Daily Pipeline

流程: 采集 → 去重 → Claude 摘要 → 发送邮件

用法:
    python run_pipeline.py              # 完整流程
    python run_pipeline.py --fetch-only # 只采集，不发邮件
    python run_pipeline.py --local      # 采集+摘要，保存本地 HTML（不发邮件）
"""

import sys
import json
import os
from datetime import datetime

# ── Fetchers ──
from fetchers import arxiv_fetcher, hf_papers, github_trending, release_tracker, startup_blogs
from summarizer import summarize
from send_email import send


def dedup(items: list) -> list:
    """Remove duplicate items based on title similarity (exact match for now)."""
    seen = set()
    result = []
    for item in items:
        key = item["title"].lower().strip()[:80]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def run(fetch_only=False, local_only=False):
    print(f"\n{'='*60}")
    print(f"  AI Trend Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # ── Step 1: Fetch ──
    print("[1/4] 📡 Fetching data sources...\n")

    research_items = []
    commercial_items = []

    # Research sources
    print("  ── Research ──")
    research_items.extend(arxiv_fetcher.fetch())
    research_items.extend(hf_papers.fetch())
    research_items.extend(github_trending.fetch())
    research_items.extend(release_tracker.fetch())

    # Commercial sources
    print("\n  ── Commercial ──")
    commercial_items.extend(startup_blogs.fetch())

    # ── Step 2: Dedup ──
    print(f"\n[2/4] 🧹 Deduplicating...")
    r_before, c_before = len(research_items), len(commercial_items)
    research_items = dedup(research_items)
    commercial_items = dedup(commercial_items)
    print(f"  Research: {r_before} → {len(research_items)}")
    print(f"  Commercial: {c_before} → {len(commercial_items)}")

    # Save raw data
    os.makedirs("output", exist_ok=True)
    raw_path = f"output/raw_{datetime.now().strftime('%Y%m%d')}.json"
    with open(raw_path, "w") as f:
        json.dump({
            "date": datetime.now().isoformat(),
            "research": research_items,
            "commercial": commercial_items,
        }, f, ensure_ascii=False, indent=2)
    print(f"  Raw data saved → {raw_path}")

    if fetch_only:
        print("\n✅ Fetch complete (--fetch-only mode)")
        return

    # ── Step 3: Summarize ──
    print(f"\n[3/4] 🧠 Generating AI summary...")
    digest = summarize(research_items, commercial_items)

    if local_only:
        # Save HTML locally without sending
        from send_email import _save_local
        _save_local(digest)
        print("\n✅ Digest saved locally (--local mode)")
        return

    # ── Step 4: Send ──
    print(f"\n[4/4] 📬 Sending email digest...")
    send(digest)

    print(f"\n{'='*60}")
    print(f"  ✅ Pipeline complete!")
    print(f"  Research: {len(research_items)} items")
    print(f"  Commercial: {len(commercial_items)} items")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    fetch_only = "--fetch-only" in sys.argv
    local_only = "--local" in sys.argv
    run(fetch_only=fetch_only, local_only=local_only)
