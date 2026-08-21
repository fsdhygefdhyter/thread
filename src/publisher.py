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

    Currently a stub — does nothing and returns a placeholder result.

    Args:
        post_text:    The full text of the Threads post (150–200 words + URL).
        access_token: Threads API access token (from GitHub Secret THREADS_ACCESS_TOKEN).
        user_id:      Threads user ID (from GitHub Secret THREADS_USER_ID).

    Returns:
        ThreadsPublishResult with success=False and a clear stub message.

    Implementation notes (for when you're ready to enable this):
        Step 1 — Create a media container:
            POST https://graph.threads.net/v1.0/{user_id}/threads
                ?media_type=TEXT
                &text={url-encoded post_text}
                &access_token={access_token}
            Returns: { "id": "<container_id>" }

        Step 2 — Publish the container:
            POST https://graph.threads.net/v1.0/{user_id}/threads_publish
                ?creation_id={container_id}
                &access_token={access_token}
            Returns: { "id": "<post_id>" }
    """
    # ── STUB: remove this block and implement the API calls above ──────
    return ThreadsPublishResult(
        success=False,
        error="Threads publishing is not yet enabled. Post saved to output/ only.",
    )
    # ── END STUB ───────────────────────────────────────────────────────
