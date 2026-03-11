"""Email Sender — Renders digest and sends via Resend."""

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import resend


def send(digest: dict):
    """Render the digest template and send via Resend.

    Args:
        digest: dict with research_summary, commercial_summary, top_picks,
                research_items, commercial_items
    """
    api_key = os.environ.get("RESEND_API_KEY")
    email_to = os.environ.get("EMAIL_TO")
    email_from = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")

    if not api_key or not email_to:
        print("  [Email] Missing RESEND_API_KEY or EMAIL_TO — skipping send")
        _save_local(digest)
        return

    # Render HTML
    html = _render(digest)

    # Send
    resend.api_key = api_key
    today = datetime.now().strftime("%m/%d")
    r_count = len(digest.get("research_items", []))
    c_count = len(digest.get("commercial_items", []))
    subject = f"🔬 AI Digest {today} — {r_count + c_count} items | Research + Commercial"

    try:
        result = resend.Emails.send({
            "from": email_from,
            "to": [email_to],
            "subject": subject,
            "html": html,
        })
        print(f"  [Email] Sent to {email_to} — ID: {result.get('id', 'unknown')}")
    except Exception as e:
        print(f"  [Email] Send failed: {e}")
        _save_local(digest)


def _render(digest: dict) -> str:
    """Render Jinja2 email template."""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("digest_email.html")

    r_items = digest.get("research_items", [])
    c_items = digest.get("commercial_items", [])
    sources = set(i["source"] for i in r_items + c_items)

    return template.render(
        date=datetime.now().strftime("%Y-%m-%d %A"),
        total_items=len(r_items) + len(c_items),
        source_count=len(sources),
        research_summary=digest.get("research_summary", ""),
        commercial_summary=digest.get("commercial_summary", ""),
        top_picks=digest.get("top_picks", []),
        research_items=r_items,
        commercial_items=c_items,
    )


def _save_local(digest: dict):
    """Fallback: save rendered HTML locally."""
    os.makedirs("output", exist_ok=True)
    html = _render(digest)
    path = f"output/digest_{datetime.now().strftime('%Y%m%d')}.html"
    with open(path, "w") as f:
        f.write(html)
    print(f"  [Email] Saved local copy → {path}")
