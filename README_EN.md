# AI Trend Monitor — Daily Email Digest

> [中文版](README.md)

Automatically aggregates **11 data sources** across Research and Commercial domains, generates AI-powered summaries, and delivers a digest email every morning at 7:00 AM (Beijing Time).

## Data Sources

### Research (5 sources)
| Source | Method | Frequency |
|---|---|---|
| arXiv (custom topics) | arXiv API | Daily |
| Hugging Face Daily Papers | HF API | Daily |
| GitHub Trending (AI/Agent) | Web scraping | Daily |
| Model Provider Release Notes | RSS/Atom | Real-time |
| Evaluation Platforms (LMSYS, etc.) | Web scraping | Weekly |

### Commercial (6 sources)
| Source | Method | Frequency |
|---|---|---|
| Stanford AI Index | Report monitoring | Annual |
| OpenAI Enterprise Report | Blog RSS | Biannual |
| Anthropic Enterprise / Blog | Blog RSS | Quarterly |
| Together AI Blog | Blog RSS | Weekly |
| AI Startup Tech Blogs (8+) | Multi-RSS | Daily |
| YC Requests for Startups | Page monitoring | Periodic |

## Quick Start (3 Steps)

### 1. Fork this repository

### 2. Set up GitHub Secrets

Go to `Settings → Secrets and variables → Actions` and add:

| Secret | Description | How to obtain |
|---|---|---|
| `DASHSCOPE_API_KEY` | Qwen model API key | [Alibaba Cloud Bailian](https://bailian.console.aliyun.com/) → API Key Management |
| `RESEND_API_KEY` | Email delivery key | [resend.com](https://resend.com) (free 100 emails/day) |
| `EMAIL_TO` | Recipient email address | Your email |
| `EMAIL_FROM` | Sender email address | Resend verified domain email or `onboarding@resend.dev` |

### 3. Enable GitHub Actions

Go to the `Actions` tab → Enable the workflow → Done!

The workflow runs automatically every day at 7:00 AM Beijing Time (UTC 23:00). You can also trigger it manually for testing.

## Local Development

```bash
pip install -r requirements.txt

# Set environment variables
export DASHSCOPE_API_KEY="sk-..."
export RESEND_API_KEY="re_..."
export EMAIL_TO="you@example.com"
export EMAIL_FROM="onboarding@resend.dev"

# Run the pipeline
python run_pipeline.py
```

## Customization

- **Modify arXiv keywords**: Edit `QUERIES` in `fetchers/arxiv_fetcher.py`
- **Add/remove startup blogs**: Edit `BLOG_FEEDS` in `fetchers/startup_blogs.py`
- **Change delivery schedule**: Edit the cron expression in `.github/workflows/daily-digest.yml`
- **Switch to Slack**: Replace `EMAIL_TO` with a Slack webhook URL and modify `send_email.py`

## Tech Stack

Python 3.11+ / feedparser / arxiv / beautifulsoup4 / OpenAI SDK (Qwen via DashScope) / Resend / GitHub Actions
