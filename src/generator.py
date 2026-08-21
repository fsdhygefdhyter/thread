"""
src/generator.py — Threads post generator using Google Gemini.

Gemini directly fetches and analyzes the AWS affiliate URL,
then generates a 150–200 word English Threads post.
"""

from dataclasses import dataclass

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


def generate(
    url: str,
    gemini_api_key: str,
) -> GeneratedPost:
    """
    Generate a Threads post from an AWS affiliate URL using Gemini.
    Gemini fetches the URL directly and analyzes it.

    Args:
        url:            The AWS affiliate product URL.
        gemini_api_key: Google Gemini API key.

    Returns:
        GeneratedPost with the post text, or an error message.
    """
    if not HAS_GENAI:
        return GeneratedPost(
            url=url,
            error="google-genai package not installed. Run: pip install google-genai",
        )

    client = genai.Client(api_key=gemini_api_key)
    
    # Create user prompt that asks Gemini to fetch and analyze the URL
    user_prompt = f"""Visit and read this AWS product URL, then write a Threads post about it:

{url}

Instructions:
- Fetch the URL and read the product page content
- Write a 150–200 word Threads post in the voice of a tired senior cloud engineer
- Attack the pain point in the first sentence
- Naturally work in the product as the solution
- End with a funny CTA
- Include the URL on its own line at the very end
- Output ONLY the post text, nothing else
"""

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
                    max_output_tokens=1024,
                ),
            )
            raw = (response.text or "").strip()
            if not raw:
                last_error = f"{model} returned empty response"
                continue

            result = GeneratedPost(url=url, post_text=raw)
            print(f"  Generated post: {result.word_count} words")
            return result

        except Exception as e:
            last_error = str(e)
            err_lower = last_error.lower()
            if any(code in err_lower for code in ("503", "unavailable", "429", "overloaded")):
                print(f"  {model} unavailable, trying next model...")
                continue
            # Non-transient error — don't retry other models
            return GeneratedPost(url=url, error=f"Gemini error: {last_error[:300]}")

    return GeneratedPost(
        url=url,
        error=f"All Gemini models failed. Last error: {last_error[:300]}",
    )
