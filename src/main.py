"""
src/main.py — Main orchestration script.

Workflow:
  1. Read url.txt — all candidate AWS affiliate URLs.
  2. Read processed_urls.txt — URLs already handled.
  3. Pick ONE unprocessed URL.
  4. Scrape the article content.
  5. Generate a 150–200 word Threads post using Gemini.
  6. Save the post to output/<timestamp>.txt
  7. Append the URL to processed_urls.txt.
  8. (Future) Publish to Threads via publisher.publish_to_threads().

Exit codes:
  0 — success
  1 — error (scrape fail, generation fail, I/O error, etc.)
  2 — no unprocessed URLs available (NO UNUSED URL AVAILABLE)
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Ensure src/ is on the path when called from repo root
sys.path.insert(0, str(Path(__file__).parent))

from scraper import scrape
from generator import generate
from publisher import publish_to_threads   # stub — safe to import always


# ── File paths (all relative to repo root, one level up from src/) ────────────
REPO_ROOT      = Path(__file__).parent.parent
URL_FILE       = REPO_ROOT / "url.txt"
PROCESSED_FILE = REPO_ROOT / "processed_urls.txt"
OUTPUT_DIR     = REPO_ROOT / "output"


def load_urls(filepath: Path) -> list[str]:
    """Read a URL list file; skip blank lines and # comments."""
    if not filepath.exists():
        return []
    urls = []
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def load_processed(filepath: Path) -> set[str]:
    """Return a set of already-processed URLs."""
    if not filepath.exists():
        return set()
    processed = set()
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            processed.add(line)
    return processed


def pick_next_url(all_urls: list[str], processed: set[str]) -> str | None:
    """Return the first URL in url.txt that has not yet been processed."""
    for url in all_urls:
        if url not in processed:
            return url
    return None


def save_post(post_text: str) -> Path:
    """
    Save the generated Threads post to output/<timestamp>.txt.
    Timestamp is UTC, formatted as YYYY-MM-DD-HH-MM.
    Returns the path of the saved file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M")
    output_path = OUTPUT_DIR / f"{timestamp}.txt"

    # Handle the (unlikely) case where two runs fire in the same minute
    counter = 1
    while output_path.exists():
        output_path = OUTPUT_DIR / f"{timestamp}-{counter}.txt"
        counter += 1

    output_path.write_text(post_text, encoding="utf-8")
    return output_path


def mark_processed(filepath: Path, url: str) -> None:
    """Append a URL to processed_urls.txt."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(url + "\n")


def main() -> int:
    """
    Main entry point. Returns an exit code (0=success, 1=error, 2=no URLs).
    """
    load_dotenv()

    # ── Validate environment ──────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("Add it to .env (local) or GitHub Secrets (Actions).")
        return 1

    # ── Step 1 & 2: Load URL lists ────────────────────────────────────
    all_urls  = load_urls(URL_FILE)
    processed = load_processed(PROCESSED_FILE)

    print(f"url.txt:           {len(all_urls)} URLs total")
    print(f"processed_urls.txt: {len(processed)} already processed")

    if not all_urls:
        print("ERROR: url.txt is empty or missing. Add AWS affiliate URLs.")
        return 1

    # ── Step 3: Pick one unprocessed URL ─────────────────────────────
    target_url = pick_next_url(all_urls, processed)

    if target_url is None:
        print("NO UNUSED URL AVAILABLE")
        print("All URLs in url.txt have already been processed.")
        print("Add new URLs to url.txt to continue.")
        return 2

    print(f"\nSelected URL: {target_url}")

    # ── Step 4: Scrape article ────────────────────────────────────────
    print("\n[1/3] Scraping article...")
    article = scrape(target_url)

    if not article.is_ok:
        print(f"ERROR: Failed to scrape article: {article.error}")
        print("URL will NOT be added to processed_urls.txt — will retry next run.")
        return 1

    print(f"      OK — {len(article.text)} chars extracted")
    if article.title:
        print(f"      Title: {article.title[:80]}")

    # ── Step 5: Generate Threads post ─────────────────────────────────
    print("\n[2/3] Generating Threads post...")
    result = generate(article, gemini_api_key=gemini_key)

    if not result.is_ok:
        print(f"ERROR: Post generation failed: {result.error}")
        print("URL will NOT be added to processed_urls.txt — will retry next run.")
        return 1

    print(f"      OK — {result.word_count} words")
    print("\n--- GENERATED POST PREVIEW ---")
    print(result.post_text)
    print("--- END PREVIEW ---\n")

    # ── Step 6: Save post to output/ ──────────────────────────────────
    print("[3/3] Saving post...")
    output_path = save_post(result.post_text)
    print(f"      Saved to: {output_path.relative_to(REPO_ROOT)}")

    # ── Step 7: Mark URL as processed ────────────────────────────────
    mark_processed(PROCESSED_FILE, target_url)
    print(f"      Marked as processed: {target_url}")

    # ── Step 8 (Now enabled): Publish to Threads ──────────────────────
    threads_token   = os.getenv("THREADS_ACCESS_TOKEN")
    threads_user_id = os.getenv("THREADS_USER_ID")
    if threads_token and threads_user_id:
        print("\n[4/4] Publishing to Threads...")
        pub_result = publish_to_threads(
            post_text=result.post_text,
            access_token=threads_token,
            user_id=threads_user_id,
        )
        if pub_result.success:
            print(f"      Published: {pub_result.post_url}")
        else:
            print(f"      Publish failed: {pub_result.error}")
    else:
        print("\n[4/4] Threads publishing skipped (credentials not configured).")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
