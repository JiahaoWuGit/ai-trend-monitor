"""Email Sender — Renders digest and sends via Resend."""

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import resend


def send(digest: dict):
    """Render the digest template and send via Resend.

    Sends to all recipients in EMAIL_TO (comma-separated). As long as one
    succeeds the pipeline is considered successful. If some fail, a follow-up
    notification is sent to the successful recipients.

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

    # Support comma-separated recipients
    recipients = [addr.strip() for addr in email_to.split(",") if addr.strip()]

    # Render HTML
    html = _render(digest, interactive=True)

    # Send
    resend.api_key = api_key
    today = datetime.now().strftime("%m/%d")
    r_count = len(digest.get("research_items", []))
    c_count = len(digest.get("commercial_items", []))
    subject = f"🔬 AI Digest {today} — {r_count + c_count} items | Research + Commercial"

    succeeded = []
    failed = []

    for addr in recipients:
        try:
            result = resend.Emails.send({
                "from": email_from,
                "to": [addr],
                "subject": subject,
                "html": html,
            })
            print(f"  [Email] Sent to {addr} — ID: {result.get('id', 'unknown')}")
            succeeded.append(addr)
        except Exception as e:
            print(f"  [Email] Send to {addr} failed: {e}")
            failed.append((addr, str(e)))

    if not succeeded:
        print("  [Email] All sends failed — saving local copy")
        _save_local(digest)
        return

    # If some failed, notify successful recipients
    if failed:
        failed_list = "\n".join(f"  - {addr}: {err}" for addr, err in failed)
        print(f"  [Email] {len(failed)} recipient(s) failed, notifying {len(succeeded)} successful recipient(s)")
        notify_html = (
            f"<h3>⚠️ AI Digest 邮件发送部分失败</h3>"
            f"<p>以下收件人的 AI Digest ({today}) 发送失败：</p><ul>"
            + "".join(f"<li><b>{addr}</b>: {err}</li>" for addr, err in failed)
            + "</ul><p>成功发送的收件人：</p><ul>"
            + "".join(f"<li>{addr}</li>" for addr in succeeded)
            + "</ul>"
        )
        try:
            resend.Emails.send({
                "from": email_from,
                "to": succeeded,
                "subject": f"⚠️ AI Digest {today} — 部分邮件发送失败通知",
                "html": notify_html,
            })
            print(f"  [Email] Failure notification sent to {succeeded}")
        except Exception as e:
            print(f"  [Email] Failed to send failure notification: {e}")


def _render(digest: dict, interactive: bool = False) -> str:
    """Render Jinja2 email template.

    Args:
        digest: digest data dict
        interactive: if True, use digest_interactive.html (with deep analysis toggles)
    """
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template_name = "digest_interactive.html" if interactive else "digest_email.html"
    template = env.get_template(template_name)

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
    """Fallback: save rendered interactive HTML locally (with deep analysis toggles)."""
    os.makedirs("output", exist_ok=True)
    html = _render(digest, interactive=True)
    path = f"output/digest_{datetime.now().strftime('%Y%m%d')}.html"
    with open(path, "w") as f:
        f.write(html)
    print(f"  [Email] Saved local copy → {path}")
