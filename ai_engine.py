"""
HookSpike Creator Intelligence Engine
====================================

Core philosophy:
    INPUT
      -> CURRENT RESEARCH / VERIFICATION (Gemini + Google Search)
      -> CREATOR STRATEGY
      -> CREATIVE GENERATION (OpenAI)
      -> LOCAL QUALITY GATE
      -> OPTIONAL AI QUALITY PASS
      -> FINAL CREATOR ASSET

Public API kept compatible with main.py:
    get_ai_response
    generate_thumbnail_image
    generate_creator_pack
    refine_creator_content
    analyze_hook
    discover_topics
    run_creator_workflow

The engine deliberately does NOT promise guaranteed virality. It is designed to
maximize usefulness while refusing fabricated current facts, fake certainty,
and meaningless generic filler.
"""

import os
import re
import time
from typing import Any, Dict, Optional, Tuple

from google import genai
from google.genai import types


# ============================================================
# CONFIG
# ============================================================

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BACKUP_KEY = os.environ.get("OPENAI_BACKUP_KEY")
OPENAI_IMAGE_API_KEY = os.environ.get("OPENAI_IMAGE_API_KEY")

GEMINI_PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_MODELS = list(dict.fromkeys([
    GEMINI_PRIMARY_MODEL,
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]))

# Prefer a stronger model when available, but retain the existing fallbacks so
# a newly deployed project does not die simply because one model is unavailable.
OPENAI_PRIMARY_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-sol")
OPENAI_MODELS = list(dict.fromkeys([
    OPENAI_PRIMARY_MODEL,
    "gpt-5.6-sol",
    "gpt-6-luna",
    "gpt-4.1-mini",
    "gpt-4o-mini",
]))

MAX_RESEARCH_CHARS = 28000
MAX_RESEARCH_FOR_OPENAI_CHARS = 16000
MAX_TOPIC_CHARS = 12000
MAX_CREATIVE_CHARS = 40000
OPENAI_TIMEOUT_SECONDS = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "120"))
OPENAI_SDK_RETRIES = int(os.environ.get("OPENAI_SDK_RETRIES", "2"))
MAX_RETRIES = int(os.environ.get("HOOKSPIKE_MAX_RETRIES", "2"))
QUALITY_PASS = os.environ.get("HOOKSPIKE_QUALITY_PASS", "1").lower() not in {"0", "false", "no"}
GEMINI_THINKING_LEVEL = os.environ.get("GEMINI_THINKING_LEVEL", "medium")


# ============================================================
# KEY / ERROR HELPERS
# ============================================================

def _get_gemini_keys():
    return list(dict.fromkeys([x for x in (PRIMARY_KEY, BACKUP_KEY) if x]))


def _get_openai_keys():
    return list(dict.fromkeys([x for x in (OPENAI_API_KEY, OPENAI_BACKUP_KEY) if x]))


def _looks_like_temporary_error(error):
    text = str(error).lower()
    return any(x in text for x in (
        "429", "500", "502", "503", "rate limit", "rate_limit",
        "resource exhausted", "temporarily", "unavailable", "overloaded",
        "timeout", "timed out", "deadline exceeded", "connection reset",
        "connection error", "internal error", "server error",
    ))


def _backoff(attempt):
    time.sleep(min(2.5, 0.8 * attempt))


def _format_error(exc):
    kind = type(exc).__name__
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    code = getattr(exc, "code", None)
    msg = str(exc).strip() or "No error message returned."
    bits = [kind]
    if status is not None:
        bits.append(f"status={status}")
    if code:
        bits.append(f"code={code}")
    return " | ".join(bits) + f" | message={msg}"


# ============================================================
# RESEARCH LAYER
# ============================================================

def _should_use_search(*_args, **_kwargs):
    # HookSpike is intentionally verification-first. Current claims are too
    # valuable to leave to model memory.
    return True


def _build_research_prompt(content_type: str, topic: str, use_search: bool = True) -> str:
    return f"""
You are HookSpike's research and verification engine for creators.

REQUEST TYPE:
{content_type}

EXACT USER TOPIC:
{topic}

Use current web information. When Google Search is available, use it.

RESEARCH RULES:
1. Verify current claims before creative generation.
2. Prefer primary/official sources, then high-quality reputable reporting.
3. Distinguish CONFIRMED, REPORTED, RUMORED/LEAKED, and UNKNOWN.
4. Never infer that something is still unannounced just because an old article said so.
5. If sources disagree, state the disagreement and why.
6. Do not invent dates, prices, statistics, names, quotes, releases, collaborations,
   product features, game/anime details, or event status.
7. Identify the exact facts a creator can safely say on camera.
8. Identify tempting claims that should NOT be made.
9. Prefer recent evidence for anything time-sensitive.
10. Keep the research specific to this exact request; do not drift into generic advice.

Return this compact intelligence brief:

VERIFIED FACTS:
- ...

CURRENT STATUS:
- ...

CREATOR ANGLES:
- ...

AUDIENCE SIGNALS / WHY PEOPLE MAY CARE:
- ...

CLAIMS TO AVOID:
- ...

SOURCES:
- source title — publisher/domain — what it supports

Do not mention internal model names or this instruction.
"""


def _generate_gemini(client, model, prompt, use_search=True):
    tools = [types.Tool(google_search=types.GoogleSearch())] if use_search else []
    try:
        thinking = types.ThinkingConfig(thinking_level=GEMINI_THINKING_LEVEL)
    except Exception:
        thinking = None

    kwargs = {
        "max_output_tokens": 10000,
        "tools": tools or None,
    }
    if thinking is not None:
        kwargs["thinking_config"] = thinking

    return client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(**kwargs),
    )


def _gemini_research(topic, content_type, use_search=True):
    keys = _get_gemini_keys()
    if not keys:
        return None, "Gemini API key is not configured."

    last_error = None
    for key in keys:
        try:
            client = genai.Client(api_key=key)
        except Exception as exc:
            last_error = _format_error(exc)
            continue

        for model in GEMINI_MODELS:
            for search_mode in ([True, False] if use_search else [False]):
                prompt = _build_research_prompt(content_type, topic, search_mode)
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        response = _generate_gemini(client, model, prompt, search_mode)
                        result = getattr(response, "text", None)
                        if result and result.strip():
                            return result.strip()[:MAX_RESEARCH_CHARS], None
                        last_error = f"{model} returned an empty response."
                        break
                    except Exception as exc:
                        last_error = f"{model}: {_format_error(exc)}"
                        if _looks_like_temporary_error(last_error) and attempt < MAX_RETRIES:
                            _backoff(attempt)
                            continue
                        break
    return None, last_error or "Gemini research failed."


def _compact_research_for_openai(research):
    if not research:
        return ""
    text = str(research).strip()
    if len(text) <= MAX_RESEARCH_FOR_OPENAI_CHARS:
        return text
    head = int(MAX_RESEARCH_FOR_OPENAI_CHARS * 0.72)
    tail = MAX_RESEARCH_FOR_OPENAI_CHARS - head
    return text[:head] + "\n\n[Middle research compacted.]\n\n" + text[-tail:]


# ============================================================
# OPENAI LAYER
# ============================================================

def _get_openai_client(api_key):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI SDK is missing. Add 'openai' to requirements.txt and redeploy.") from exc
    return OpenAI(
        api_key=api_key,
        timeout=OPENAI_TIMEOUT_SECONDS,
        max_retries=OPENAI_SDK_RETRIES,
    )


def _generate_openai(client, prompt, model, system=None):
    system = system or (
        "You are HookSpike's senior creator strategist and creative director. "
        "Produce the requested asset only. Never invent current facts."
    )
    try:
        response = client.responses.create(
            model=model,
            instructions=system,
            input=prompt,
        )
        text = getattr(response, "output_text", None)
        if text and text.strip():
            return text.strip()
        chunks = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                value = getattr(content, "text", None)
                if value:
                    chunks.append(value)
        if chunks:
            return "\n".join(chunks).strip()
    except (AttributeError, TypeError):
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content
        if content and content.strip():
            return content.strip()
    return None


def _openai_freeform(prompt, purpose="creator tool", *, quality=True):
    keys = _get_openai_keys()
    if not keys:
        return None, "OpenAI API key is not configured."

    last_error = None
    for key in keys:
        try:
            client = _get_openai_client(key)
        except Exception as exc:
            last_error = _format_error(exc)
            continue

        for model in OPENAI_MODELS:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = _generate_openai(client, prompt, model)
                    if result and result.strip():
                        return result.strip()[:MAX_CREATIVE_CHARS], None
                    last_error = f"{model} returned an empty response."
                except Exception as exc:
                    last_error = f"{model}: {_format_error(exc)}"
                    if _looks_like_temporary_error(last_error) and attempt < MAX_RETRIES:
                        _backoff(attempt)
                        continue
                break
    return None, last_error or f"{purpose} failed."


# ============================================================
# QUALITY / CREATIVE PROMPTS
# ============================================================

VOICE_RULES = """
Creator voice rules:
- Sound like a real creator, not a marketing brochure.
- Prefer concrete nouns, verbs, tension, specificity and natural spoken rhythm.
- Avoid empty phrases such as 'you won't believe', 'game changer', 'in today's world'.
- Never manufacture urgency, controversy or certainty.
- If the topic is factual/current, the research brief is the source of truth.
"""


def _creative_prompt(content_type, topic, research, brand_voice=""):
    research = _compact_research_for_openai(research)
    voice = brand_voice.strip()[:4000] if brand_voice else "Natural, confident, conversational creator voice."

    if content_type == "hooks":
        task = """
Create exactly 7 spoken opening hooks.

Make the seven angles genuinely different:
1. strongest curiosity gap
2. surprising fact/contrast
3. direct viewer problem
4. bold but defensible claim
5. story/open-loop
6. question/challenge
7. fast value promise

Each must be one or two natural spoken sentences and directly tied to the topic.
After them add:
🏆 BEST HOOK: pick one and explain in one sentence why it fits this topic.
"""
    elif content_type == "script":
        task = """
Create one ready-to-record script. Use:
🎯 HOOK
🧩 SETUP
🔥 MAIN BODY
💥 PAYOFF
📣 CTA

The first lines must pay off the title/thumbnail promise immediately.
Use concrete details from verified research. Keep the pacing tight and avoid repeating points.
"""
    else:
        task = """
Create exactly 3 distinct thumbnail concepts.
For each:
CONCEPT NAME
THUMBNAIL TEXT (2-5 words)
VISUAL COMPOSITION
MAIN SUBJECT
EMOTION / EXPRESSION
COLOR / LIGHTING
WHY IT SHOULD WORK

Optimize for phone-size clarity: one dominant subject, one obvious idea, short readable text.
Do not put tiny paragraphs into the image.
"""

    return f"""
You are the senior creative director for a serious creator platform.

USER TOPIC:
{topic}

CREATOR VOICE:
{voice}

VERIFIED RESEARCH:
{research}

{task}

{VOICE_RULES}

NON-NEGOTIABLE FACT RULES:
- Do not contradict the research.
- Do not invent current announcements, dates, numbers, names, quotes or sources.
- If something is uncertain, do not state it as confirmed.
- Never use fake leaks or fabricated insider language.
- Do not mention AI systems, prompts or internal tools.
- Use only a few useful emojis as section markers.
"""


def _local_quality_check(content_type, text):
    if not text or len(text.strip()) < 30:
        return False, "empty_or_too_short"
    lower = text.lower()
    bad = [
        "let's search", "let’s search", "i need to search", "search strategy",
        "query:", "search process", "as an ai", "internal system",
    ]
    if any(x in lower for x in bad):
        return False, "process_leak"

    if content_type == "hooks":
        nums = re.findall(r"(?m)^\s*(?:\*\*)?\s*(?:hook\s*)?([1-7])\s*(?:[.)\-:]|\*\*[.)\-:])", text, re.I)
        seen = []
        for n in nums:
            if n not in seen:
                seen.append(n)
        if seen != ["1", "2", "3", "4", "5", "6", "7"]:
            return False, "hook_count_or_format"

    if content_type == "script":
        upper = text.upper()
        if not all(x in upper for x in ["HOOK", "SETUP", "MAIN BODY", "PAYOFF", "CTA"]):
            return False, "script_sections"

    if content_type == "thumbnail":
        upper = text.upper()
        if upper.count("CONCEPT NAME") < 3 or upper.count("THUMBNAIL TEXT") < 3:
            return False, "thumbnail_concepts"

    return True, "ok"


def _quality_rewrite(content_type, topic, research, text, brand_voice=""):
    prompt = f"""
You are HookSpike's final quality editor.

TOPIC:
{topic}

RESEARCH:
{_compact_research_for_openai(research)}

CREATOR VOICE:
{brand_voice or 'Natural creator voice.'}

DRAFT:
{text[:MAX_CREATIVE_CHARS]}

Rewrite the draft into a stronger final asset.

Quality checklist:
- factual alignment with research
- topic specificity
- originality between items
- natural spoken language
- no generic filler
- no unsupported current claim
- no clickbait that creates a false expectation
- clear payoff / usefulness
- preserve the requested format

Return ONLY the final asset. Do not explain the edit.
"""
    return _openai_freeform(prompt, "creative quality pass", quality=False)


def _openai_creative(topic, content_type, research, brand_voice=""):
    prompt = _creative_prompt(content_type, topic, research, brand_voice)
    result, error = _openai_freeform(prompt, f"{content_type} generation", quality=False)
    if not result:
        return None, error

    ok, _reason = _local_quality_check(content_type, result)
    if not ok:
        repaired, repair_error = _quality_rewrite(content_type, topic, research, result, brand_voice)
        if repaired:
            result = repaired
            ok, _reason = _local_quality_check(content_type, result)
        if not ok:
            return None, repair_error or "Creative output failed quality validation."

    # Optional second pass. This is deliberately configurable because it costs
    # an additional model call but gives substantially stronger editorial output.
    if QUALITY_PASS:
        improved, _err = _quality_rewrite(content_type, topic, research, result, brand_voice)
        if improved:
            valid, _ = _local_quality_check(content_type, improved)
            if valid:
                result = improved

    return result[:MAX_CREATIVE_CHARS], None


# ============================================================
# MAIN CREATION TOOLS
# ============================================================

def get_ai_response(content_type, topic, brand_voice=""):
    if not str(topic or "").strip():
        return "❌ Please enter a question or topic first."

    topic = str(topic).strip()[:MAX_TOPIC_CHARS]
    content_type = str(content_type or "hooks").strip().lower()
    if content_type not in {"hooks", "script", "thumbnail"}:
        content_type = "hooks"

    research, research_error = _gemini_research(topic, content_type, use_search=True)
    if not research:
        research = (
            "CURRENT RESEARCH UNAVAILABLE. Treat all current/time-sensitive claims as unverified. "
            "Do not invent facts, dates, announcements, statistics or sources."
        )

    creative, creative_error = _openai_creative(topic, content_type, research, brand_voice)
    if creative:
        return {"text": creative, "image": None, "content_type": content_type}

    # Never expose a raw research brief as if it were the final creator asset.
    print("[HookSpike AI FAILURE]", research_error, "|", creative_error, flush=True)
    return "⚠️ AI is temporarily busy right now. Please try again in a few seconds."


def generate_thumbnail_image(topic, thumbnail_text):
    api_key = OPENAI_IMAGE_API_KEY or OPENAI_BACKUP_KEY
    if not api_key:
        return {"ok": False, "image": None, "error": "⚠️ Image generation is not configured yet."}

    prompt = f"""
Create a polished creator thumbnail IDEA image.
Topic: {str(topic or '')[:4000]}
Direction: {str(thumbnail_text or '')[:8000]}

Requirements:
- instantly readable at phone size
- one dominant visual idea
- strong depth and contrast
- cinematic but clean
- leave sensible space for short text overlay
- no fake official logos, fake quotes or fabricated claims
- do not depend on tiny text inside the generated image
- no watermark
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
                return {"ok": True, "image": "data:image/png;base64," + b64, "error": None}
            url = getattr(data[0], "url", None)
            if url:
                return {"ok": True, "image": url, "error": None}
    except Exception as exc:
        print("[HookSpike IMAGE]", _format_error(exc), flush=True)
    return {"ok": False, "image": None, "error": "⚠️ Thumbnail image generation failed. Your text concepts are still safe."}


# ============================================================
# COMPLETE CREATOR PACK
# ============================================================

def generate_creator_pack(topic, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    if not topic:
        return None, "Please enter a topic first."

    research, research_error = _gemini_research(topic, "creator_pack", True)
    research = research or "Current research unavailable. Treat current claims as unverified."
    prompt = f"""
Build a publish-ready creator system around this topic.

TOPIC:
{topic}
CREATOR VOICE:
{brand_voice or 'Natural, confident creator voice.'}
VERIFIED RESEARCH:
{_compact_research_for_openai(research)}

Return ONLY:

🔥 TITLE OPTIONS
1.
2.
3.
4.
5.

🪝 HOOK OPTIONS
Exactly 7 distinct hooks numbered 1-7.

🎬 CORE SCRIPT
HOOK
SETUP
MAIN BODY
PAYOFF
CTA

🖼️ THUMBNAIL SYSTEM
CONCEPT 1 — TEXT / VISUAL / EMOTION
CONCEPT 2 — TEXT / VISUAL / EMOTION
CONCEPT 3 — TEXT / VISUAL / EMOTION

📝 DESCRIPTION
A ready-to-paste description.

#️⃣ HASHTAGS
8-12 relevant hashtags.

🔑 KEYWORDS
10-15 relevant keywords.

🧠 STRATEGY NOTE
One short paragraph explaining the strongest audience promise and the main thing
that must stay consistent between title, thumbnail and opening.

Rules: research is the factual source of truth. Make the package internally consistent.
Do not invent current claims. No generic filler. No internal-system mentions.
"""
    result, error = _openai_freeform(prompt, "complete creator pack", quality=False)
    if result:
        return result, None
    return None, error or research_error or "Creator pack failed."


# ============================================================
# REFINEMENT / ANALYSIS
# ============================================================

def refine_creator_content(topic, content, action, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    content = str(content or "").strip()[:MAX_CREATIVE_CHARS]
    action = str(action or "").strip().lower()
    if not content:
        return None, "Please generate or paste content first."

    actions = {
        "more-curious": "Increase the curiosity gap without changing factual meaning.",
        "more-viral": "Increase attention and emotional tension without fake claims or guarantees.",
        "more-natural": "Rewrite it like a confident human creator speaking naturally.",
        "shorter": "Compress it aggressively while preserving the core value and strongest lines.",
        "cinematic": "Make the storytelling more visual, scene-aware and emotionally paced.",
        "shorts": "Convert it into a tight short-form version with an immediate payoff.",
        "gaming": "Use energetic gaming-creator language while preserving facts.",
        "anime": "Use energetic anime-community language while preserving facts.",
        "thumbnail-clickable": "Improve thumbnail clarity, visual hierarchy and curiosity without misleading clickbait.",
    }
    if action not in actions:
        return None, "Unknown creator action."

    prompt = f"""
You are HookSpike's senior editor.
TOPIC: {topic}
CREATOR VOICE: {brand_voice or 'Natural creator voice.'}
ACTION: {actions[action]}

EXISTING CONTENT:
{content}

Return ONLY the improved content.
Do not add unsupported facts, dates, numbers, quotes, announcements or fake urgency.
Preserve the useful meaning and original content type.
"""
    return _openai_freeform(prompt, f"refine:{action}", quality=False)


def analyze_hook(hook, topic=""):
    hook = str(hook or "").strip()[:8000]
    topic = str(topic or "").strip()[:4000]
    if not hook:
        return None, "Please enter a hook first."

    prompt = f"""
You are a ruthless but constructive creator editor.
TOPIC: {topic or 'Not provided'}
HOOK: {hook}

Analyze the hook as if deciding whether a viewer would understand the promise and want to continue.
Return ONLY:

🎯 CLARITY
What is immediately clear / unclear.

🧲 CURIOSITY
What creates an open loop and what kills it.

⚡ FIRST-SECONDS IMPACT
How quickly the hook earns attention.

🎯 SPECIFICITY
What concrete detail is missing or working.

🔗 PROMISE → PAYOFF FIT
What the viewer expects after hearing it.

🚨 BIGGEST WEAKNESS
One highest-priority problem.

🛠️ 3 STRONGER VERSIONS
A — safer / clearer
B — curiosity-led
C — bold but honest

Do not promise virality or pretend to know future performance.
"""
    return _openai_freeform(prompt, "hook analyzer", quality=False)


# ============================================================
# FRESH TOPIC RADAR
# ============================================================

def discover_topics(category="general"):
    category = str(category or "general").strip()[:200]
    research, error = _gemini_research(
        f"current creator opportunities in {category}",
        "topic_radar",
        True,
    )
    if not research:
        return None, error or "Topic discovery failed."

    prompt = f"""
Turn this verified research into a creator opportunity radar.
CATEGORY: {category}
RESEARCH:
{_compact_research_for_openai(research)}

Return exactly 8 opportunities. For each:
🔥 OPPORTUNITY
WHY NOW
WHAT IS CONFIRMED
WHAT IS UNCERTAIN
BEST CREATOR ANGLE
BEST FORMAT (SHORT / LONG / BOTH)
TITLE DIRECTION

End with:
🏆 BEST 3 BETS — rank the three opportunities that have the clearest combination of timeliness,
viewer relevance and content potential. Do not predict views.

Never invent a trend. Never turn a rumor into a fact.
"""
    return _openai_freeform(prompt, "topic radar", quality=False)


# ============================================================
# PREMIUM WORKFLOWS
# ============================================================

def _workflow_research(topic, kind):
    research, error = _gemini_research(topic, kind, True)
    return research or "Current research unavailable. Treat current claims as unverified.", error


def generate_packaging_lab(topic, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    if not topic:
        return None, "Please enter a topic first."
    research, error = _workflow_research(topic, "packaging_lab")
    prompt = f"""
Build a premium packaging decision system for this video.
TOPIC: {topic}
VOICE: {brand_voice or 'Natural creator voice.'}
RESEARCH: {_compact_research_for_openai(research)}

Create 3 complete packages. Each package must coordinate title + thumbnail + opening hook.

📦 PACKAGE A — CLEAR / BROAD
TITLE:
THUMBNAIL TEXT:
THUMBNAIL VISUAL:
HOOK:
WHY THIS MATCHES:

📦 PACKAGE B — CURIOSITY
TITLE:
THUMBNAIL TEXT:
THUMBNAIL VISUAL:
HOOK:
WHY THIS MATCHES:

📦 PACKAGE C — BOLD / CONTRAST
TITLE:
THUMBNAIL TEXT:
THUMBNAIL VISUAL:
HOOK:
WHY THIS MATCHES:

🧠 PACKAGING DIAGNOSIS
BEST PROMISE:
BIGGEST CONFUSION RISK:
WHAT THE THUMBNAIL SHOULD NOT REPEAT FROM THE TITLE:
BEST PACKAGE TO START WITH:

Rules: the three packages must feel meaningfully different. No misleading claims.
"""
    return _openai_freeform(prompt, "packaging lab", quality=False)


def generate_ab_packs(topic, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    if not topic:
        return None, "Please enter a topic first."
    research, error = _workflow_research(topic, "ab_pack")
    prompt = f"""
Create three genuinely different tests for the same creator video.
TOPIC: {topic}
VOICE: {brand_voice or 'Natural creator voice.'}
RESEARCH: {_compact_research_for_openai(research)}

A — SEARCH / CLEAR
TITLE:
THUMBNAIL TEXT:
VISUAL:
HOOK:
VIEWER PSYCHOLOGY:

B — CURIOSITY / OPEN LOOP
TITLE:
THUMBNAIL TEXT:
VISUAL:
HOOK:
VIEWER PSYCHOLOGY:

C — CONTRAST / BOLD BUT HONEST
TITLE:
THUMBNAIL TEXT:
VISUAL:
HOOK:
VIEWER PSYCHOLOGY:

🏁 TEST ORDER
Which should be tested first and what signal would justify switching direction?

Do not predict exact CTR or views.
"""
    return _openai_freeform(prompt, "A/B pack generator", quality=False)


def performance_coach(topic, metrics):
    topic = str(topic or "").strip()[:4000]
    metrics = str(metrics or "").strip()[:10000]
    if not metrics:
        return None, "Please enter your video metrics first."

    prompt = f"""
Act as HookSpike's evidence-first creator performance coach.

VIDEO TOPIC:
{topic or 'Not provided'}

SUPPLIED METRICS:
{metrics}

Do not invent missing numbers. Do not pretend to access a platform account.
Use the supplied evidence to separate packaging, retention and audience problems.

Return ONLY:
📊 PERFORMANCE SNAPSHOT
What the supplied numbers actually say.

🎯 PRIMARY BOTTLENECK
The most likely limiting factor and why.

🧲 PACKAGING CHECK
Title / thumbnail / appeal diagnosis. If CTR is missing, say so.

🎬 RETENTION CHECK
Opening / retention diagnosis. If retention is missing, say so.

🚨 TOP 3 ACTIONS
Rank exactly three actions by expected usefulness, not hype.

🧪 NEXT EXPERIMENT
One controlled change for the next upload.

📈 WHAT TO WATCH
Which metric(s) should determine whether the experiment worked.

⚠️ DO NOT OVERREACT TO
One misleading or incomplete conclusion the creator should avoid.

Never guarantee views, subscribers, CTR or revenue.
"""
    return _openai_freeform(prompt, "performance coach", quality=False)


def generate_content_plan(niche, goal="growth"):
    niche = str(niche or "").strip()[:3000]
    goal = str(goal or "growth").strip()[:1000]
    if not niche:
        return None, "Please enter your niche first."
    research, error = _workflow_research(niche, "content_planner")
    prompt = f"""
Build a realistic 7-day creator operating plan.
NICHE: {niche}
GOAL: {goal}
CURRENT RESEARCH: {_compact_research_for_openai(research)}

For each day:
DAY
CONTENT IDEA
AUDIENCE PROBLEM / DESIRE
ANGLE
HOOK
FORMAT
TITLE DIRECTION
THUMBNAIL DIRECTION
REPURPOSE OPPORTUNITY
EFFORT: LOW / MEDIUM / HIGH

End with:
🏁 WEEKLY THESIS
🧪 THE ONE THING TO LEARN THIS WEEK
♻️ CONTENT FLYWHEEL

Keep it achievable for one creator. Use current information only when supported.
"""
    return _openai_freeform(prompt, "7-day content planner", quality=False)


def repurpose_creator_content(content, source_platform="YouTube", target_platform="Instagram Reels"):
    content = str(content or "").strip()[:MAX_CREATIVE_CHARS]
    if not content:
        return None, "Please paste a script or transcript first."
    source_platform = str(source_platform or "YouTube")[:100]
    target_platform = str(target_platform or "Instagram Reels")[:100]
    prompt = f"""
Repurpose the following creator content from {source_platform} for {target_platform}.

SOURCE:
{content}

Do not change factual meaning. Preserve names, numbers and claims exactly unless clearly marked as an editorial rewrite.

Return ONLY:
🎯 TARGET-PLATFORM ANGLE
How the same idea should be reframed for the target audience.

🪝 HOOK OPTIONS
3 platform-native hooks.

🎬 READY-TO-POST VERSION
A complete adapted version.

✂️ CUT / EMPHASIS PLAN
3 moments or ideas to emphasize.

📣 CTA
One natural CTA for the target platform.

🔁 SECOND REPURPOSE
One additional format this content can become.
"""
    return _openai_freeform(prompt, "content repurposer", quality=False)


def run_creator_workflow(action, payload):
    action = str(action or "").strip().lower()
    payload = payload or {}
    topic = str(payload.get("topic", "")).strip()[:MAX_TOPIC_CHARS]
    voice = str(payload.get("brand_voice", "")).strip()[:4000]

    if action == "packaging":
        return generate_packaging_lab(topic, voice)
    if action == "ab_pack":
        return generate_ab_packs(topic, voice)
    if action == "performance":
        return performance_coach(topic, payload.get("metrics", ""))
    if action == "planner":
        return generate_content_plan(payload.get("niche", topic), payload.get("goals", "growth"))
    if action == "repurpose":
        return repurpose_creator_content(payload.get("content", ""), payload.get("source_platform", "YouTube"), payload.get("target_platform", "Instagram Reels"))
    return None, "Unknown creator workflow."


# ============================================================
# SAFE STATUS
# ============================================================

def get_ai_engine_status():
    return {
        "gemini_configured": bool(_get_gemini_keys()),
        "openai_configured": bool(_get_openai_keys()),
        "gemini_model": GEMINI_MODELS[0],
        "gemini_fallback_models": GEMINI_MODELS[1:],
        "openai_model": OPENAI_MODELS[0],
        "openai_fallback_models": OPENAI_MODELS[1:],
        "search_available": bool(_get_gemini_keys()),
        "quality_pass": QUALITY_PASS,
    }
