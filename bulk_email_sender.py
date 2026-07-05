#!/usr/bin/env python3
"""
Bulk Email Sender — Gmail SMTP (HTML Edition)
-----------------------------------------------
Sends personalized, beautifully designed HTML emails to a list of
recipients from a CSV file. Each email inserts the recipient's name
into the HTML template automatically.

Setup:
  1. pip install python-dotenv
  2. Copy .env.example → .env and fill in your Gmail credentials
  3. Edit email_template.html  — the designed email body ({name} is replaced)
  4. Edit recipients.csv       — add Name and Email columns
  5. Run:  python bulk_email_sender.py
"""

import csv
import os
import smtplib
import sys
import time
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ─── Try loading python-dotenv ────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARNING] python-dotenv not installed. Install with: pip install python-dotenv")
    print("          Falling back to system environment variables only.\n")

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("send_log.txt", encoding="utf-8"),
    ],
)
# Force UTF-8 for stdout on Windows if possible
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

log = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
GMAIL_USER         = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
EMAIL_SUBJECT      = os.getenv("EMAIL_SUBJECT", "National Entrepreneurship Challange 2026 (NEC'26)").strip()
DELAY_SECONDS      = float(os.getenv("EMAIL_DELAY_SECONDS", "2"))

RECIPIENTS_FILE = Path("recipients.csv")
HTML_TEMPLATE   = Path("email_template.html")


def validate_config() -> None:
    """Abort early if required settings are missing."""
    errors = []
    if not GMAIL_USER:
        errors.append("GMAIL_USER is not set in .env")
    if not GMAIL_APP_PASSWORD:
        errors.append("GMAIL_APP_PASSWORD is not set in .env")
    if not RECIPIENTS_FILE.exists():
        errors.append(f"Recipients file not found: {RECIPIENTS_FILE}")
    if not HTML_TEMPLATE.exists():
        errors.append(f"HTML template not found: {HTML_TEMPLATE}")
    if errors:
        for e in errors:
            log.error("Config error: %s", e)
        sys.exit(1)


def load_html_template() -> str:
    """Read the HTML email template from file."""
    html = HTML_TEMPLATE.read_text(encoding="utf-8")
    if "{name}" not in html:
        log.warning(
            "'{name}' placeholder not found in %s — every email will be identical.",
            HTML_TEMPLATE,
        )
    return html


def html_to_plain(name: str) -> str:
    """Generate a minimal plain-text fallback for non-HTML email clients."""
    return (
        f"Dear {name},\n\n"
        "This is to inform you that the National Entrepreneurship Challenge 2026 "
        "(NEC'26) has commenced.\n\n"
        "Last year, during NEC'25, we had 17 third-year members who actively "
        "contributed to the challenge. As those members have now moved into their "
        "fourth year, we understand that academic commitments, project work, "
        "placements, and other responsibilities may affect their availability.\n\n"
        "Since the team size for NEC'26 is constrained, this form is being "
        "circulated to understand your willingness to continue as a member for "
        "this year's challenge.\n\n"
        "Kindly fill out this form carefully and honestly. Your response will help "
        "us plan the team structure for NEC'26 accordingly.\n\n"
        "Form Link: https://forms.gle/dEdR4E71ZMwKswuZ8\n\n"
        "Please submit your response by End of Day (EOD) today.\n\n"
        "Regards,\nE-Cell Team"
    )


def load_recipients() -> list[dict]:
    """
    Read recipients.csv.
    Expected columns: name, email  (case-insensitive)
    Returns a list of dicts: [{"name": ..., "email": ...}, ...]
    """
    recipients = []
    with RECIPIENTS_FILE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalize header names to lowercase
        if reader.fieldnames is None:
            log.error("recipients.csv appears to be empty.")
            sys.exit(1)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            name  = row.get("name",  "").strip()
            email = row.get("email", "").strip()
            if not email:
                log.warning("Row %d: missing email — skipping.", i)
                continue
            if not name:
                log.warning("Row %d (%s): missing name — using email prefix.", i, email)
                name = email.split("@")[0]
            recipients.append({"name": name, "email": email})

    log.info("Loaded %d recipient(s) from %s.", len(recipients), RECIPIENTS_FILE)
    return recipients


def build_message(name: str, to_email: str, html_template: str) -> MIMEMultipart:
    """
    Compose a MIME multipart/alternative email.
    Attaches plain-text first (fallback), then HTML (preferred).
    Email clients that support HTML will render the designed version.
    """
    html_body  = html_template.replace("{name}", name)
    plain_body = html_to_plain(name)

    msg = MIMEMultipart("alternative")
    msg["From"]    = GMAIL_USER
    msg["To"]      = to_email
    msg["Subject"] = EMAIL_SUBJECT

    # Order matters: plain first, HTML last (clients prefer the last part)
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))
    return msg


def send_bulk(recipients: list[dict], html_template: str) -> None:
    """Connect to Gmail SMTP once and send all emails."""
    total   = len(recipients)
    success = 0
    failed  = []

    log.info("Connecting to Gmail SMTP (smtp.gmail.com:587) …")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            log.info("Logged in as %s", GMAIL_USER)
            log.info("─" * 55)

            for idx, recipient in enumerate(recipients, start=1):
                name  = recipient["name"]
                email = recipient["email"]
                try:
                    msg = build_message(name, email, html_template)
                    server.sendmail(GMAIL_USER, email, msg.as_string())
                    log.info("[%d/%d] ✓  Sent to %s <%s>", idx, total, name, email)
                    success += 1
                except smtplib.SMTPRecipientsRefused as e:
                    log.error("[%d/%d] ✗  Rejected: %s — %s", idx, total, email, e)
                    failed.append(email)
                except Exception as e:
                    log.error("[%d/%d] ✗  Failed:   %s — %s", idx, total, email, e)
                    failed.append(email)

                # Polite delay between sends to respect Gmail rate limits
                if idx < total:
                    time.sleep(DELAY_SECONDS)

    except smtplib.SMTPAuthenticationError:
        log.error(
            "Authentication failed!\n"
            "  → Make sure you're using a Gmail App Password, NOT your regular password.\n"
            "  → Generate one at: https://myaccount.google.com/apppasswords\n"
            "  → Requires 2-Step Verification to be enabled on your account."
        )
        sys.exit(1)
    except smtplib.SMTPException as e:
        log.error("SMTP error: %s", e)
        sys.exit(1)

    # ─── Summary ──────────────────────────────────────────────────────────────
    log.info("─" * 55)
    log.info("Done. %d/%d emails sent successfully.", success, total)
    if failed:
        log.warning("Failed addresses (%d): %s", len(failed), ", ".join(failed))
    log.info("Full log saved to: send_log.txt")


def main() -> None:
    print("=" * 55)
    print("  Bulk Email Sender — Gmail SMTP")
    print("=" * 55)

    validate_config()
    html_template = load_html_template()
    recipients    = load_recipients()

    if not recipients:
        log.error("No valid recipients found. Aborting.")
        sys.exit(1)

    # Show a quick preview before sending
    print(f"\n  From   : {GMAIL_USER}")
    print(f"  Subject: {EMAIL_SUBJECT}")
    print(f"  To     : {len(recipients)} recipient(s)")
    print(f"  Delay  : {DELAY_SECONDS}s between sends")
    print()
    confirm = input("  Proceed? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  Aborted.")
        sys.exit(0)

    print()
    send_bulk(recipients, html_template)


if __name__ == "__main__":
    main()
