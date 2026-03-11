"""AI Summarizer — Uses Qwen (via DashScope OpenAI-compatible API) to generate a concise daily digest."""

import os
import json
from openai import OpenAI

# ===== Qwen 模型配置 =====
# 推荐模型：
#   qwen-plus    — 性价比最好，适合日常摘要（$0.40/M input, $1.20/M output）
#   qwen-turbo   — 最便宜，速度最快
#   qwen-max     — 最强，复杂推理（$1.60/M input, $6.40/M output）
#   qwen3.5-plus — 最新版，能力更强
MODEL = "qwen-plus"
MAX_TOKENS = 4000

# DashScope API 地址
#   国内：https://dashscope.aliyuncs.com/compatible-mode/v1
#   海外：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def summarize(research_items: list, commercial_items: list) -> dict:
    """Generate a structured digest summary using Qwen.

    Returns:
        dict with keys: 'date', 'research_summary', 'commercial_summary',
                        'top_picks', 'research_items', 'commercial_items'
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("  [Summarizer] No DASHSCOPE_API_KEY — returning raw items without summary")
        return {
            "research_summary": "（未配置 DASHSCOPE_API_KEY，跳过摘要生成）",
            "commercial_summary": "（未配置 DASHSCOPE_API_KEY，跳过摘要生成）",
            "top_picks": [],
            "research_items": research_items[:20],
            "commercial_items": commercial_items[:20],
        }

    client = OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
    )

    # Build context
    r_text = "\n".join(
        f"- [{i['source']}] {i['title']}: {i.get('abstract', '')[:200]}"
        for i in research_items[:30]
    )
    c_text = "\n".join(
        f"- [{i['source']}] {i['title']}: {i.get('abstract', '')[:200]}"
        for i in commercial_items[:20]
    )

    prompt = f"""你是一位 AI/LLM/Agent 方向的 PhD 研究助手。请根据以下今日信息流，生成一份简洁的每日摘要。

== RESEARCH 信息（{len(research_items)} 条）==
{r_text}

== COMMERCIAL 信息（{len(commercial_items)} 条）==
{c_text}

请输出以下 JSON 格式（直接输出 JSON，不要 markdown）：
{{
  "research_summary": "3-5 句话概括今日 research 要点，重点关注 agent safety/eval/governance/tool use 方向",
  "commercial_summary": "3-5 句话概括今日 commercial/startup 动态",
  "top_picks": [
    {{"title": "...", "source": "...", "reason": "一句话说明为什么值得关注"}}
  ]
}}

top_picks 选 3-5 条最值得 PhD 关注的条目（跨 research 和 commercial）。摘要请用中文。"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": "你是一位专注于 AI/LLM/Agent 研究的学术助手，擅长信息整理和趋势分析。请直接输出 JSON，不要任何多余文字。"},
                {"role": "user", "content": prompt},
            ],
        )
        text = response.choices[0].message.content.strip()

        # Parse JSON (handle possible markdown fences)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)

        result["research_items"] = research_items[:20]
        result["commercial_items"] = commercial_items[:20]
        print(f"  [Summarizer] Generated digest with {len(result.get('top_picks', []))} top picks (model: {MODEL})")
        return result

    except Exception as e:
        print(f"  [Summarizer] Qwen API failed: {e}")
        return {
            "research_summary": f"摘要生成失败: {e}",
            "commercial_summary": "",
            "top_picks": [],
            "research_items": research_items[:20],
            "commercial_items": commercial_items[:20],
        }
