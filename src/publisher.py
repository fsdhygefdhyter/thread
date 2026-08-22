"""
src/publisher.py — Threads publisher via Meta Graph API.

Flow:
  1. Publish main post (no URL, ends with CTA to check comment)
  2. Reply to that post with: URL + affiliate disclosure
"""

from dataclasses import dataclass


@dataclass
class ThreadsPublishResult:
    success: bool
    post_id: str = ""
    post_url: str = ""
    error: str = ""


AFFILIATE_DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."


def publish_to_threads(
    post_text: str,
    access_token: str | None = None,
    user_id: str | None = None,
) -> ThreadsPublishResult:
    """
    Publish a Threads post + reply with affiliate URL.

    post_text format (from generator):
      <main post body — no URL>
      ---REPLY---
      <url>
    """
    if not access_token or not user_id:
        return ThreadsPublishResult(
            success=False,
            error="Missing THREADS_ACCESS_TOKEN or THREADS_USER_ID",
        )

    import requests

    # ── Split main post and reply URL ────────────────────────────────────
    if "---REPLY---" in post_text:
        parts = post_text.split("---REPLY---", 1)
        main_text = parts[0].strip()
        reply_url = parts[1].strip()
    else:
        # Fallback: last line is URL
        lines = post_text.strip().splitlines()
        url_lines = [l for l in lines if l.strip().startswith("http")]
        body_lines = [l for l in lines if not l.strip().startswith("http")]
        main_text = "\n".join(body_lines).strip()
        reply_url = url_lines[-1].strip() if url_lines else ""

    # Clean Amazon URL
    reply_url = _clean_amazon_url(reply_url)
    reply_text = f"{reply_url}\n\n{AFFILIATE_DISCLOSURE}"

    print(f"      Main post: {len(main_text)} chars")
    print(f"      Reply URL: {reply_url}")

    # ── Step 1: Publish main post ────────────────────────────────────────
    post_id = _create_and_publish(main_text, access_token, user_id)
    if isinstance(post_id, str) and post_id.startswith("ERROR:"):
        return ThreadsPublishResult(success=False, error=post_id)

    post_url = f"https://www.threads.net/t/{post_id}"
    print(f"      Main post published: {post_url}")

    # ── Step 2: Reply with URL + disclosure ─────────────────────────────
    import time
    time.sleep(10)  # Wait for post to be available via API before replying
    reply_id = _create_and_publish_reply(reply_text, post_id, access_token, user_id)
    if isinstance(reply_id, str) and reply_id.startswith("ERROR:"):
        print(f"      Warning: reply failed: {reply_id}")
        # Still consider success since main post went through
    else:
        print(f"      Reply published: https://www.threads.net/t/{reply_id}")

    return ThreadsPublishResult(success=True, post_id=post_id, post_url=post_url)


def _create_and_publish(text: str, access_token: str, user_id: str) -> str:
    """Create container and publish. Returns post_id or 'ERROR: ...'"""
    import requests

    # Create container
    resp = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        data={"media_type": "TEXT", "text": text, "access_token": access_token},
        timeout=30,
    )
    try:
        resp.raise_for_status()
    except Exception as e:
        return f"ERROR: create container failed: {resp.text[:200]}"

    data = resp.json()
    if "error" in data:
        return f"ERROR: {data['error'].get('message', 'unknown')}"
    container_id = data.get("id")
    if not container_id:
        return "ERROR: no container ID"

    # Publish
    resp2 = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    try:
        resp2.raise_for_status()
    except Exception:
        return f"ERROR: publish failed: {resp2.text[:200]}"

    data2 = resp2.json()
    if "error" in data2:
        return f"ERROR: {data2['error'].get('message', 'unknown')}"
    post_id = data2.get("id")
    if not post_id:
        return "ERROR: no post ID"
    return post_id


def _create_and_publish_reply(text: str, reply_to_id: str, access_token: str, user_id: str) -> str:
    """Create a reply container and publish it. Returns reply_id or 'ERROR: ...'"""
    import requests

    # Create reply container
    resp = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads",
        data={
            "media_type": "TEXT",
            "text": text,
            "reply_to_id": reply_to_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    try:
        resp.raise_for_status()
    except Exception:
        return f"ERROR: create reply container failed: {resp.text[:200]}"

    data = resp.json()
    if "error" in data:
        return f"ERROR: {data['error'].get('message', 'unknown')}"
    container_id = data.get("id")
    if not container_id:
        return "ERROR: no reply container ID"

    # Publish reply
    resp2 = requests.post(
        f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    try:
        resp2.raise_for_status()
    except Exception:
        return f"ERROR: publish reply failed: {resp2.text[:200]}"

    data2 = resp2.json()
    if "error" in data2:
        return f"ERROR: {data2['error'].get('message', 'unknown')}"
    return data2.get("id", "ERROR: no reply ID")


def _clean_amazon_url(url: str) -> str:
    """Keep only /dp/ID?tag= from Amazon URL."""
    import re
    from urllib.parse import urlparse, parse_qs

    dp_match = re.search(r'/dp/([A-Z0-9]+)', url)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    tag = params.get("tag", [None])[0]

    if dp_match and tag:
        return f"https://www.amazon.com/dp/{dp_match.group(1)}?tag={tag}"
    return url
