"""Deep Analyzer — Generates detailed per-item analysis using LLM (batched)."""

import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# Reuse same config as summarizer.py
MODEL = "kimi-k2.5"
MAX_TOKENS = 40000
BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
BATCH_SIZE = 5
MAX_CONCURRENT_BATCHES = 3


def analyze_all(research_items: list, commercial_items: list) -> tuple[list, list]:
    """Generate deep analysis for all items in batches (parallel).

    Adds a 'deep_analysis' field (HTML string) to each item dict.
    Returns (research_items, commercial_items) with analysis attached.
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("  [DeepAnalyzer] No DASHSCOPE_API_KEY — skipping deep analysis")
        for item in research_items + commercial_items:
            item["deep_analysis"] = ""
        return research_items, commercial_items

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    print(f"  [DeepAnalyzer] Analyzing {len(research_items)} research + {len(commercial_items)} commercial items (parallel, max {MAX_CONCURRENT_BATCHES} concurrent)...")

    _analyze_batch_list_parallel(client, research_items, "research")
    _analyze_batch_list_parallel(client, commercial_items, "commercial")

    analyzed = sum(1 for i in research_items + commercial_items if i.get("deep_analysis"))
    print(f"  [DeepAnalyzer] Done — {analyzed}/{len(research_items) + len(commercial_items)} items analyzed")
    return research_items, commercial_items


def _analyze_batch_list_parallel(client: OpenAI, items: list, category: str):
    """Process items in batches of BATCH_SIZE, running up to MAX_CONCURRENT_BATCHES in parallel."""
    batches = []
    for i in range(0, len(items), BATCH_SIZE):
        batches.append((i, items[i:i + BATCH_SIZE]))

    total_batches = len(batches)
    print(f"    [{category}] {total_batches} batches total, {MAX_CONCURRENT_BATCHES} concurrent")

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as executor:
        futures = {}
        for start_idx, batch in batches:
            batch_num = start_idx // BATCH_SIZE + 1
            future = executor.submit(_analyze_batch, client, batch, category)
            futures[future] = (start_idx, batch, batch_num)

        for future in as_completed(futures):
            start_idx, batch, batch_num = futures[future]
            try:
                results = future.result()
                for item, analysis in zip(batch, results):
                    item["deep_analysis"] = analysis
                print(f"    [{category}] Batch {batch_num}/{total_batches} done")
            except Exception as e:
                print(f"    [{category}] Batch {batch_num}/{total_batches} failed: {e}")
                for item in batch:
                    item["deep_analysis"] = f"<p style='color:#94a3b8;'>分析生成失败: {e}</p>"


def _analyze_batch(client: OpenAI, items: list, category: str) -> list[str]:
    """Call LLM to analyze a batch of items. Returns list of HTML strings."""
    items_text = ""
    for idx, item in enumerate(items):
        items_text += f"\n=== ITEM {idx + 1} ===\n"
        items_text += f"Title: {item['title']}\n"
        items_text += f"Source: {item['source']}\n"
        if item.get("url"):
            items_text += f"URL: {item['url']}\n"
        if item.get("abstract"):
            items_text += f"Abstract: {item['abstract']}\n"
        if item.get("authors"):
            items_text += f"Authors: {item['authors']}\n"
        if item.get("tags"):
            items_text += f"Tags: {', '.join(item['tags'])}\n"

    if category == "research":
        task_desc = """对每篇论文/项目，请提供以下分析：
1. **核心贡献**：这项工作的主要贡献是什么？解决了什么问题？
2. **方法/技术路线**：采用了什么方法或技术？有何创新之处？
3. **主要发现**：关键实验结果或发现是什么？
4. **局限性**：有哪些潜在的局限或不足？
5. **研究意义**：对 AI/LLM/Agent 领域的意义是什么？"""
    else:
        task_desc = """对每篇博客/公告，请提供以下分析：
1. **核心内容**：这篇文章的主要内容是什么？
2. **技术细节**：涉及哪些关键技术或产品特性？
3. **行业影响**：对 AI 行业有什么影响或启示？
4. **值得关注的点**：有哪些值得 PhD 研究者关注的亮点？"""

    prompt = f"""你是一位 AI/LLM/Agent 方向的资深研究助手。请对以下 {len(items)} 个条目逐一进行详细分析。

{items_text}

{task_desc}

请输出 JSON 数组格式（直接输出 JSON，不要 markdown 代码块），数组中每个元素对应一个条目的分析：
[
  {{
    "item_index": 1,
    "analysis_html": "<strong>核心贡献：</strong><p>...</p><strong>方法/技术路线：</strong><p>...</p>..."
  }},
  ...
]

要求：
- analysis_html 必须是合法的 HTML 片段，使用 <strong>, <p>, <ul>, <li> 等标签
- HTML 属性请使用单引号，例如 <p style='color:red'> 而非双引号
- 不要使用带 href 属性的 <a> 标签，直接输出文字即可
- 确保 JSON 格式正确，所有字符串值中的双引号必须转义为 \\"
- 分析要详细、专业、有深度，每个条目的分析至少 150 字
- 用中文输出"""

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": "你是一位专注于 AI/LLM/Agent 研究的学术助手。请直接输出 JSON，不要任何多余文字。"},
            {"role": "user", "content": prompt},
        ],
    )
    text = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    results = _parse_json_robust(text, len(items))

    # Map results back to items by order
    analyses = [""] * len(items)
    for r in results:
        idx = r.get("item_index", 0) - 1
        if 0 <= idx < len(items):
            analyses[idx] = r.get("analysis_html", "")

    return analyses


def _parse_json_robust(text: str, expected_count: int) -> list:
    """Parse LLM-generated JSON with multiple fallback strategies.

    The LLM often returns JSON with unescaped double quotes inside HTML strings
    (e.g., <a href="url"> or style="..."), which breaks json.loads().
    """
    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    [JSON] Strategy 1 (direct) failed: {e}")

    # Strategy 2: Fix unescaped quotes inside analysis_html values
    try:
        fixed = _fix_json_html_escaping(text)
        result = json.loads(fixed)
        print(f"    [JSON] Strategy 2 (fix escaping) succeeded")
        return result
    except (json.JSONDecodeError, Exception) as e:
        print(f"    [JSON] Strategy 2 (fix escaping) failed: {e}")

    # Strategy 3: Regex extraction — pull each item_index + analysis_html individually
    try:
        results = _extract_items_by_regex(text)
        if results:
            print(f"    [JSON] Strategy 3 (regex) recovered {len(results)}/{expected_count} items")
            return results
    except Exception as e:
        print(f"    [JSON] Strategy 3 (regex) failed: {e}")

    # Strategy 4: Give up gracefully
    print(f"    [JSON] All strategies failed — returning empty analyses")
    return [{"item_index": i + 1, "analysis_html": ""} for i in range(expected_count)]


def _fix_json_html_escaping(text: str) -> str:
    """Try to fix unescaped double quotes inside JSON string values.

    Locates each "analysis_html": "..." value and escapes internal quotes
    that are clearly part of HTML (not JSON structure).
    """
    # Pattern: find "analysis_html" : " and then walk to find the real end
    result_parts = []
    pattern = re.compile(r'"analysis_html"\s*:\s*"')
    last_end = 0

    for match in pattern.finditer(text):
        # Copy everything before this match as-is
        result_parts.append(text[last_end:match.end()])
        pos = match.end()

        # Walk forward to find the real end of the string value
        # The string ends at an unescaped " followed by } or ,
        # We need to find the closing pattern: "} or ", or "]
        content_chars = []
        i = pos
        while i < len(text):
            ch = text[i]
            if ch == '\\':
                # Already escaped — keep as-is
                content_chars.append(ch)
                if i + 1 < len(text):
                    content_chars.append(text[i + 1])
                    i += 2
                else:
                    i += 1
                continue
            if ch == '"':
                # Check if this is the real end of the string
                # Look ahead for }, ], or ,
                rest = text[i + 1:].lstrip()
                if rest and rest[0] in ('}', ']', ','):
                    # This is the real closing quote
                    break
                else:
                    # This is an unescaped quote inside the HTML — escape it
                    content_chars.append('\\"')
                    i += 1
                    continue
            content_chars.append(ch)
            i += 1

        result_parts.append(''.join(content_chars))
        last_end = i  # position at the closing quote

    result_parts.append(text[last_end:])
    return ''.join(result_parts)


def _extract_items_by_regex(text: str) -> list:
    """Extract item_index and analysis_html from malformed JSON using regex."""
    results = []
    # Find all item_index values and their positions
    idx_pattern = re.compile(r'"item_index"\s*:\s*(\d+)')
    html_pattern = re.compile(r'"analysis_html"\s*:\s*"')

    idx_matches = list(idx_pattern.finditer(text))
    html_matches = list(html_pattern.finditer(text))

    for idx_m, html_m in zip(idx_matches, html_matches):
        item_index = int(idx_m.group(1))
        # Extract the HTML string starting after the opening quote
        start = html_m.end()
        html_content = _extract_string_at(text, start)
        if html_content is not None:
            results.append({
                "item_index": item_index,
                "analysis_html": html_content,
            })

    return results


def _extract_string_at(text: str, start: int):
    """Extract a JSON string value starting at position `start` (right after opening quote).

    Walks character by character, handling escape sequences, until finding
    the closing quote that's followed by a JSON structural character.
    """
    chars = []
    i = start
    while i < len(text):
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            # Escape sequence — keep both characters
            chars.append(ch)
            chars.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            # Check if this is the real closing quote
            rest = text[i + 1:].lstrip()
            if not rest or rest[0] in ('}', ']', ','):
                # Unescape for final output
                raw = ''.join(chars)
                # Unescape \" back to " for the HTML content
                return raw.replace('\\"', '"').replace('\\n', '\n')
        chars.append(ch)
        i += 1

    # Didn't find proper end — return whatever we got
    if chars:
        raw = ''.join(chars)
        return raw.replace('\\"', '"').replace('\\n', '\n')
    return None
