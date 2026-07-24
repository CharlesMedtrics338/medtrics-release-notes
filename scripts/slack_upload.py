#!/usr/bin/env python3
"""
slack_upload.py — post a message to Slack and upload PDFs to the same thread.

Used by the /release-slack command after the user confirms the preview.
Does NOT use the Slack MCP. Talks to the Slack Web API directly via urllib,
using SLACK_BOT_TOKEN from .env in the current working directory.

Required env (in .env at CWD):
    SLACK_BOT_TOKEN       xoxb-... bot token with chat:write + files:write scopes
    SLACK_CHANNEL_RELEASE C0123ABC channel id, or #channel-name

Usage:
    python3 slack_upload.py \
        --channel "$SLACK_CHANNEL_RELEASE" \
        --message-file /tmp/release_slack_message.txt \
        --pdf /path/to/release-notes-2026-05-19.pdf \
        --pdf /path/to/integration-notes-2026-05-19.pdf

Exit codes:
    0  success — message posted, all PDFs uploaded
    1  configuration error (missing env, bad arg)
    2  Slack API error
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


SLACK_API = "https://slack.com/api"


def load_env(path=".env"):
    """Best-effort .env loader. Mirrors the pattern used by the other plugin scripts."""
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def slack_call(method, token, payload=None, files=None):
    """POST to Slack Web API. Returns parsed JSON or raises on transport error."""
    url = f"{SLACK_API}/{method}"
    if payload is None:
        payload = {}

    # JSON body for normal calls
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def slack_get(method, token, params=None):
    """GET-style Slack call (used for files.getUploadURLExternal)."""
    qs = urllib.parse.urlencode(params or {})
    url = f"{SLACK_API}/{method}?{qs}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def resolve_channel(channel, token):
    """If channel looks like a name (#x or x), resolve to a channel id."""
    if channel.startswith("C") and channel[1:].replace("_", "").isalnum() and len(channel) >= 9:
        return channel  # already an id
    name = channel.lstrip("#")
    # conversations.list — paginate
    cursor = ""
    while True:
        params = {"limit": "1000", "exclude_archived": "true",
                  "types": "public_channel,private_channel"}
        if cursor:
            params["cursor"] = cursor
        result = slack_get("conversations.list", token, params)
        if not result.get("ok"):
            raise RuntimeError(f"conversations.list failed: {result.get('error')}")
        for ch in result.get("channels", []):
            if ch.get("name") == name:
                return ch["id"]
        cursor = result.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    raise RuntimeError(f"Channel #{name} not found (or bot is not a member).")


def post_message(channel_id, text, token):
    """Post the main release announcement. Returns the ts (thread root)."""
    result = slack_call(
        "chat.postMessage",
        token,
        payload={
            "channel": channel_id,
            "text": text,
            "mrkdwn": True,
            "unfurl_links": False,
            "unfurl_media": False,
        },
    )
    if not result.get("ok"):
        raise RuntimeError(f"chat.postMessage failed: {result.get('error')}")
    return result["ts"]


def upload_pdf(channel_id, thread_ts, pdf_path, token, title=None):
    """Upload a single PDF as a reply to the thread.

    Uses the modern files.getUploadURLExternal + files.completeUploadExternal flow.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    size = pdf_path.stat().st_size

    # Step 1: get the upload URL
    step1 = slack_get(
        "files.getUploadURLExternal",
        token,
        {"filename": pdf_path.name, "length": str(size)},
    )
    if not step1.get("ok"):
        raise RuntimeError(f"files.getUploadURLExternal failed: {step1.get('error')}")
    upload_url = step1["upload_url"]
    file_id = step1["file_id"]

    # Step 2: PUT the file bytes to the upload URL
    with pdf_path.open("rb") as f:
        body = f.read()
    req = urllib.request.Request(
        upload_url,
        data=body,
        headers={"Content-Type": "application/pdf"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"file body upload returned HTTP {resp.status}")

    # Step 3: complete the upload, posting into the channel + thread
    complete_payload = {
        "files": [{"id": file_id, "title": title or pdf_path.name}],
        "channel_id": channel_id,
        "thread_ts": thread_ts,
    }
    step3 = slack_call("files.completeUploadExternal", token, payload=complete_payload)
    if not step3.get("ok"):
        raise RuntimeError(f"files.completeUploadExternal failed: {step3.get('error')}")
    return step3


def main():
    ap = argparse.ArgumentParser(description="Post Slack message + thread PDF uploads")
    ap.add_argument("--channel", required=True,
                    help="Channel id (C0123ABC) or name (#client-releases). "
                         "Usually $SLACK_CHANNEL_RELEASE from .env.")
    ap.add_argument("--message-file", required=True,
                    help="Path to a text file containing the Slack mrkdwn message body.")
    ap.add_argument("--pdf", action="append", default=[],
                    help="Path to a PDF to upload as a thread reply. Repeatable.")
    ap.add_argument("--title", action="append", default=[],
                    help="Optional title for the corresponding --pdf. "
                         "Order-matched; if omitted, filename is used.")
    ap.add_argument("--env-path", default=".env",
                    help="Path to .env (default: .env in CWD).")
    args = ap.parse_args()

    env = load_env(args.env_path)
    # Allow process env to override .env (standard pattern).
    token = os.environ.get("SLACK_BOT_TOKEN") or env.get("SLACK_BOT_TOKEN")
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set in environment or .env", file=sys.stderr)
        return 1
    if not token.startswith("xoxb-"):
        print("ERROR: SLACK_BOT_TOKEN must start with xoxb- (bot token, not user)",
              file=sys.stderr)
        return 1

    msg_path = Path(args.message_file)
    if not msg_path.exists():
        print(f"ERROR: message file not found: {msg_path}", file=sys.stderr)
        return 1
    message_text = msg_path.read_text()

    try:
        channel_id = resolve_channel(args.channel, token)
    except Exception as e:
        print(f"ERROR resolving channel: {e}", file=sys.stderr)
        return 2

    try:
        ts = post_message(channel_id, message_text, token)
    except Exception as e:
        print(f"ERROR posting message: {e}", file=sys.stderr)
        return 2

    print(f"OK: posted message to {channel_id} at ts={ts}")

    # Upload each PDF as a thread reply
    titles = list(args.title) + [None] * max(0, len(args.pdf) - len(args.title))
    for pdf, title in zip(args.pdf, titles):
        try:
            upload_pdf(channel_id, ts, pdf, token, title=title)
            print(f"OK: uploaded {pdf}")
        except Exception as e:
            print(f"ERROR uploading {pdf}: {e}", file=sys.stderr)
            return 2

    # Final summary block (machine-parseable for the command to extract)
    print()
    print("---SLACK_UPLOAD_RESULT---")
    print(json.dumps({"ok": True, "channel": channel_id, "ts": ts,
                      "uploaded": list(args.pdf)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
