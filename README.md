# 🔬 PhD AI/LLM/Agent 趋势监控 — 每日邮件推送

> [English Version](README_EN.md)

自动采集 Research + Commercial 两大板块共 **11 个信息源**，用 Claude 生成摘要，每天早上 7:00 推送 digest 邮件。

## 信息源

### Research（5 源）
| 源 | 采集方式 | 频率 |
|---|---|---|
| arXiv 定制主题 | arXiv API | 每日 |
| Hugging Face Daily Papers | HF API | 每日 |
| GitHub Trending (AI/Agent) | Web scraping | 每日 |
| 模型厂商 Release Notes | RSS/Atom | 实时 |
| 独立评测平台 (LMSYS 等) | Web scraping | 每周 |

### Commercial（6 源）
| 源 | 采集方式 | 频率 |
|---|---|---|
| Stanford AI Index | 报告监控 | 年度 |
| OpenAI Enterprise Report | Blog RSS | 半年 |
| Anthropic Enterprise / Blog | Blog RSS | 季度 |
| Together AI Blog | Blog RSS | 每周 |
| AI Startup Tech Blogs (8家) | Multi-RSS | 每日 |

## 快速部署（3 步）

### 1. Fork 本仓库

### 2. 设置 GitHub Secrets

进入 `Settings → Secrets and variables → Actions`，添加：

| Secret | 说明 | 获取方式 |
|---|---|---|
| `DASHSCOPE_API_KEY` | Qwen 模型 API key | [阿里云百炼](https://bailian.console.aliyun.com/) → API-KEY 管理 |
| `RESEND_API_KEY` | 邮件发送 key | [resend.com](https://resend.com)（免费 100 封/天） |
| `EMAIL_TO` | 接收邮件地址 | 你的邮箱 |
| `EMAIL_FROM` | 发送邮件地址 | Resend 验证的域名邮箱或 `onboarding@resend.dev` |

### 3. 启用 GitHub Actions

进入 `Actions` tab → 启用 workflow → 完成！

每天北京时间早上 7:00（UTC 23:00）自动运行。也可以手动触发测试。

## 本地测试

```bash
pip install -r requirements.txt

# 设置环境变量
export DASHSCOPE_API_KEY="sk-..."
export RESEND_API_KEY="re_..."
export EMAIL_TO="you@example.com"
export EMAIL_FROM="onboarding@resend.dev"

# 运行
python run_pipeline.py
```

## 自定义

- **修改 arXiv 关键词**：编辑 `fetchers/arxiv_fetcher.py` 中的 `QUERIES`
- **增减 startup 博客**：编辑 `fetchers/startup_blogs.py` 中的 `BLOG_FEEDS`
- **调整推送时间**：编辑 `.github/workflows/daily-digest.yml` 中的 cron
- **改用 Slack 推送**：把 `EMAIL_TO` 换成 Slack webhook，修改 `send_email.py`

## 技术栈

Python 3.11+ / feedparser / arxiv / beautifulsoup4 / OpenAI SDK (Qwen via DashScope) / Resend / GitHub Actions
