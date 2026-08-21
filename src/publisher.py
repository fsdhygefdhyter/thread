"""
src/publisher.py — Threads publishing stub.

This module is intentionally left as a stub.
Threads API integration will be added here when credentials are available.

To enable publishing later:
  1. Obtain a Threads API access token.
  2. Add THREADS_ACCESS_TOKEN and THREADS_USER_ID to GitHub Secrets.
  3. Implement publish_to_threads() below using the Meta Graph API.
  4. Uncomment the publish_to_threads() call in src/main.py.

Meta Threads API docs: https://developers.facebook.com/docs/threads
"""

from dataclasses import dataclass


@dataclass
class ThreadsPublishResult:
    success: bool
    post_id: str = ""
    post_url: str = ""
    error: str = ""


def publish_to_threads(
    post_text: str,
    access_token: str | None = None,
    user_id: str | None = None,
) -> ThreadsPublishResult:
    """
    Publish a text post to Threads via the Meta Graph API.

    Args:
        post_text:    The full text of the Threads post (150–200 words + URL).
        access_token: Threads API access token (from GitHub Secret THREADS_ACCESS_TOKEN).
        user_id:      Threads user ID (from GitHub Secret THREADS_USER_ID).

    Returns:
        ThreadsPublishResult with success/error and post details if successful.

    Flow:
        Step 1 — Create a media container with the post text
        Step 2 — Publish the container to make it live
    """
    if not access_token or not user_id:
        return ThreadsPublishResult(
            success=False,
            error="Missing THREADS_ACCESS_TOKEN or THREADS_USER_ID",
        )

    if not post_text or len(post_text.strip()) == 0:
        return ThreadsPublishResult(
            success=False,
            error="Post text is empty",
        )

    import requests

    # ── Shorten the URL first ────────────────────────────────────────────
    short_url = _shorten_url(post_text.split("\n")[-1].strip())
    # Replace the long URL at the end with the short one
    lines = post_text.rstrip().split("\n")
    # Find and replace the last URL line
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("http"):
            lines[i] = short_url
            break
    post_text = "\n".join(lines)

    # ── Step 1: Create media container ──────────────────────────────────
    container_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    container_payload = {
        "media_type": "TEXT",
        "text": post_text,
        "access_token": access_token,
    }

    try:
        resp_container = requests.post(container_url, data=container_payload, timeout=30)
        resp_container.raise_for_status()
        container_data = resp_container.json()

        if "error" in container_data:
            error_msg = container_data["error"].get("message", "Unknown error")
            return ThreadsPublishResult(
                success=False,
                error=f"Failed to create media container: {error_msg}",
            )

        container_id = container_data.get("id")
        if not container_id:
            return ThreadsPublishResult(
                success=False,
                error="No container ID returned from Threads API",
            )

    except requests.exceptions.RequestException as e:
        return ThreadsPublishResult(
            success=False,
            error=f"Failed to create container: {str(e)[:300]}",
        )

    # ── Step 2: Publish the container ───────────────────────────────────
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": access_token,
    }

    try:
        resp_publish = requests.post(publish_url, data=publish_payload, timeout=30)
        resp_publish.raise_for_status()
        publish_data = resp_publish.json()

        if "error" in publish_data:
            error_msg = publish_data["error"].get("message", "Unknown error")
            return ThreadsPublishResult(
                success=False,
                error=f"Failed to publish: {error_msg}",
            )

        post_id = publish_data.get("id")
        if not post_id:
            return ThreadsPublishResult(
                success=False,
                error="No post ID returned from Threads API",
            )

        # Construct the Threads post URL
        post_url = f"https://www.threads.net/t/{post_id}"

        return ThreadsPublishResult(
            success=True,
            post_id=post_id,
            post_url=post_url,
        )

    except requests.exceptions.RequestException as e:
        return ThreadsPublishResult(
            success=False,
            error=f"Failed to publish: {str(e)[:300]}",
        )


def _shorten_url(url: str) -> str:
    """Shorten a URL using TinyURL API. Returns original URL if shortening fails."""
    import requests
    try:
        resp = requests.get(
            f"https://tinyurl.com/api-create.php?url={url}",
            timeout=10,
        )
        if resp.status_code == 200 and resp.text.startswith("http"):
            return resp.text.strip()
    except Exception:
        pass
    return url
