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

# Optional dedicated key for thumbnail image generation.
# If not set, the existing OpenAI backup key is used.
OPENAI_IMAGE_API_KEY = os.environ.get("OPENAI_IMAGE_API_KEY")


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

# Gemini research can be useful but unnecessarily large research briefs make
# the OpenAI creative request slower and more expensive. Keep the full
# research available to Gemini, but send a compact slice to OpenAI.
MAX_RESEARCH_CHARS = 24000
MAX_RESEARCH_FOR_OPENAI_CHARS = 12000

MAX_CREATIVE_CHARS = 30000

# OpenAI gets more than the old 30-second window because the creative step can
# receive verified research and may need a little time to produce structured
# hooks/scripts/thumbnail concepts.
OPENAI_TIMEOUT_SECONDS = 90.0
OPENAI_SDK_RETRIES = 2


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

def _should_use_search(content_type, topic):
    """
    Creator requests can depend on very recent announcements, collaborations,
    game updates, releases and trends. Search is therefore enabled by default
    so the research layer can verify current claims before creative generation.
    """
    return True


# GEMINI RESEARCH PROMPT
# ============================================================

def _build_research_prompt(
    content_type,
    topic,
    use_search,
):
    return f"""
You are HookSpike's factual research intelligence engine.

USER CONTENT TYPE:
{content_type}

USER TOPIC:
{topic}

CURRENT INFORMATION RULE:
This request MUST be checked against current web information before creative output.
Use Google Search grounding.

If the topic mentions a game, anime, collaboration, event, update, release,
announcement, partnership, character, product, feature, or other time-sensitive
entity, actively verify whether it has actually been announced/released/confirmed.

VERY IMPORTANT VERIFICATION RULES:
- Never say "not officially announced" unless the searched evidence supports that exact status.
- If an announcement exists, say it is announced and include the relevant date/context.
- Distinguish official announcements from leaks, rumors, speculation and fan posts.
- Prefer official sources and reputable reporting for announcement status.
- Do not turn an old article into a current claim.
- If sources disagree, explicitly state the disagreement instead of choosing a side without evidence.
- Do not invent dates, names, statistics, quotes, collaborations or release details.
- Do not assume that because something was unannounced at an older date it is still unannounced now.

Return a compact research brief for the creative engine:

1. VERIFIED CORE FACTS
2. CURRENT / ANNOUNCEMENT STATUS
3. IMPORTANT DETAILS FOR THIS TOPIC
4. CREATOR-RELEVANT ANGLES
5. FACTS THAT MUST NOT BE CLAIMED
6. SOURCES / SOURCE TITLES IF AVAILABLE

Keep it specific to the user's exact topic.
Do not mention internal AI systems.
Output in clear English.
"""


# CREATIVE PROMPT
# ============================================================

def _build_creative_prompt(
    content_type,
    topic,
    research,
):
    if content_type == "hooks":
        task = """
Create ONLY hooks.

Return exactly 7 hooks, numbered 1 to 7, ordered from strongest scroll-stopping
opening to alternative angles.

Each hook must:
- be genuinely different from the others
- directly use the user's topic
- be usable as spoken opening lines
- avoid generic filler
- avoid repeating the same sentence pattern
- respect the verified research
- never claim something is unannounced if the research says it was announced

After the 7 hooks, add a very short section:
BEST USE: one sentence explaining when to use the strongest hook.
Do NOT include a script, thumbnail ideas, titles, hashtags or unrelated content.
"""

    elif content_type == "script":
        task = """
Create ONLY one topic-specific short-form script.

Structure:
1. HOOK
2. SETUP
3. MAIN BODY
4. PAYOFF
5. CTA

Make it natural to speak, specific to the searched topic, and based on verified
current information when applicable.

Do NOT include a list of hooks, thumbnail concepts, title ideas or hashtags.
Do not repeat the same point in different wording.
"""

    else:
        task = """
Create ONLY a thumbnail concept package for the searched topic.

Give exactly 3 distinct thumbnail concepts.

For each concept include:
1. CONCEPT NAME
2. VISUAL COMPOSITION
3. SUBJECT / CHARACTER FOCUS
4. SHORT THUMBNAIL TEXT (3-6 words)
5. EXPRESSION / EMOTION
6. COLOR / LIGHTING DIRECTION
7. WHY IT FITS THIS TOPIC

The concepts must be visually different and tied tightly to the user's topic.
Do not include hooks, scripts, titles or hashtags.
"""

    return f"""
You are HookSpike's creative intelligence engine.

USER REQUEST:
{topic}

REQUESTED OUTPUT TYPE:
{content_type}

VERIFIED RESEARCH:
---------------------
{research}
---------------------

{task}

QUALITY RULES:
- The research is the factual source of truth.
- Do not contradict verified facts.
- Do not invent current claims, statistics, dates, names, quotes or announcements.
- If the research says a claim is uncertain, preserve that uncertainty.
- Make every item meaningfully different.
- Avoid generic motivational filler.
- Avoid repeated hooks or near-duplicate wording.
- Do not mention Gemini, OpenAI, HookSpike or internal systems.
- Output in clear English.
"""


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
    content_type,
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
                    content_type=content_type,
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
        timeout=OPENAI_TIMEOUT_SECONDS,
        max_retries=OPENAI_SDK_RETRIES,
    )


# ============================================================
# OPENAI GENERATION
# ============================================================

def _generate_openai(
    client,
    prompt,
    model,
):
    """Generate text using the modern Responses API, with a legacy-compatible fallback."""
    try:
        response = client.responses.create(
            model=model,
            instructions=(
                "You are HookSpike's creative intelligence engine. "
                "Return only the requested creative asset. "
                "Do not research, browse, explain your process, or discuss internal systems."
            ),
            input=prompt,
        )

        output_text = getattr(response, "output_text", None)
        if output_text and output_text.strip():
            return output_text.strip()

        chunks = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                value = getattr(content, "text", None)
                if value:
                    chunks.append(value)
        if chunks:
            return "\n".join(chunks).strip()

    except (AttributeError, TypeError) as exc:
        # Compatibility path for older OpenAI SDK installations.
        print(f"[HookSpike OPENAI] Responses API unavailable; trying Chat Completions | {type(exc).__name__}: {exc}")
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are HookSpike's creative intelligence engine. "
                            "Return only the requested creative asset. "
                            "Do not research or explain your process."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except Exception:
            raise

    return None


def _creative_output_is_valid(content_type, text):
    """Reject research/search-planning output before it reaches the user."""
    if not text or not text.strip():
        return False

    lower = text.lower()
    forbidden = [
        "self-correction",
        "search strategy",
        "let's search",
        "let’s search",
        "i need to search",
        "query:",
        "search process",
    ]
    if any(marker in lower for marker in forbidden):
        return False

    if content_type == "hooks":
        import re
        numbers = re.findall(r"(?m)^\s*(?:hook\s*)?(\d)\s*[.)\-:]\s+", text, re.IGNORECASE)
        return sorted(set(numbers)) == ["1", "2", "3", "4", "5", "6", "7"]

    if content_type == "script":
        required = ["HOOK", "SETUP", "MAIN BODY", "PAYOFF", "CTA"]
        return all(item in text.upper() for item in required)

    if content_type == "thumbnail":
        return text.upper().count("CONCEPT NAME") >= 3 and text.upper().count("THUMBNAIL TEXT") >= 3

    return True


def _repair_creative_output(client, model, content_type, text):
    """One strict formatting repair; never turns research into the final asset."""
    repair_prompt = f"""
Your previous answer was rejected because it did not follow the required output format.

CONTENT TYPE: {content_type}

PREVIOUS OUTPUT:
{text[:12000]}

Return ONLY the corrected final asset. Do not explain the correction.

For hooks: output exactly 7 genuinely different hooks numbered 1 through 7.
For script: output exactly one script with HOOK, SETUP, MAIN BODY, PAYOFF, CTA headings.
For thumbnail: output exactly 3 distinct concepts, each containing CONCEPT NAME and THUMBNAIL TEXT.
Do not mention searching, queries, research process, Gemini, OpenAI, or internal systems.
"""
    return _generate_openai(client, repair_prompt, model)


# ============================================================
# OPENAI DEBUG / RESEARCH COMPACTION HELPERS
# ============================================================

def _compact_research_for_openai(research):
    """Keep the creative request focused without throwing away all research."""
    if not research:
        return ""

    text = str(research).strip()
    if len(text) <= MAX_RESEARCH_FOR_OPENAI_CHARS:
        return text

    # Preserve the beginning (verified facts/status) and the ending (sources),
    # while avoiding a huge middle section that can slow the creative call.
    head_size = int(MAX_RESEARCH_FOR_OPENAI_CHARS * 0.72)
    tail_size = MAX_RESEARCH_FOR_OPENAI_CHARS - head_size

    return (
        text[:head_size]
        + "\n\n[Research middle section compacted for creative generation.]\n\n"
        + text[-tail_size:]
    )


def _format_openai_error(exc):
    """Return useful diagnostics without ever printing an API key."""
    error_type = type(exc).__name__
    message = str(exc).strip() or "No error message returned."

    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "status", None)

    code = getattr(exc, "code", None)
    request_id = getattr(exc, "request_id", None)

    parts = [error_type]
    if status is not None:
        parts.append(f"status={status}")
    if code:
        parts.append(f"code={code}")
    if request_id:
        parts.append(f"request_id={request_id}")

    return f"{' | '.join(parts)} | message={message}"


# ============================================================
# OPENAI CREATIVE ENGINE
# ============================================================

def _openai_creative(
    topic,
    content_type,
    research,
):
    keys = _get_openai_keys()

    if not keys:
        return (
            None,
            "OpenAI API key is not configured."
        )

    compact_research = _compact_research_for_openai(research)

    print(
        f"[HookSpike OPENAI] Starting creative generation | "
        f"type={content_type} | research_chars={len(compact_research)}"
    )

    prompt = _build_creative_prompt(
        content_type=content_type,
        topic=topic,
        research=compact_research,
    )

    last_error = None

    for api_key in keys:

        try:
            client = _get_openai_client(
                api_key
            )

        except Exception as exc:
            last_error = (
                f"OpenAI client error: {_format_openai_error(exc)}"
            )
            print(
                f"[HookSpike OPENAI ERROR] client setup | "
                f"{last_error}"
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
                        if _creative_output_is_valid(content_type, result):
                            print(
                                f"[HookSpike OPENAI] Success | model={model} | "
                                f"output_chars={len(result)}"
                            )
                            return (result[:MAX_CREATIVE_CHARS], None)

                        print(
                            f"[HookSpike OPENAI] Invalid creative format | model={model} | "
                            "attempting one strict repair"
                        )

                        try:
                            repaired = _repair_creative_output(
                                client=client,
                                model=model,
                                content_type=content_type,
                                text=result,
                            )
                        except Exception as repair_exc:
                            repaired = None
                            print(
                                f"[HookSpike OPENAI ERROR] repair failed | "
                                f"{_format_openai_error(repair_exc)}"
                            )

                        if repaired and _creative_output_is_valid(content_type, repaired):
                            print(
                                f"[HookSpike OPENAI] Repair success | model={model} | "
                                f"output_chars={len(repaired)}"
                            )
                            return (repaired[:MAX_CREATIVE_CHARS], None)

                        last_error = (
                            f"{model} returned invalid creative output."
                        )
                        print(
                            f"[HookSpike OPENAI ERROR] model={model} | invalid creative output"
                        )
                    else:
                        last_error = (
                            f"{model} returned an empty response."
                        )
                    print(
                        f"[HookSpike OPENAI ERROR] model={model} | "
                        f"empty response"
                    )

                except Exception as exc:

                    last_error = (
                        f"{model}: {_format_openai_error(exc)}"
                    )

                    print(
                        f"[HookSpike OPENAI ERROR] model={model} | "
                        f"key_slot={keys.index(api_key) + 1} | "
                        f"{last_error}"
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

    final_error = last_error or "OpenAI creative generation failed."

    print(
        f"[HookSpike OPENAI FAILURE] {final_error}"
    )

    return (
        None,
        final_error
    )


# ============================================================
# THUMBNAIL IMAGE GENERATION
# ============================================================

def generate_thumbnail_image(topic, thumbnail_text):
    """
    Generate one thumbnail visual ONLY when the user explicitly asks for it.

    The image request uses a dedicated image key when configured. If that
    variable is missing, the existing OpenAI backup key is used. Failure is
    intentionally returned to the UI as an image-only error; it never replaces
    or damages the already-generated thumbnail text.
    """
    api_key = (
        OPENAI_IMAGE_API_KEY
        or OPENAI_BACKUP_KEY
    )

    if not api_key:
        return {
            "ok": False,
            "image": None,
            "error": "⚠️ Image server is busy — thumbnail image can't be generated right now."
        }

    prompt = f"""
Create a high-impact YouTube/social-media thumbnail concept image.

Topic: {topic}

Thumbnail direction:
{thumbnail_text}

IMPORTANT:
- This is an illustrative thumbnail IDEA, not a factual photograph.
- Use a clean, dramatic, creator-friendly composition.
- Make the main subject immediately readable on a phone screen.
- Leave sensible space for a short text overlay.
- Do not add fake logos, fake official announcements, or misleading claims.
- Do not rely on tiny unreadable text inside the image.
- No watermark.
"""

    try:
        client = _get_openai_client(api_key)
        response = client.images.generate(
            model=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2"),
            prompt=prompt,
            size="1536x1024",
            quality="low",
        )
        data = getattr(response, "data", None) or []
        if data:
            b64 = getattr(data[0], "b64_json", None)
            if b64:
                return {
                    "ok": True,
                    "image": "data:image/png;base64," + b64,
                    "error": None,
                }

            url = getattr(data[0], "url", None)
            if url:
                return {
                    "ok": True,
                    "image": url,
                    "error": None,
                }

    except Exception as exc:
        print(f"Thumbnail image generation failed: {exc}")

    return {
        "ok": False,
        "image": None,
        "error": "⚠️ Image server is busy — thumbnail image can't be generated right now. Please try again later.",
    }


# MAIN PUBLIC FUNCTION
# ============================================================

def get_ai_response(
    content_type,
    topic,
):
    """
    Main function used by main.py.

    content_type:
        hooks | script | thumbnail

    Pipeline:
        Gemini current-fact verification
                    |
                    v
        OpenAI generates ONLY requested asset
                    |
                    v
        Thumbnail requests optionally receive one AI visual example
    """

    if not topic:
        return "❌ Please enter a question or topic first."

    topic = str(topic).strip()

    if not topic:
        return "❌ Please enter a question or topic first."

    if len(topic) > MAX_TOPIC_CHARS:
        topic = topic[:MAX_TOPIC_CHARS]

    content_type = str(content_type or "hooks").strip().lower()

    if content_type not in {"hooks", "script", "thumbnail"}:
        content_type = "hooks"

    # Current verification is deliberately enabled for creator topics.
    use_search = True

    research = None
    research_error = None

    try:
        research, research_error = _gemini_research(
            topic=topic,
            content_type=content_type,
            use_search=use_search,
        )
    except Exception as exc:
        research_error = f"Gemini research exception: {exc}"

    creative = None
    creative_error = None

    if research:
        try:
            creative, creative_error = _openai_creative(
                topic=topic,
                content_type=content_type,
                research=research,
            )
        except Exception as exc:
            creative_error = f"OpenAI creative exception: {exc}"
    else:
        # Keep the service usable if research temporarily fails.
        fallback_research = """
Current web research was temporarily unavailable.

Work only from the user's exact request.
Do not invent current facts, announcements, dates, statistics, quotes or sources.
If a current claim cannot be verified, explicitly mark it as unverified.
"""

        try:
            creative, creative_error = _openai_creative(
                topic=topic,
                content_type=content_type,
                research=fallback_research,
            )
        except Exception as exc:
            creative_error = f"OpenAI creative exception: {exc}"

    if creative:
        # Thumbnail images are deliberately NOT generated here.
        # The UI asks for the image only after the user clicks the button.
        return {
            "text": creative,
            "image": None,
            "content_type": content_type,
        }

    # NEVER expose Gemini's research brief as the final creative result.
    # If OpenAI fails, main.py receives the normal temporary-busy response.
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
