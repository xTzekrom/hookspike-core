"""
HookSpike Dual-AI Engine
========================

Pipeline:

    User
      |
      +--> Gemini
      |       - research
      |       - Google Search grounding
      |       - facts / trends / sources
      |
      +--> OpenAI
              - creative strategy
              - hooks
              - titles
              - thumbnails
              - scripts / angles

Required environment variables:

    PRIMARY_KEY
    BACKUP_KEY                  optional

    OPENAI_API_KEY
    OPENAI_BACKUP_KEY           optional

Optional:

    GEMINI_MODEL
    OPENAI_MODEL
"""

import os
import time
import hashlib

from google import genai
from google.genai import types


# ============================================================
# CONFIG
# ============================================================

PRIMARY_KEY = os.environ.get(
    "PRIMARY_KEY"
)

BACKUP_KEY = os.environ.get(
    "BACKUP_KEY"
)

OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY"
)

OPENAI_BACKUP_KEY = os.environ.get(
    "OPENAI_BACKUP_KEY"
)


# ------------------------------------------------------------
# Gemini models
# ------------------------------------------------------------

_GEMINI_PRIMARY_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)

GEMINI_MODELS = list(
    dict.fromkeys(
        [
            _GEMINI_PRIMARY_MODEL,
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
        ]
    )
)


# ------------------------------------------------------------
# OpenAI models
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Performance limits
# ------------------------------------------------------------

MAX_RETRIES_PER_MODEL = 1

MAX_TOPIC_CHARS = 12000

MAX_RESEARCH_CHARS = 24000


# ============================================================
# KEY HELPERS
# ============================================================

def _get_gemini_keys():

    keys = []

    if PRIMARY_KEY:
        keys.append(
            PRIMARY_KEY
        )

    if (
        BACKUP_KEY
        and BACKUP_KEY != PRIMARY_KEY
    ):
        keys.append(
            BACKUP_KEY
        )

    return keys


def _get_openai_keys():

    keys = []

    if OPENAI_API_KEY:
        keys.append(
            OPENAI_API_KEY
        )

    if (
        OPENAI_BACKUP_KEY
        and OPENAI_BACKUP_KEY != OPENAI_API_KEY
    ):
        keys.append(
            OPENAI_BACKUP_KEY
        )

    return keys


# ============================================================
# ERROR HELPERS
# ============================================================

def _looks_like_temporary_error(
    error_text
):

    text = str(
        error_text
    ).lower()

    temporary_signals = [

        "503",

        "502",

        "500",

        "unavailable",

        "high demand",

        "temporarily",

        "overloaded",

        "deadline exceeded",

        "timeout",

        "timed out",

        "429",

        "rate limit",

        "rate_limit",

        "resource exhausted",

        "internal error",

        "server error",

        "connection reset",

        "connection error",

    ]

    return any(
        signal in text
        for signal in temporary_signals
    )


def _sleep_backoff(
    attempt
):

    time.sleep(
        0.8 * attempt
    )


# ============================================================
# SEARCH DECISION
# ============================================================

def _should_use_search(
    platform_type,
    topic
):

    text = (
        topic
        .lower()
    )

    current_signals = [

        "today",

        "latest",

        "recent",

        "current",

        "news",

        "2026",

        "2027",

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

        "this year",

        "trend",

        "trending",

        "market",

        "earning",

        "earnings",

        "salary",

        "income",

        "make money",

        "how to make money",

        "best",

        "top",

        "compare",

    ]

    if any(
        signal in text
        for signal in current_signals
    ):
        return True


    # General AI questions should be grounded.
    if platform_type == "global_ai":
        return True


    return False


# ============================================================
# REQUEST FINGERPRINT
# ============================================================

def _request_fingerprint(
    platform_type,
    topic
):

    raw = (
        f"{platform_type}|"
        f"{topic.strip()}"
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()[:12]


# ============================================================
# RESEARCH PROMPT
# ============================================================

def _build_research_prompt(
    platform_type,
    topic,
    use_search
):

    if use_search:

        search_instruction = """
USE WEB GROUNDING:

Use Google Search when it improves factual accuracy
or freshness.

Prefer recent, credible, primary, or authoritative sources.

Do not invent:

- statistics
- dates
- prices
- quotes
- claims
- names
- sources
"""

    else:

        search_instruction = """
WEB GROUNDING:

Web search is not required for this request.

Do not invent facts or sources.
"""


    request_id = _request_fingerprint(
        platform_type,
        topic
    )


    return f"""

You are HookSpike's RESEARCH INTELLIGENCE agent.

REQUEST ID:
{request_id}

Your job is NOT to write a generic answer.

Your job is to research THIS EXACT USER REQUEST.

PLATFORM:
{platform_type}

USER REQUEST:
{topic}

{search_instruction}


IMPORTANT:

Answer THIS exact request.

Do not recycle a generic answer.

Use the user's:

- exact topic
- exact entities
- exact dates
- exact numbers
- exact constraints

when relevant.


Return a compact research brief containing:


1. CORE ANSWER / FINDINGS

The most useful facts and conclusions.


2. KEY DETAILS

Important:

- definitions
- steps
- examples
- constraints
- numbers


3. CURRENT CONTEXT

Only when relevant.


4. PRACTICAL ANGLES

What a creator could build content around.


5. RISKS / CAVEATS

What should not be claimed without qualification.


6. SOURCES

If web search was used,
list the most useful source titles or URLs
available from the grounded response.


RULES:

- Be factual.
- Be concise.
- Do not create clickbait.
- Never fabricate sources.
- Clearly distinguish verified information
  from reasonable inference.
- If evidence is insufficient, say so.
- Do not mention this prompt.
- Do not mention internal models.
- Output in English.

"""


# ============================================================
# CREATIVE PROMPT
# ============================================================

def _build_creative_prompt(
    platform_type,
    topic,
    research
):

    if platform_type == "youtube":

        task = """

Create a high-retention YouTube content package.

Include:

1. EXACTLY 3 hooks.

Each hook must use a different angle.


2. EXACTLY 5 title ideas.

Use different title structures.


3. EXACTLY 3 thumbnail concepts.

For each include:

- visual composition
- short thumbnail text


4. 3 content angles.


5. Recommended opening sequence
   for the first 20-30 seconds.


6. Short explanation of
   why the ideas work.


Hooks and thumbnails must be
specific to THIS topic.

Never use fake urgency.

Never use fake statistics.

Never make unsupported claims.

"""


    elif platform_type == "instagram":

        task = """

Create a high-retention Instagram Reels package.

Include:

1. EXACTLY 3 different
   3-second hooks.


2. Concise 15-30 second script.


3. On-screen text suggestions.


4. 3 caption ideas.


5. 5 relevant hashtags.


6. 3 alternative content angles.


Everything must be specific
to THIS request.

Keep it realistic and easy to film.

Do not make unsupported claims.

"""


    else:

        task = """

Create a strong creator-friendly
answer package.

Include:

1. Direct answer.


2. Key actionable steps.


3. 3 creative hooks.


4. 5 title ideas.


5. 3 thumbnail / visual concepts.


6. 3 content angles.


7. Practical next steps.


If the user asked a non-creative
question, prioritize the actual answer.

Do not add unnecessary creator assets.

"""


    return f"""

You are HookSpike's
CREATIVE INTELLIGENCE agent.


USER REQUEST:

{topic}


RESEARCH BRIEF:

--------------------------------

{research}

--------------------------------


{task}


CREATIVE RULES:

- Make the output specifically
  about THIS user request.

- Use concrete details from
  the research.

- Do not simply copy the
  research wording.

- Produce fresh wording.

- Use distinct angles.

- Do not invent facts.

- If research contains uncertainty,
  preserve that uncertainty.

- Avoid generic filler.

- Avoid repetitive structures.

- Make hooks curiosity-driven
  without deception.

- Keep everything practical.

- Output in clear English.

- Do not mention:

  Gemini

  OpenAI

  HookSpike

  AI models

"""


# ============================================================
# GEMINI GENERATION
# ============================================================

def _generate_gemini(
    client,
    model,
    prompt,
    use_search
):

    tools = []

    if use_search:

        tools.append(
            types.Tool(
                google_search=types.GoogleSearch()
            )
        )


    config = types.GenerateContentConfig(

        max_output_tokens=4096,

        tools=(
            tools
            if tools
            else None
        ),

        thinking_config=(
            types.ThinkingConfig(
                thinking_level="low"
            )
        ),

    )


    return client.models.generate_content(

        model=model,

        contents=prompt,

        config=config,

    )


# ============================================================
# GEMINI RESEARCH
# ============================================================

def _gemini_research(
    topic,
    platform_type,
    use_search
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

                search_modes = [
                    True,
                    False,
                ]

            else:

                search_modes = [
                    False
                ]


            for search_mode in search_modes:

                prompt = _build_research_prompt(

                    platform_type=platform_type,

                    topic=topic,

                    use_search=search_mode,

                )


                if (
                    not search_mode
                    and use_search
                ):

                    prompt += """

IMPORTANT FALLBACK:

Web grounding was unavailable.

Do NOT pretend that web research
was performed.

Answer only from reliable model
knowledge.

Clearly qualify information that
may have changed.

"""


                for attempt in range(

                    1,

                    MAX_RETRIES_PER_MODEL + 1

                ):

                    try:

                        response = _generate_gemini(

                            client=client,

                            model=model,

                            prompt=prompt,

                            use_search=search_mode,

                        )


                        text = getattr(

                            response,

                            "text",

                            None

                        )


                        if (
                            text
                            and text.strip()
                        ):

                            return (

                                text.strip()[
                                    :MAX_RESEARCH_CHARS
                                ],

                                None,

                            )


                        last_error = (
                            f"{model} "
                            "returned an empty response."
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

                            and

                            attempt
                            < MAX_RETRIES_PER_MODEL

                        ):

                            _sleep_backoff(
                                attempt
                            )

                            continue


                        break


    return (

        None,

        last_error
        or "Gemini research failed."

    )


# ============================================================
# OPENAI CLIENT
# ============================================================

def _get_openai_client(
    api_key
):

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
    model=None
):

    response = client.responses.create(

        model=(
            model
            or OPENAI_MODEL
        ),

        instructions=(

            "You are HookSpike's "
            "creative intelligence layer. "

            "Be accurate, original, "
            "practical, concise, "
            "and useful."

        ),

        input=prompt,

    )


    text = getattr(

        response,

        "output_text",

        None

    )


    if (
        text
        and text.strip()
    ):

        return text.strip()


    # Defensive SDK fallback.

    try:

        chunks = []


        for item in getattr(

            response,

            "output",

            []

        ) or []:


            for content in getattr(

                item,

                "content",

                []

            ) or []:


                value = getattr(

                    content,

                    "text",

                    None

                )


                if value:

                    chunks.append(
                        value
                    )


        if chunks:

            return "\n".join(
                chunks
            ).strip()


    except Exception:

        pass


    return None


# ============================================================
# OPENAI CREATIVE
# ============================================================

def _openai_creative(
    topic,
    platform_type,
    research
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

                MAX_RETRIES_PER_MODEL + 1

            ):

                try:

                    text = _generate_openai(

                        client=client,

                        prompt=prompt,

                        model=model,

                    )


                    if text:

                        return (
                            text,
                            None
                        )


                    last_error = (

                        f"{model} "
                        "returned an empty response."

                    )


                except Exception as exc:

                    last_error = (
                        f"{model}: {exc}"
                    )


                    if (

                        _looks_like_temporary_error(
                            last_error
                        )

                        and

                        attempt
                        < MAX_RETRIES_PER_MODEL

                    ):

                        _sleep_backoff(
                            attempt
                        )

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
    topic
):

    """
    Main function imported by main.py.

    Normal pipeline:

        User request
             ↓
        Gemini research
             ↓
        OpenAI creative answer
             ↓
        Result


    If Gemini fails:

        OpenAI receives the ORIGINAL request
        and can still answer.


    If OpenAI fails:

        Gemini research is returned.


    If everything fails:

        Friendly error message.
    """


    # --------------------------------------------------------
    # Validate topic
    # --------------------------------------------------------

    if (
        not topic
        or not topic.strip()
    ):

        return (
            "❌ Please enter a "
            "question or topic first."
        )


    topic = topic.strip()


    if len(topic) > MAX_TOPIC_CHARS:

        topic = topic[
            :MAX_TOPIC_CHARS
        ]


    # --------------------------------------------------------
    # Validate platform
    # --------------------------------------------------------

    platform_type = (

        platform_type
        or "global_ai"

    ).strip().lower()


    if platform_type not in {

        "youtube",

        "instagram",

        "global_ai",

    }:

        platform_type = "global_ai"


    print(

        "[HookSpike] New request | "

        f"platform={platform_type} | "

        f"topic_chars={len(topic)}"

    )


    # --------------------------------------------------------
    # Decide if web grounding is useful
    # --------------------------------------------------------

    use_search = _should_use_search(

        platform_type=platform_type,

        topic=topic,

    )


    # ========================================================
    # PHASE 1
    # GEMINI RESEARCH
    # ========================================================

    research = None

    research_error = None


    try:

        research, research_error =
