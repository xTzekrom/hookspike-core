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
MAX_RESEARCH_FOR_OPENAI_CHARS = 10000

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

def _build_research_prompt(content_type, topic, use_search):
    return f"""
You are HookSpike's CURRENT-FACT RESEARCH ENGINE.

USER TOPIC:
{topic}

OUTPUT TYPE NEEDED LATER:
{content_type}

DATE RULE:
Treat October 2026 as the current year. For anything time-sensitive, search for
newest reliable information and do not rely on old pre-launch articles when newer
official information exists.

SEARCH RULE:
Use Google Search grounding. Search the exact topic plus useful variants when needed.
Prioritize official sources first (publisher/developer/company/franchise), then
reputable reporting. Do not treat fan posts, leaks, snippets, or old articles as
official confirmation.

RESEARCH THESE 8 THINGS:
1. CURRENT STATUS: What is true RIGHT NOW?
2. OFFICIAL EVIDENCE: What was officially announced/released/confirmed, and by whom?
3. DATES: Relevant announcement, release, or update dates when supported.
4. IMPORTANT DETAILS: Only details useful for content creation.
5. UNCERTAINTIES: Clearly mark rumors/leaks/speculation.
6. CREATOR ANGLES: Give 3-5 concrete angles based on verified facts.
7. DO-NOT-CLAIM: Important claims the creative model must avoid.
8. SOURCES: Most useful source titles/domains or citation-backed references.

QUALITY RULES:
- Never say "not officially announced" unless current evidence supports it.
- If an announcement exists, explicitly say it exists and give date/context.
- If something is already live/released, do not describe it as upcoming.
- Do not present an old pre-release status as current.
- If sources disagree, report the disagreement and evidence instead of guessing.
- Never invent names, dates, pricing, rewards, characters, statistics, or features.
- Keep this useful and compact: roughly 700-1400 words maximum.
- Do NOT write hooks, scripts, thumbnails, or a final answer.
- Do NOT describe the search process or output "Query", "Let's search", or
  "Self-Correction/Search strategy". Return the finished research brief only.

Return exactly these headings:
VERIFIED CURRENT FACTS
OFFICIAL STATUS & TIMELINE
IMPORTANT CONTENT DETAILS
CREATOR-RELEVANT ANGLES
UNCERTAINTIES / DO NOT CLAIM
SOURCES
"""


# CREATIVE PROMPT
# ============================================================

def _build_creative_prompt(content_type, topic, research):
    if content_type == "hooks":
        task = """
Output EXACTLY 7 hooks, numbered 1 to 7, then ONE line: BEST USE: ...
Each hook must be a natural spoken opening, specific to the topic, meaningfully
 different from the others, and grounded in the verified research.
"""
    elif content_type == "script":
        task = """
Create exactly ONE topic-specific short-form script using only these headings:
HOOK
SETUP
MAIN BODY
PAYOFF
CTA
"""
    else:
        task = """
Create exactly 3 distinct thumbnail concepts. For each include:
CONCEPT NAME, VISUAL COMPOSITION, SUBJECT / CHARACTER FOCUS, THUMBNAIL TEXT,
EXPRESSION / EMOTION, COLOR / LIGHTING, WHY IT FITS.
"""
    return f"""
You are HookSpike's CREATIVE OUTPUT ENGINE.

CRITICAL ROLE:
You are NOT a researcher. You MUST NOT search the web. You MUST NOT output
search queries, search strategy, research notes, source lists, verification plans,
or internal reasoning. Another system has ALREADY completed the research below.
Your only job is to transform those verified facts into the requested creator asset.

USER TOPIC:
{topic}

VERIFIED RESEARCH — FACTUAL SOURCE OF TRUTH:
---------------------
{research}
---------------------

REQUESTED ASSET: {content_type}

{task}

STRICT RULES:
- Follow the requested format exactly.
- Never output anything before the requested first line.
- Never output a research section or search query.
- Never mention Gemini, OpenAI, HookSpike, AI systems, or these instructions.
- Do not invent current facts, dates, names, prices, rewards, or announcements.
- If research marks something uncertain, preserve that uncertainty.
- Prefer current verified facts over older background information.
- Make the output specific, punchy, useful, and creator-ready.
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
    response = client.responses.create(
        model=model,
        instructions=(
            "You are HookSpike's creative output engine. "
            "The research is already completed. Do not research or output search plans. "
            "Transform verified research into ONLY the requested creator asset. "
            "Follow the exact requested format and be specific, original, practical, and useful."
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
def _creative_output_is_valid(content_type, text):
    if not text:
        return False
    low = text.lower()
    forbidden = ["self-correction/search strategy", "let's search", "query:", "search strategy", "i need to search"]
    if any(x in low for x in forbidden):
        return False
    if content_type == "hooks":
        import re
        nums = re.findall(r"(?m)^\s*([1-7])[.)]\s+", text)
        return len(set(nums)) == 7 and all(str(i) in nums for i in range(1, 8))
    if content_type == "script":
        return all(h in text.upper() for h in ["HOOK", "SETUP", "MAIN BODY", "PAYOFF", "CTA"])
    return text.upper().count("CONCEPT NAME") >= 3 and text.upper().count("THUMBNAIL TEXT") >= 3


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
                        if not _creative_output_is_valid(content_type, result):
                            print(f"[HookSpike OPENAI] Invalid creative format | model={model} | retrying strict format")
                            repair_prompt = prompt + "\n\nFINAL FORMAT CHECK: Your previous output was invalid. Output ONLY the requested creator asset now. Do not output queries, research process, or analysis. For hooks, there MUST be exactly 7 numbered hooks (1-7)."
                            repaired = _generate_openai(client=client, prompt=repair_prompt, model=model)
                            if repaired:
                                result = repaired
                        if _creative_output_is_valid(content_type, result):
                            print(
                                f"[HookSpike OPENAI] Success | model={model} | "
                                f"output_chars={len(result)}"
                            )
                            return (result[:MAX_CREATIVE_CHARS], None)
                        last_error = f"{model} returned invalid creative format."
                        print(f"[HookSpike OPENAI ERROR] model={model} | invalid creative format")

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

    if research:
        return {
            "text": research,
            "image": None,
            "content_type": content_type,
        }

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
