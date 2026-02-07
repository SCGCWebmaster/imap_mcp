"""IMAP email client - fetch unread emails and download attachments."""
import email
import os
from contextlib import contextmanager
from email.header import decode_header
from email.message import Message

from imapclient import IMAPClient


# --- Email parsing helpers ---

def _decode_mime_header(header_value: str | None) -> str:
    """Decode MIME encoded header value."""
    if header_value is None:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _get_email_body(msg: Message) -> str:
    """Extract the text body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return body


def _extract_attachments(msg: Message) -> list[dict]:
    """Extract attachments from an email message. Returns list of {filename, content_type, payload}."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    filename = _decode_mime_header(filename)
                    payload = part.get_payload(decode=True)
                    if payload:
                        attachments.append({
                            "filename": filename,
                            "content_type": part.get_content_type(),
                            "payload": payload,
                        })
    return attachments


def _get_attachment_filenames(msg: Message) -> list[str]:
    """Get just the filenames of attachments without downloading payload."""
    filenames = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    filenames.append(_decode_mime_header(filename))
    return filenames


# --- IMAP connection ---

@contextmanager
def _imap_connection(email_account: str, password: str, server: str = None, port: int = None):
    """Context manager for IMAP connection."""
    server = server or os.environ.get("IMAP_SERVER", "imap.gmail.com")
    port = port or int(os.environ.get("IMAP_PORT", "993"))

    client = IMAPClient(server, port=port, ssl=True)
    client.login(email_account, password)
    try:
        yield client
    finally:
        client.logout()


def _resolve_email_id(client: IMAPClient, email_id: str) -> int:
    """Resolve email_id to IMAP UID."""
    if str(email_id).isdigit():
        return int(email_id)

    query = f"rfc822msgid:{email_id}"
    message_ids = client.gmail_search(query)

    if not message_ids:
        query = f"in:anywhere {email_id}"
        message_ids = client.gmail_search(query)

    if not message_ids:
        raise ValueError(f"Email with ID '{email_id}' not found")

    return message_ids[0]


# --- Public API ---

def get_unread_emails(email_account: str, password: str, sender_emails: list[str]) -> list[dict]:
    """Fetch unread emails from specified senders.

    Returns: [{email_id, subject, from, date, attachment_filenames}]
    """
    results = []

    with _imap_connection(email_account, password) as client:
        client.select_folder("INBOX")

        for from_addr in sender_emails:
            query = f"category:primary is:unread from:{from_addr}"
            message_ids = client.gmail_search(query)

            if not message_ids:
                continue

            response = client.fetch(message_ids, ["RFC822"])

            for msg_id, data in response.items():
                raw_bytes = data[b"RFC822"]
                msg = email.message_from_bytes(raw_bytes)

                results.append({
                    "email_id": str(msg_id),
                    "subject": _decode_mime_header(msg.get("Subject", "")),
                    "from": _decode_mime_header(msg.get("From", "")),
                    "date": _decode_mime_header(msg.get("Date", "")),
                    "attachment_filenames": _get_attachment_filenames(msg),
                })

    return results


def _deduplicate_filename(filepath: str) -> str:
    """Handle duplicate filenames by appending counter."""
    if not os.path.exists(filepath):
        return filepath
    base, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{ext}"
        counter += 1
    return filepath


def download_email(email_account: str, password: str, email_id: str, folder: str) -> dict:
    """Download email and attachments to folder/email_id/.

    Returns: {email_id, subject, folder_path, downloaded_files}
    """
    with _imap_connection(email_account, password) as client:
        client.select_folder("INBOX")
        imap_uid = _resolve_email_id(client, email_id)

        response = client.fetch([imap_uid], ["RFC822"])
        if imap_uid not in response:
            raise ValueError(f"Email with ID '{email_id}' not found in fetch")

        raw_bytes = response[imap_uid][b"RFC822"]

    msg = email.message_from_bytes(raw_bytes)
    subject = _decode_mime_header(msg.get("Subject", ""))
    from_addr = _decode_mime_header(msg.get("From", ""))
    date = _decode_mime_header(msg.get("Date", ""))
    message_id = msg.get("Message-ID", "").replace("\n", "").replace("\r", "").strip()
    body = _get_email_body(msg)
    attachments = _extract_attachments(msg)

    # Save to folder/email_id/
    folder_path = os.path.join(folder, str(email_id))
    os.makedirs(folder_path, exist_ok=True)

    downloaded_files = []

    # Write email.txt
    email_txt_path = os.path.join(folder_path, "email.txt")
    with open(email_txt_path, "w", encoding="utf-8") as f:
        f.write(f"Subject: {subject}\n")
        f.write(f"From: {from_addr}\n")
        f.write(f"Date: {date}\n")
        f.write(f"Message-ID: {message_id}\n")
        f.write(f"IMAP UID: {imap_uid}\n")
        f.write(f"\n{'=' * 60}\n\n")
        f.write(body)
    downloaded_files.append(email_txt_path)

    # Save attachments
    if attachments:
        attachments_folder = os.path.join(folder_path, "attachments")
        os.makedirs(attachments_folder, exist_ok=True)
        for att in attachments:
            filepath = _deduplicate_filename(os.path.join(attachments_folder, att["filename"]))
            with open(filepath, "wb") as f:
                f.write(att["payload"])
            downloaded_files.append(filepath)

    return {
        "email_id": str(email_id),
        "subject": subject,
        "folder_path": folder_path,
        "downloaded_files": downloaded_files,
    }
