# Email Polling Workflow

## Overview

A standalone Python script that polls emails from a configurable watch list and tracks processing state in a persistent log file.

---

## 1. Email Polling

### Source
Scan for emails from senders defined in the environment variable:
```
EMAIL_SENDER_WATCH_LIST=liquan1992@outlook.com,other@example.com
```
Comma-separated list of email addresses to monitor.

### Filter
- **Time range:** Past 24 hours from the time of polling
- **Read status:** Regardless of read or unread state
- **Folder:** INBOX

---

## 2. Process Log (`email.process.log`)

A CSV file that persists the state of all discovered emails.

### Location
Project root by default, overrideable via `EMAIL_PROCESS_LOG_PATH` environment variable.

### Format
```
id,sender,received_time,subject,status,updated_time
```

| Column | Description |
|---|---|
| `id` | Unique email identifier (Message-ID header) |
| `sender` | Sender email address |
| `received_time` | Time email was received, in AEST (UTC+10/+11) |
| `subject` | Email subject line |
| `status` | One of: `unprocessed`, `processing`, `error`, `success` |
| `updated_time` | Last status update time, in AEST |

### Status Lifecycle
```
(new email detected) → processing → success
                                  → error
```

When an email is detected during polling and has no existing log entry, it is added with status `processing`.

---

## 3. Script: `poll_emails.py`

A standalone script run directly:
```bash
python poll_emails.py
```

### Behaviour
1. Read `EMAIL_SENDER_WATCH_LIST` from environment
2. Connect to IMAP and fetch emails from those senders sent in the past 24 hours
3. Load existing `email.process.log` (create if missing)
4. For each fetched email:
   - If its `id` is already in the log → skip
   - If new → append a row with status `processing`
5. Print a summary to stdout: how many new emails were found

---

## 4. Implementation Notes

- Use `zoneinfo` (stdlib) for AEST timezone (`Australia/Sydney`)
- Log file uses CSV with a header row
- Deduplication key is the `Message-ID` header
- Reuse `imap_client.py` — add a new function `get_emails_from_senders_since` that fetches emails regardless of read status, filtered by sender and a since-date
