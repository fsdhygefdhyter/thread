"""
src/generator.py — Threads post generator using Google Gemini.

Takes a scraped AWS affiliate article and generates a 150–200 word
English Threads post in the voice of a senior Taiwanese IT/cloud engineer.
"""

from dataclasses import dataclass
from scraper import ScrapedArticle

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


# ── Writing style prompt ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior Taiwanese IT/cloud engineer with 10+ years of real-world AWS production experience.

Your voice:
- Extremely sarcastic, funny, sharp, technically credible
- Exhausted survivor of 2 AM production alerts, runaway AWS bills, mysterious outages, pointless meetings, and managers who discovered "the cloud" last week
- You write Threads posts, not LinkedIn posts — no corporate fluff, no inspirational nonsense

Rules for every post:
1. English ONLY.
2. Exactly 150–200 words (count carefully).
3. First sentence immediately attacks the pain point — no warm-up, no intro.
4. Short paragraphs, suitable for Threads (2–4 sentences each).
5. Naturally introduce the product/solution mid-post without sounding like an ad.
6. Focus on real, practical benefits — what problem it actually solves.
7. End with a funny, slightly self-deprecating CTA.
8. Include the original article URL on its own line at the very end.
9. Maximum 1–2 emojis total. Use sparingly for emphasis, not decoration.
10. Zero generic AI marketing phrases: no "game-changer", "revolutionize", "seamlessly", "leverage", "empower", "robust solution", "cutting-edge", "unlock potential".
11. No intro or explanation before the post — output the post text ONLY.
12. No hashtags.

Tone reference: "Oh great, another 3 AM PagerDuty alert because someone forgot to set a memory limit. Classic."
"""

# Gemini models to try in order (fallback chain)
# Using latest available models from Gemini API (as of 2026-08)
MODEL_CHAIN = [
    "models/gemini-3.7-flash",
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
]


@dataclass
class GeneratedPost:
    url: str
    post_text: str = ""
    error: str = ""

    @property
    def is_ok(self) -> bool:
        return bool(self.post_text) and not self.error

    @property
    def word_count(self) -> int:
        return len(self.post_text.split())


def build_user_prompt(article: ScrapedArticle, original_url: str = "") -> str:
    """Build the user-facing prompt from the scraped article."""
    # Limit article text to avoid token waste
    text_preview = article.text[:4000]
    if len(article.text) > 4000:
        text_preview += "\n\n[... content truncated ...]"

    title_line = f"Title: {article.title}" if article.title else ""
    
    # Include instruction to use the original URL in the final post
    url_instruction = f"\n\nIMPORTANT: At the very end of your post, include this exact URL (preserve all parameters):\n{original_url}" if original_url else ""

    return f"""Write a Threads post for this AWS affiliate product article.

Article URL: {article.url}
{title_line}

--- ARTICLE CONTENT ---
{text_preview}
--- END ---

Remember:
- 150–200 words exactly
- Attack the pain point in the first sentence
- Sound like a tired but sharp senior cloud engineer
- Naturally work in the product as the solution
- End with a funny CTA
- Put the article URL on its own line at the very end
- Output ONLY the post text, nothing else
{url_instruction}
"""


def generate(
    article: ScrapedArticle,
    gemini_api_key: str,
    original_url: str = "",
) -> GeneratedPost:
    """
    Generate a Threads post from a scraped article using Gemini.

    Args:
        article:        A successfully scraped article (article.is_ok must be True).
        gemini_api_key: Google Gemini API key.
        original_url:   The original URL with affiliate parameters. If provided, will be used in the final post.

    Returns:
        GeneratedPost with the post text, or an error message.
    """
    if not article.is_ok:
        return GeneratedPost(url=article.url, error=f"Scrape failed: {article.error}")

    if not HAS_GENAI:
        return GeneratedPost(
            url=article.url,
            error="google-genai package not installed. Run: pip install google-genai",
        )

    client = genai.Client(api_key=gemini_api_key)
    user_prompt = build_user_prompt(article, original_url=original_url)
    last_error = ""

    for model in MODEL_CHAIN:
        try:
            print(f"  Calling Gemini ({model})...")
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.85,        # slightly higher for personality
                    max_output_tokens=1024,  # posts are short
                ),
            )
            raw = (response.text or "").strip()
            if not raw:
                last_error = f"{model} returned empty response"
                continue

            # Ensure the original URL appears at the end (with all affiliate parameters)
            post_text = _ensure_url_at_end(raw, original_url or article.url)

            result = GeneratedPost(url=article.url, post_text=post_text)
            print(f"  Generated post: {result.word_count} words")
            return result

        except Exception as e:
            last_error = str(e)
            err_lower = last_error.lower()
            if any(code in err_lower for code in ("503", "unavailable", "429", "overloaded")):
                print(f"  {model} unavailable, trying next model...")
                continue
            # Non-transient error — don't retry other models
            return GeneratedPost(url=article.url, error=f"Gemini error: {last_error[:300]}")

    return GeneratedPost(
        url=article.url,
        error=f"All Gemini models failed. Last error: {last_error[:300]}",
    )


def _ensure_url_at_end(post_text: str, url: str) -> str:
    """
    Make sure the article URL appears on its own line at the end of the post.
    If Gemini already included it, leave it. If not, append it.
    """
    if url in post_text:
        # URL is there — make sure it's on its own line at the end
        # Remove it from wherever it is and re-append cleanly
        cleaned = post_text.replace(url, "").rstrip()
        return f"{cleaned}\n\n{url}"
    else:
        return f"{post_text.rstrip()}\n\n{url}"
