"""
Email sender.

Sends the markdown report by email over SMTP using only the standard library
(smtplib + email). If email settings are missing, it prints a warning and skips
sending instead of crashing.

The report is sent both as a plain-text part (the raw markdown) and a very
light HTML part, so it is readable in any mail client.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

import config
from radar.utils.logging import get_logger

logger = get_logger(__name__)


def _markdown_to_basic_html(markdown_text: str) -> str:
    """
    Convert the markdown to extremely simple HTML.

    We don't pull in a markdown library to keep dependencies light. We just
    wrap the raw markdown in a <pre> block so structure is preserved. Mail
    clients that prefer plain text will use the plain part anyway.
    """
    escaped = (
        markdown_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        "<html><body>"
        "<pre style=\"font-family: -apple-system, Segoe UI, sans-serif; "
        "white-space: pre-wrap; line-height: 1.4;\">"
        f"{escaped}"
        "</pre></body></html>"
    )


def send_report(report_markdown: str, report_date: str) -> bool:
    """
    Send the report by email. Returns True on success, False otherwise.

    Never raises — failures are logged and reported via the return value.
    """
    if not config.email_is_configured():
        logger.warning(
            "Email settings are incomplete — skipping send. "
            "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, "
            "EMAIL_TO in your .env to enable email."
        )
        return False

    subject = f"EU Job Market Radar — {report_date}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO
    # Force quoted-printable + utf-8 so non-ASCII characters (em dashes,
    # emoji, the non-breaking spaces that often appear in scraped news
    # titles) survive even if the SMTP server does not advertise 8BITMIME
    # and the message gets re-encoded as 7-bit on the wire.
    msg.set_content(report_markdown, subtype="plain", charset="utf-8", cte="quoted-printable")
    msg.add_alternative(
        _markdown_to_basic_html(report_markdown),
        subtype="html",
        charset="utf-8",
        cte="quoted-printable",
    )

    try:
        logger.info(
            "Connecting to SMTP %s:%s as %s",
            config.SMTP_HOST,
            config.SMTP_PORT,
            config.SMTP_USER,
        )
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()  # upgrade to a secure connection
            server.ehlo()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Report emailed to %s", config.EMAIL_TO)
        return True
    except Exception as exc:
        # Log the full traceback so SMTP/encoding issues are diagnosable
        # from the GitHub Actions logs, not just the one-line message.
        logger.exception("Failed to send email: %s", exc)
        return False
