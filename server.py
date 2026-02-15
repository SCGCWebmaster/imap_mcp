"""IMAP Email MCP Server - exposes email fetching tools via MCP protocol."""
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

import imap_client

load_dotenv()

mcp = FastMCP("imap-email")


def _get_credentials() -> tuple[str, str]:
    """Get email credentials from environment variables."""
    email_account = os.environ.get("EMAIL_ACCOUNT")
    app_pass = os.environ.get("APP_PASS")
    if not email_account or not app_pass:
        raise ValueError(
            "EMAIL_ACCOUNT and APP_PASS environment variables are required. "
            "Set them in your .env file or environment."
        )
    return email_account, app_pass


@mcp.tool()
def get_unread_email_by_sender_email(sender_emails: list[str]) -> list[dict]:
    """Fetch unread emails from specified senders. Returns email metadata including unique IDs
    that can be used with download_email_attachment."""
    try:
        email_account, password = _get_credentials()
        return imap_client.get_unread_emails(email_account, password, sender_emails)
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def download_email_attachment(email_id: str, folder: str) -> dict:
    """Download email content and attachments to the specified folder.
    Use email_id from get_unread_email_by_sender_email results."""
    try:
        email_account, password = _get_credentials()
        return imap_client.download_email(email_account, password, email_id, folder)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def send_email(to: str, subject: str, content: str) -> dict:
    """Send an email to the specified recipient.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        content: Plain text email body.
    """
    try:
        email_account, password = _get_credentials()
        return imap_client.send_email(email_account, password, to, subject, content)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
