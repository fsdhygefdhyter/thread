"""
src/generator.py — Threads post generator using Google Gemini.

Generates a 160–180 word English Threads post from an AWS affiliate URL.
The URL is appended automatically at the end by the code (not by Gemini),
so it is never truncated.
"""

from dataclasses import dataclass

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


SYSTEM_PROMPT = """You are a senior Taiwanese IT/cloud engineer with 10+ years of real-world AWS production experience.

Your voice:
- Extremely sarcastic, funny, sharp, technically credible
- Exhausted survivor of 2 AM production alerts, runaway AWS bills, mysterious outages, pointless meetings, and managers who discovered "the cloud" last week
- You write Threads posts, not LinkedIn posts — no corporate fluff, no inspirational nonsense

Rules for every post:
1. English ONLY.
2. Exactly 160-180 words. Count carefully. Do not stop early.
3. First sentence immediately attacks the pain point — no warm-up, no intro.
4. Short paragraphs, suitable for Threads (2–4 sentences each).
5. Naturally introduce the product/solution mid-post without sounding like an ad.
6. Focus on real, practical benefits — what problem it actually solves.
7. End with a funny, slightly self-deprecating CTA.
8. Maximum 1–2 emojis total.
9. Zero generic AI marketing phrases: no "game-changer", "revolutionize", "seamlessly", "leverage", "empower".
10. No intro or explanation — output the post text ONLY.
11. No hashtags. Do NOT include any URL in your response.

Tone reference: "Oh great, another 3 AM PagerDuty alert because someone forgot to set a memory limit. Classic."
"""

MODEL_CHAIN = [
    "models/gemini-3.5-flash",
    "models/gemini-3.6-flash",
    "models/gemini-flash-latest",
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
        lines = [l for l in self.post_text.splitlines() if not l.startswith("http")]
        return len(" ".join(lines).split())


def generate(url: str, gemini_api_key: str) -> GeneratedPost:
    """
    Generate a Threads post for an Amazon affiliate product URL.
    Gemini writes the post body only; the URL is appended by this function.
    """
    if not HAS_GENAI:
        return GeneratedPost(url=url, error="google-genai not installed")

    client = genai.Client(api_key=gemini_api_key)

    # Extract product ID hint from URL for Gemini
    import re
    dp_match = re.search(r'/dp/([A-Z0-9]+)', url)
    product_hint = f"Product ID: {dp_match.group(1)}" if dp_match else ""

    user_prompt = f"""Write a Threads post about this Amazon product.

{product_hint}
Full URL (for context only, do NOT include in your response): {url}

Use the product ID or URL to identify what the product is (cookware, keyboard, skincare, hard drive, water bottle, backpack, mouse, etc.).

Write EXACTLY 160-180 words. The URL will be added automatically — do NOT put any URL in your response.
Output ONLY the post body text."""

    last_error = ""

    for model in MODEL_CHAIN:
        try:
            print(f"  Calling Gemini ({model})...")
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.85,
                    max_output_tokens=4096,
                ),
            )
            raw = (response.text or "").strip()
            if not raw:
                last_error = f"{model} returned empty response"
                continue

            # Always append the full affiliate URL at the end
            post_text = raw.rstrip() + "\n\n" + url

            result = GeneratedPost(url=url, post_text=post_text)
            print(f"  Generated post: {result.word_count} words")
            return result

        except Exception as e:
            last_error = str(e)
            if any(c in last_error.lower() for c in ("503", "unavailable", "429", "overloaded")):
                print(f"  {model} unavailable, trying next...")
                continue
            return GeneratedPost(url=url, error=f"Gemini error: {last_error[:300]}")

    return GeneratedPost(url=url, error=f"All models failed. Last: {last_error[:300]}")
