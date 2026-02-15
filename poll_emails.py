"""Poll emails from a watch list and update email.process.log.

Usage:
  python poll_emails.py           # run once
  python poll_emails.py --watch   # run every 5 minutes until Ctrl+C
"""
import argparse
import csv
import os
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

import imap_client

load_dotenv()

AEST = ZoneInfo("Australia/Sydney")
LOG_COLUMNS = ["id", "imap_uid", "sender", "received_time", "subject", "status", "updated_time", "session_id"]


def _now_aest() -> str:
    return datetime.now(AEST).strftime("%Y-%m-%d %H:%M:%S %Z")


def _parse_email_date(date_str: str) -> str:
    """Parse email Date header and return AEST formatted string."""
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(AEST).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return date_str


def _since_date_str() -> str:
    """Return IMAP SINCE date string for 24 hours ago."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return since.strftime("%d-%b-%Y")


def load_log(log_path: str) -> dict[str, dict]:
    """Load the process log CSV and return a dict keyed by email id."""
    entries = {}
    if not os.path.exists(log_path):
        return entries
    with open(log_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries[row["id"]] = row
    return entries


def save_log(log_path: str, entries: dict[str, dict]) -> None:
    """Write all log entries back to the CSV file."""
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        writer.writeheader()
        writer.writerows(entries.values())


def poll() -> None:
    email_account = os.environ.get("EMAIL_ACCOUNT")
    app_pass = os.environ.get("APP_PASS")
    watch_list_raw = os.environ.get("EMAIL_SENDER_WATCH_LIST", "")
    log_path = os.environ.get("EMAIL_PROCESS_LOG_PATH", "email.process.log")

    if not email_account or not app_pass:
        print("ERROR: EMAIL_ACCOUNT and APP_PASS must be set.", file=sys.stderr)
        sys.exit(1)

    watch_list = [s.strip() for s in watch_list_raw.split(",") if s.strip()]
    if not watch_list:
        print("ERROR: EMAIL_SENDER_WATCH_LIST is empty.", file=sys.stderr)
        sys.exit(1)

    since = _since_date_str()
    print(f"Polling emails from {watch_list} since {since} ...")

    try:
        emails = imap_client.get_emails_from_senders_since(
            email_account, app_pass, watch_list, since
        )
    except Exception as e:
        print(f"ERROR: Failed to fetch emails: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(emails)} email(s) in the past 24 hours.")

    log = load_log(log_path)
    new_count = 0
    new_entries = []

    for em in emails:
        # Use Message-ID as dedup key; fall back to IMAP UID
        uid = em["message_id"] or em["email_id"]
        if uid in log:
            continue

        entry = {
            "id": uid,
            "imap_uid": em["email_id"],
            "sender": em["from"],
            "received_time": _parse_email_date(em["date"]),
            "subject": em["subject"],
            "status": "processing",
            "updated_time": _now_aest(),
            "session_id": "",
        }
        log[uid] = entry
        new_entries.append(entry)
        new_count += 1
        print(f"  + New: [{em['subject']}] from {em['from']}")

    save_log(log_path, log)

    print(f"\nDone. {new_count} new email(s) added to log. Total in log: {len(log)}.")
    print(f"Log: {os.path.abspath(log_path)}")

    # Launch a claude -p session in iTerm2 for each new email
    header = ",".join(LOG_COLUMNS)
    for entry in new_entries:
        row = ",".join(entry[col] for col in LOG_COLUMNS)
        prompt = f"Receive this email:\n{header}\n{row}"
        print(f"\nStarting iTerm2 claude session for: [{entry['subject']}]")

        # Write a self-contained shell script — avoids all AppleScript escaping issues
        session_id = str(uuid.uuid4())
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\n")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as pf:
                pf.write(prompt)
                prompt_file = pf.name
            f.write(f"claude --dangerously-skip-permissions --output-format stream-json --verbose --session-id '{session_id}' -p \"$(cat '{prompt_file}')\"\n")
            # f.write(f"rm -f '{prompt_file}' '{f.name}'\n")
            script_file = f.name
        os.chmod(script_file, stat.S_IRWXU)
        print(f"  Script: {script_file}")
        print(f"  Prompt: {prompt_file}")
        print(f"  Session ID: {session_id}")

        # Update log entry with session_id before launching
        entry["session_id"] = session_id
        log[entry["id"]] = entry
        save_log(log_path, log)

        subprocess.Popen(["open", "-a", "iTerm", script_file])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run continuously, polling every 5 minutes until Ctrl+C.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Poll interval in seconds when using --watch (default: 300).",
    )
    args = parser.parse_args()

    if not args.watch:
        poll()
    else:
        print(f"Watch mode: polling every {args.interval}s. Press Ctrl+C to stop.\n")
        while True:
            try:
                poll()
            except Exception as e:
                print(f"ERROR during poll: {e}", file=sys.stderr)
            print(f"\nNext poll in {args.interval}s ...\n")
            time.sleep(args.interval)
