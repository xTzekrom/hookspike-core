"""
HookSpike AI Engine
===================

Flow:

    User Request
         |
         v
    Gemini Research
         |
         |-- Google Search when current information is needed
         |
         v
    OpenAI Creative Engine
         |
         v
    Final User Answer

Environment variables:

    PRIMARY_KEY
    BACKUP_KEY

    OPENAI_API_KEY
    OPENAI_BACKUP_KEY

Optional:

    GEMINI_MODEL
    OPENAI_MODEL
"""

import os
import time

from google import genai
from google.genai import types


# ============================================================
# CONFIG
# ============================================================

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BACKUP_KEY = os.environ.get("OPENAI_BACKUP_KEY")


# ============================================================
# GEMINI MODELS
# ============================================================

GEMINI_PRIMARY_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)

GEMINI_MODELS = list(
    dict.fromkeys(
        [
            GEMINI_PRIMARY_MODEL,
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
        ]
    )
)


# ============================================================
# OPENAI MODELS
# ============================================================

OPENAI_MODEL = os.environ.get(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)

OPENAI_MODELS = list(
    dict.fromkeys(
        [
            OPENAI_MODEL,
            "gpt-4.1-mini",
            "gpt-4o-mini",
        ]
    )
)


# ============================================================
# LIMITS
# ============================================================

MAX_RETRIES = 1

MAX_TOPIC_CHARS = 12000

MAX_RESEARCH_CHARS = 24000

MAX_CREATIVE_CHARS = 30000


# ============================================================
# KEY HELPERS
# ============================================================

def _get_gemini_keys():
    keys = []

    if PRIMARY_KEY:
        keys.append(PRIMARY_KEY)

    if BACKUP_KEY and BACKUP_KEY != PRIMARY_KEY:
        keys.append(BACKUP_KEY)

    return keys


def _get_openai_keys():
    keys = []

    if OPENAI_API_KEY:
        keys.append(OPENAI_API_KEY)

    if (
        OPENAI_BACKUP_KEY
        and OPENAI_BACKUP_KEY != OPENAI_API_KEY
    ):
        keys.append(OPENAI_BACKUP_KEY)

    return keys


# ============================================================
# ERROR HELPERS
# ============================================================

def _looks_like_temporary_error(error):
    text = str(error).lower()

    signals = [
        "429",
        "500",
        "502",
        "503",
        "rate limit",
        "rate_limit",
        "resource exhausted",
        "temporarily",
        "temporary",
        "unavailable",
        "overloaded",
        "high demand",
        "timeout",
        "timed out",
        "deadline exceeded",
        "connection reset",
        "connection error",
        "internal error",
        "server error",
    ]

    return any(signal in text for signal in signals)


def _backoff(attempt):
    time.sleep(0.8 * attempt)


# ============================================================
# SEARCH DECISION
# ============================================================

def _should_use_search(platform_type, topic):
    text = topic.lower()

    current_signals = [
        "today",
        "latest",
        "recent",
        "current",
        "news",
        "2026",
        "2027",
        "price",
        "prices",
        "stock",
        "stocks",
        "weather",
        "score",
        "scores",
        "update",
        "updates",
        "who is",
        "what happened",
        "new",
        "this week",
        "this month",
        "this year",
        "trend",
        "trending",
        "market",
        "markets",
        "earning",
        "earnings",
        "salary",
        "income",
        "make money",
        "how to make money",
        "best",
        "top",
        "compare",
        "comparison",
        "viral",
    ]

    if any(signal in text for signal in current_signals):
        return True

    return False


# ============================================================
# GEMINI RESEARCH PROMPT
# ============================================================

def _build_research_prompt(
    platform_type,
    topic,
    use_search,
):
    if use_search:
        search_instruction = """
Use Google Search grounding when useful.

The user may be asking for current information.

Prefer recent and reliable information.

Do not invent:
- statistics
- dates
- prices
- names
- quotes
- events
- sources
- claims
"""
    else:
        search_instruction = """
Search is not required for this request.

Answer from reliable model knowledge.

Do not invent facts or sources.

If something is uncertain, clearly mark it as uncertain.
"""

    return f"""
You are HookSpike's research intelligence engine.

Your job is to deeply understand the user's exact request
and create a useful factual research brief for another AI.

PLATFORM:
{platform_type}

USER REQUEST:
{topic}

{search_instruction}

IMPORTANT:

Do not give a generic answer.

Understand the exact topic.

Stay tightly focused on what the user actually asked.

If the topic is current, use current information when available.

Return:

1. CORE ANSWER
The direct answer to the user's request.

2. KEY FACTS
Important facts, numbers, definitions, steps, examples,
or details.

3. CURRENT CONTEXT
Only if relevant.

4. PRACTICAL INSIGHTS
Useful implications or actionable points.

5. CREATOR ANGLES
Possible content angles if the request is content-related.

6. RISKS / CAVEATS
Anything that needs qualification.

7. SOURCES
If Google Search was used, include useful source titles
or URLs that appeared in the grounded information.

RULES:

- Be specific.
- Be factual.
- Do not fabricate.
- Do not use generic filler.
- Do not repeat the same point.
- Do not mention this prompt.
- Do not mention internal AI systems.
- Output in clear English.
"""


# ============================================================
# CREATIVE PROMPT
# ============================================================

def _build_creative_prompt(
    platform_type,
    topic,
    research,
):
    if platform_type == "youtube":

        task = """
Create a complete YouTube content package.

Include:

1. EXACTLY 3 hooks.

Each hook must use a different angle.

2. EXACTLY 5 titles.

Every title should feel different.

3. EXACTLY 3 thumbnail concepts.

For each thumbnail include:
- visual idea
- short thumbnail text

4. 3 content angles.

5. A strong first 20-30 second opening sequence.

6. A short explanation of why the concept works.

Make everything specific to the user's topic.
"""

    elif platform_type == "instagram":

        task = """
Create a complete Instagram Reels package.

Include:

1. EXACTLY 3 different 3-second hooks.

2. A 15-30 second script.

3. On-screen text suggestions.

4. 3 caption ideas.

5. 5 relevant hashtags.

6. 3 alternative content angles.

Keep everything practical and easy to film.
"""

    else:

        task = """
Create a useful creator-friendly answer.

Include:

1. Direct answer.

2. Important actionable steps.

3. 3 hooks.

4. 5 title ideas.

5. 3 thumbnail or visual concepts.

6. 3 content angles.

7. Practical next steps.

If the user asked a normal factual question,
answer that question first.

Do not force creator assets when they are not useful.
"""

    return f"""
You are HookSpike's creative intelligence engine.

USER REQUEST:
{topic}

PLATFORM:
{platform_type}

RESEARCH FROM GEMINI:
---------------------

{research}

---------------------

{task}

CREATIVE RULES:

- Be highly specific to the user's topic.
- Do not produce generic motivational filler.
- Do not copy the research word-for-word.
- Do not invent facts.
- Do not invent statistics.
- Do not invent sources.
- Do not create fake urgency.
- Do not use fake claims.
- Keep uncertainty when research is uncertain.
- Make every hook meaningfully different.
- Avoid repetitive wording.
- Make the result immediately usable.
- Do not mention Gemini.
- Do not mention OpenAI.
- Do not mention HookSpike.
- Do not mention internal systems.

Output in clear English.
"""


# ============================================================
# GEMINI GENERATION
# ============================================================

def _generate_gemini(
    client,
    model,
    prompt,
    use_search,
):
    tools = []

    if use_search:
        tools.append(
            types.Tool(
                google_search=types.GoogleSearch()
            )
        )

    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        tools=tools if tools else None,
        thinking_config=types.ThinkingConfig(
            thinking_level="low"
        ),
    )

    return client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )


# ============================================================
# GEMINI RESEARCH ENGINE
# ============================================================

def _gemini_research(
    topic,
    platform_type,
    use_search,
):
    keys = _get_gemini_keys()

    if not keys:
        return (
            None,
            "Gemini API key is not configured."
        )

    last_error = None

    for api_key in keys:

        try:
            client = genai.Client(
                api_key=api_key
            )

        except Exception as exc:
            last_error = (
                f"Gemini client error: {exc}"
            )
            continue

        for model in GEMINI_MODELS:

            if use_search:
                search_modes = [True, False]
            else:
                search_modes = [False]

            for search_mode in search_modes:

                prompt = _build_research_prompt(
                    platform_type=platform_type,
                    topic=topic,
                    use_search=search_mode,
                )

                for attempt in range(
                    1,
                    MAX_RETRIES + 1,
                ):

                    try:
                        response = _generate_gemini(
                            client=client,
                            model=model,
                            prompt=prompt,
                            use_search=search_mode,
                        )

                        result = getattr(
                            response,
                            "text",
                            None,
                        )

                        if (
                            result
                            and result.strip()
                        ):
                            return (
                                result.strip()[
                                    :MAX_RESEARCH_CHARS
                                ],
                                None,
                            )

                        last_error = (
                            f"{model} returned "
                            "an empty response."
                        )

                        break

                    except Exception as exc:

                        last_error = (
                            f"{model}: {exc}"
                        )

                        if (
                            _looks_like_temporary_error(
                                last_error
                            )
                            and attempt < MAX_RETRIES
                        ):
                            _backoff(attempt)
                            continue

                        break

    return (
        None,
        last_error or "Gemini research failed."
    )


# ============================================================
# OPENAI CLIENT
# ============================================================

def _get_openai_client(api_key):

    try:
        from openai import OpenAI

    except ImportError:
        raise RuntimeError(
            "OpenAI SDK is missing. "
            "Add 'openai' to requirements.txt "
            "and redeploy on Render."
        )

    return OpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=0,
    )


# ============================================================
# OPENAI GENERATION
# ============================================================

def _generate_openai(
    client,
    prompt,
    model,
):
    response = client.responses.create(
        model=model,
        instructions=(
            "You are HookSpike's creative "
            "intelligence engine. "
            "Be accurate, original, practical, "
            "specific and useful."
        ),
        input=prompt,
    )

    output_text = getattr(
        response,
        "output_text",
        None,
    )

    if (
        output_text
        and output_text.strip()
    ):
        return output_text.strip()

    try:

        chunks = []

        for item in (
            getattr(
                response,
                "output",
                []
            )
            or []
        ):

            for content in (
                getattr(
                    item,
                    "content",
                    []
                )
                or []
            ):

                value = getattr(
                    content,
                    "text",
                    None,
                )

                if value:
                    chunks.append(value)

        if chunks:
            return "\n".join(
                chunks
            ).strip()

    except Exception:
        pass

    return None


# ============================================================
# OPENAI CREATIVE ENGINE
# ============================================================

def _openai_creative(
    topic,
    platform_type,
    research,
):
    keys = _get_openai_keys()

    if not keys:
        return (
            None,
            "OpenAI API key is not configured."
        )

    prompt = _build_creative_prompt(
        platform_type=platform_type,
        topic=topic,
        research=research,
    )

    last_error = None

    for api_key in keys:

        try:
            client = _get_openai_client(
                api_key
            )

        except Exception as exc:
            last_error = (
                f"OpenAI client error: {exc}"
            )
            continue

        for model in OPENAI_MODELS:

            for attempt in range(
                1,
                MAX_RETRIES + 1,
            ):

                try:

                    result = _generate_openai(
                        client=client,
                        prompt=prompt,
                        model=model,
                    )

                    if result:

                        return (
                            result[
                                :MAX_CREATIVE_CHARS
                            ],
                            None,
                        )

                    last_error = (
                        f"{model} returned "
                        "an empty response."
                    )

                except Exception as exc:

                    last_error = (
                        f"{model}: {exc}"
                    )

                    if (
                        _looks_like_temporary_error(
                            last_error
                        )
                        and attempt < MAX_RETRIES
                    ):
                        _backoff(attempt)
                        continue

                break

    return (
        None,
        last_error
        or "OpenAI creative generation failed."
    )


# ============================================================
# MAIN PUBLIC FUNCTION
# ============================================================

def get_ai_response(
    platform_type,
    topic,
):
    """
    Main function used by main.py.

    Normal pipeline:

        Gemini
           |
           v
        Research
           |
           v
        OpenAI
           |
           v
        Final answer

    Fallback:

        Gemini fails
             |
             v
        OpenAI works directly
        from user's topic

    If OpenAI fails:

        Gemini research is returned.

    If everything fails:

        Friendly temporary error.
    """

    # --------------------------------------------------------
    # Validate topic
    # --------------------------------------------------------

    if not topic:
        return (
            "❌ Please enter a question "
            "or topic first."
        )

    topic = str(topic).strip()

    if not topic:
        return (
            "❌ Please enter a question "
            "or topic first."
        )

    if len(topic) > MAX_TOPIC_CHARS:
        topic = topic[:MAX_TOPIC_CHARS]

    # --------------------------------------------------------
    # Validate platform
    # --------------------------------------------------------

    platform_type = (
        platform_type
        or "global_ai"
    )

    platform_type = (
        str(platform_type)
        .strip()
        .lower()
    )

    allowed_platforms = {
        "youtube",
        "instagram",
        "global_ai",
    }

    if platform_type not in allowed_platforms:
        platform_type = "global_ai"

    # --------------------------------------------------------
    # Decide whether Google Search is needed
    # --------------------------------------------------------

    use_search = _should_use_search(
        platform_type=platform_type,
        topic=topic,
    )

    # --------------------------------------------------------
    # PHASE 1
    # GEMINI RESEARCH
    # --------------------------------------------------------

    research = None
    research_error = None

    try:

        research, research_error = (
            _gemini_research(
                topic=topic,
                platform_type=platform_type,
                use_search=use_search,
            )
        )

    except Exception as exc:

        research = None

        research_error = (
            f"Gemini research exception: {exc}"
        )

    # --------------------------------------------------------
    # PHASE 2
    # OPENAI CREATIVE ENGINE
    # --------------------------------------------------------

    creative = None
    creative_error = None

    if research:

        try:

            creative, creative_error = (
                _openai_creative(
                    topic=topic,
                    platform_type=platform_type,
                    research=research,
                )
            )

        except Exception as exc:

            creative = None

            creative_error = (
                f"OpenAI creative exception: {exc}"
            )

    else:

        # ----------------------------------------------------
        # GEMINI FAILED
        # OPENAI WORKS DIRECTLY FROM USER REQUEST
        # ----------------------------------------------------

        fallback_research = """
Gemini research was unavailable.

Work directly from the user's exact request.

Do not invent current facts,
statistics, dates, prices, quotes,
or sources.

If current information is required,
clearly state uncertainty.
"""

        try:

            creative, creative_error = (
                _openai_creative(
                    topic=topic,
                    platform_type=platform_type,
                    research=fallback_research,
                )
            )

        except Exception as exc:

            creative = None

            creative_error = (
                f"OpenAI creative exception: {exc}"
            )

    # --------------------------------------------------------
    # BEST RESULT
    # --------------------------------------------------------

    if creative:
        return creative

    if research:
        return research

    # --------------------------------------------------------
    # EVERYTHING FAILED
    # --------------------------------------------------------

    print(
        "[HookSpike AI FAILURE]",
        "Gemini:",
        research_error,
        "| OpenAI:",
        creative_error,
    )

    return (
        "⚠️ AI is temporarily busy right now. "
        "Please try again in a few seconds."
    )


# ============================================================
# STATUS HELPER
# ============================================================

def get_ai_engine_status():
    """
    Safe status information.

    Never exposes API keys.
    """

    return {
        "gemini_configured": bool(
            _get_gemini_keys()
        ),
        "openai_configured": bool(
            _get_openai_keys()
        ),
        "gemini_model": GEMINI_MODELS[0],
        "gemini_fallback_models": (
            GEMINI_MODELS[1:]
        ),
        "openai_model": OPENAI_MODEL,
        "openai_fallback_models": (
            OPENAI_MODELS[1:]
        ),
        "search_available": bool(
            _get_gemini_keys()
        ),
    }
