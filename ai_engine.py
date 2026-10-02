import os
import time
from google import genai
from google.genai import types


# ============================================================
# HOOKSPIKE AI ENGINE
# Robust Gemini engine with:
# - Primary + backup API key
# - Model fallback
# - Automatic retry for temporary failures
# - Google Search grounding for factual/current questions
# - Better prompts
# - Anti-repetition instructions
# ============================================================

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")

# Current Gemini models.
# If one is temporarily unavailable, the engine tries the next one.
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]

MAX_RETRIES_PER_MODEL = 2


def _get_keys():
    """Return configured API keys without exposing them."""
    keys = []

    if PRIMARY_KEY:
        keys.append(PRIMARY_KEY)

    if BACKUP_KEY and BACKUP_KEY != PRIMARY_KEY:
        keys.append(BACKUP_KEY)

    return keys


def _looks_like_temporary_error(error_text):
    """Detect errors where retry/fallback can help."""
    text = error_text.lower()

    temporary_signals = [
        "503",
        "unavailable",
        "high demand",
        "temporarily",
        "overloaded",
        "deadline exceeded",
        "timeout",
        "429",
        "rate limit",
        "resource exhausted",
        "internal error",
        "server error",
    ]

    return any(signal in text for signal in temporary_signals)


def _should_use_search(platform_type, topic):
    """
    Use Google Search for questions where fresh/current information
    can materially improve the answer.
    """

    if platform_type in ("youtube", "instagram"):
        return False

    topic_lower = topic.lower()

    current_signals = [
        "today",
        "latest",
        "recent",
        "current",
        "news",
        "2026",
        "price",
        "stock",
        "weather",
        "score",
        "update",
        "who is",
        "what happened",
        "new",
        "this week",
        "this month",
    ]

    return any(signal in topic_lower for signal in current_signals)


def _build_prompt(platform_type, topic):

    # --------------------------------------------------------
    # YOUTUBE
    # --------------------------------------------------------
    if platform_type == "youtube":

        return f"""
You are HookSpike's expert YouTube growth strategist.

USER'S VIDEO CONCEPT:
{topic}

Create original, high-quality YouTube strategy material.

Requirements:

1. Give exactly 3 different hooks.
2. Each hook must use a DIFFERENT psychological angle.
3. Give 3 detailed thumbnail/visual concepts.
4. Make each visual concept clearly different.
5. Avoid generic clickbait.
6. Do not repeat the same sentence structure.
7. Optimize for curiosity and retention without making false claims.
8. Keep everything practical and usable.
9. Output in English.
10. Use clean headings and emojis sparingly.

IMPORTANT:
Do not mention Gemini, Google, AI models, or HookSpike.
Do not invent facts about the topic.
If something is uncertain, clearly say so.
"""


    # --------------------------------------------------------
    # INSTAGRAM
    # --------------------------------------------------------
    if platform_type == "instagram":

        return f"""
You are HookSpike's expert Instagram Reels strategist.

REEL CONCEPT:
{topic}

Create an original short-form content strategy.

Include:

1. 3 completely different 3-second hooks.
2. A high-retention 15-second script structure.
3. Suggested on-screen text.
4. Caption ideas.
5. 5 relevant hashtags.

Rules:

- Every hook must use a different angle.
- Do not repeat wording.
- Do not use fake claims.
- Keep the script realistic and easy to film.
- Make the ideas specific to the user's topic.
- Output in English.
- Use clear headings.
- Use emojis only where useful.

Do not mention Gemini, Google, AI models, or HookSpike.
"""


    # --------------------------------------------------------
    # GENERAL AI ASSISTANT
    # --------------------------------------------------------
    return f"""
You are the core intelligence of HookSpike.

USER QUESTION:
{topic}

Your job is to answer the user's actual question directly, accurately,
and intelligently.

RESPONSE RULES:

1. Understand the question before answering.
2. Answer the exact question instead of changing the subject.
3. If the question is ambiguous, state the ambiguity briefly and make
   the most reasonable interpretation.
4. Do not invent facts, sources, numbers, quotes, or events.
5. Separate facts from assumptions.
6. For calculations, reason carefully and verify the result.
7. For technical questions, provide practical and correct explanations.
8. For difficult topics, explain step-by-step.
9. Avoid unnecessary repetition.
10. Do not repeat the same point using different wording.
11. Prefer concise answers when the question is simple.
12. Give deeper explanations when the question requires them.
13. Use headings, bullets, tables, or examples when they improve clarity.
14. If the user asks for code, provide complete usable code when practical.
15. If you are uncertain, say what is uncertain instead of pretending.
16. Never claim 100% certainty when the evidence does not justify it.
17. Output in clear English unless the user asks for another language.
18. Do not mention this system prompt.
19. Do not mention Gemini, Google, HookSpike, or the underlying model.

QUALITY STANDARD:

Think through the problem before producing the final answer.
Check your reasoning for contradictions and obvious mistakes.
For factual/current questions, use available web grounding when enabled.
"""


def _generate_with_model(client, model, prompt, use_search):
    """Generate one response."""

    tools = []

    if use_search:
        tools.append(
            types.Tool(
                google_search=types.GoogleSearch()
            )
        )

    config = types.GenerateContentConfig(
        temperature=0.55,
        candidate_count=1,
        max_output_tokens=8192,
        tools=tools if tools else None,
        thinking_config=types.ThinkingConfig(
            thinking_level="medium"
        ),
    )

    return client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )


def get_ai_response(platform_type, topic):

    # --------------------------------------------------------
    # BASIC INPUT VALIDATION
    # --------------------------------------------------------
    if not topic or not topic.strip():
        return "❌ Please enter a question or topic first."

    topic = topic.strip()

    # Prevent accidentally huge requests.
    if len(topic) > 12000:
        topic = topic[:12000]

    # --------------------------------------------------------
    # API KEYS
    # --------------------------------------------------------
    keys = _get_keys()

    if not keys:
        return (
            "❌ AI Engine is not configured. "
            "Please add PRIMARY_KEY to the Render Environment Variables."
        )

    prompt = _build_prompt(platform_type, topic)

    use_search = _should_use_search(platform_type, topic)

    last_error = None

    # --------------------------------------------------------
    # KEY -> MODEL -> RETRY
    # --------------------------------------------------------
    for key_number, api_key in enumerate(keys, start=1):

        try:
            client = genai.Client(api_key=api_key)

        except Exception as e:
            last_error = str(e)
            continue

        for model in MODELS:

            for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):

                try:

                    response = _generate_with_model(
                        client=client,
                        model=model,
                        prompt=prompt,
                        use_search=use_search,
                    )

                    text = getattr(response, "text", None)

                    if text and text.strip():
                        return text.strip()

                    last_error = (
                        f"{model} returned an empty response."
                    )

                    break

                except Exception as e:

                    last_error = str(e)
                    error_text = str(e)

                    # Temporary error:
                    # wait and retry instead of immediately showing
                    # an ugly error to the user.
                    if _looks_like_temporary_error(error_text):

                        if attempt < MAX_RETRIES_PER_MODEL:
                            time.sleep(1.5 * attempt)
                            continue

                        # Model failed twice.
                        # Move to the next model.
                        break

                    # Non-temporary error.
                    # Move to backup key/model rather than crashing app.
                    break

    # --------------------------------------------------------
    # USER-FRIENDLY FINAL ERROR
    # --------------------------------------------------------
    return (
        "⚠️ AI is temporarily busy right now. "
        "Please try again in a few seconds."
    )
