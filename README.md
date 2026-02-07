# imap_mcp

IMAP Email MCP Server for Claude Code. Exposes Gmail IMAP functionality as two MCP tools.

## Tools

- **`get_unread_email_by_sender_email`** - Fetch unread emails from specified senders. Returns email metadata (ID, subject, from, date, attachment filenames).
- **`download_email_attachment`** - Download email content and attachments to a local folder using an email ID.

## Setup

```bash
cd /Users/liquan/code/imap_mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

## Adding to Claude Code

```bash
claude mcp add --transport stdio --scope user imap-email \
  -e EMAIL_ACCOUNT=your_email@gmail.com \
  -e APP_PASS="your_app_password" \
  -- /Users/liquan/code/imap_mcp/venv/bin/python /Users/liquan/code/imap_mcp/server.py
```

Options:
- `--scope user` makes it available across all projects. Use `--scope project` for current project only.
- `-e` passes environment variables to the server process.

After adding, restart Claude Code and verify with `/mcp`.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `EMAIL_ACCOUNT` | Yes | Gmail address |
| `APP_PASS` | Yes | Gmail app password |
| `IMAP_SERVER` | No | IMAP server (default: `imap.gmail.com`) |
| `IMAP_PORT` | No | IMAP port (default: `993`) |
