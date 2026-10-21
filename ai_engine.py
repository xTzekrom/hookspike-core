"""
HookSpike Creator Intelligence Engine
====================================
Flow:
  1. Research & Verification -> Gemini 3.8 Flash (Google Search)
  2. Creative Polish -> OpenAI (Primary)
  3. Seamless Failover -> Gemini 3.8 Flash (Fallback if OpenAI credits are 0)
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
OPENAI_IMAGE_API_KEY = os.environ.get("OPENAI_IMAGE_API_KEY")

# Tere exact working Gemini 3 models
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
]

OPENAI_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
]

MAX_RESEARCH_CHARS = 28000
MAX_TOPIC_CHARS = 12000
MAX_CREATIVE_CHARS = 40000
OPENAI_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 2


# ============================================================
# KEY HELPERS
# ============================================================

def _get_gemini_keys():
    return list(dict.fromkeys([x for x in (PRIMARY_KEY, BACKUP_KEY) if x]))

def _get_openai_keys():
    return list(dict.fromkeys([x for x in (OPENAI_API_KEY, OPENAI_BACKUP_KEY) if x]))

def _backoff(attempt):
    time.sleep(min(2.0, 0.5 * attempt))


# ============================================================
# GEMINI LAYER (RESEARCH & FALLBACK)
# ============================================================

def _build_research_prompt(content_type: str, topic: str) -> str:
    return f"""
You are HookSpike's research engine for creators.
REQUEST TYPE: {content_type}
EXACT USER TOPIC: {topic}

RESEARCH RULES:
1. Verify current facts and recent developments using Google Search.
2. Distinguish verified facts from rumors.
3. Provide crisp creator intelligence:
- VERIFIED FACTS
- CURRENT STATUS
- CREATOR ANGLES
- AUDIENCE HOOK POINTS
"""

def _gemini_generate_text(prompt: str, use_search: bool = True):
    keys = _get_gemini_keys()
    if not keys:
        return None, "Gemini API key is not configured."

    last_error = None
    for key in keys:
        try:
            client = genai.Client(api_key=key)
        except Exception as exc:
            last_error = str(exc)
            continue

        for model in GEMINI_MODELS:
            tools = [types.Tool(google_search=types.GoogleSearch())] if use_search else []
            config_args = {"max_output_tokens": 8000}
            if tools:
                config_args["tools"] = tools

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(**config_args),
                    )
                    text = getattr(response, "text", None)
                    if text and text.strip():
                        return text.strip(), None
                except Exception as exc:
                    last_error = f"{model}: {exc}"
                    if use_search and attempt == 1:
                        tools = []
                        config_args.pop("tools", None)
                        continue
                    _backoff(attempt)
    return None, last_error or "Gemini call failed."


def _gemini_research(topic, content_type):
    prompt = _build_research_prompt(content_type, topic)
    res, err = _gemini_generate_text(prompt, use_search=True)
    if res:
        return res[:MAX_RESEARCH_CHARS], None
    return None, err


# ============================================================
# CREATIVE GENERATION (OPENAI WITH AUTO GEMINI FALLBACK)
# ============================================================

def _creative_prompt(content_type, topic, research, brand_voice=""):
    voice = brand_voice.strip()[:4000] if brand_voice else "Natural, confident, engaging creator voice."

    if content_type == "hooks":
        task = """
Create exactly 7 spoken opening hooks numbered 1 to 7:
1. Strongest curiosity gap
2. Surprising contrast / fact
3. Direct viewer problem
4. Bold claim
5. Story open-loop
6. Question / challenge
7. Quick value promise

End with:
🏆 BEST HOOK: Pick the strongest one and explain why in 1 sentence.
"""
    elif content_type == "script":
        task = """
Create one complete ready-to-record script with clear sections:
🎯 HOOK
🧩 SETUP
🔥 MAIN BODY
💥 PAYOFF
📣 CTA
"""
    else:
        task = """
Create 3 distinct thumbnail concepts:
For each concept provide:
- CONCEPT NAME
- THUMBNAIL TEXT (2-4 words max)
- VISUAL COMPOSITION
- EMOTION / LIGHTING
"""

    return f"""
You are HookSpike's senior creator strategist and creative director.
TOPIC: {topic}
CREATOR VOICE: {voice}
VERIFIED FACTS / CONTEXT:
{research}

{task}

Creator Voice Guidelines:
- Sound like a real, confident creator.
- Fast pacing, high engagement, zero boring corporate fluff.
"""

def _generate_openai(prompt):
    keys = _get_openai_keys()
    if not keys:
        return None, "OpenAI key missing"

    try:
        from openai import OpenAI
    except ImportError:
        return None, "OpenAI library not installed"

    for key in keys:
        try:
            client = OpenAI(api_key=key, timeout=OPENAI_TIMEOUT_SECONDS, max_retries=1)
        except Exception:
            continue

        for model in OPENAI_MODELS:
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are an elite YouTube creator strategist."},
                        {"role": "user", "content": prompt},
                    ],
                )
                text = completion.choices[0].message.content
                if text and text.strip():
                    return text.strip()[:MAX_CREATIVE_CHARS], None
            except Exception:
                # Quota exhausted ya API error aane par chupchap fallback par jane do
                continue

    return None, "OpenAI generation failed or credits exhausted."


def _produce_creative_asset(topic, content_type, research, brand_voice=""):
    prompt = _creative_prompt(content_type, topic, research, brand_voice)

    # 1. Pehle OpenAI try karo (agar credits honge toh best output dega)
    openai_result, _ = _generate_openai(prompt)
    if openai_result:
        return openai_result, None

    # 2. Agar OpenAI fail hua (credits 0), Gemini 3.8 Flash backup le lega
    gemini_result, gemini_err = _gemini_generate_text(prompt, use_search=False)
    if gemini_result:
        return gemini_result[:MAX_CREATIVE_CHARS], None

    return None, "All AI engines are busy right now. Please try again."


# ============================================================
# MAIN API ROUTES CALLED BY main.py
# ============================================================

def get_ai_response(content_type, topic, brand_voice=""):
    if not str(topic or "").strip():
        return "❌ Please enter a question or topic first."

    topic = str(topic).strip()[:MAX_TOPIC_CHARS]
    content_type = str(content_type or "hooks").strip().lower()
    if content_type not in {"hooks", "script", "thumbnail"}:
        content_type = "hooks"

    # Step 1: Gemini 3.8 Flash live research
    research, _ = _gemini_research(topic, content_type)
    if not research:
        research = "Treat topic with general creator knowledge. Search unavailable."

    # Step 2: Creative generation (OpenAI -> Gemini fallback)
    creative, error = _produce_creative_asset(topic, content_type, research, brand_voice)
    if creative:
        return {"text": creative, "image": None, "content_type": content_type}

    return "⚠️ AI is temporarily busy right now. Please try again in a few seconds."


def generate_thumbnail_image(topic, thumbnail_text):
    api_key = OPENAI_IMAGE_API_KEY or OPENAI_API_KEY or OPENAI_BACKUP_KEY
    if not api_key:
        return {"ok": False, "image": None, "error": "⚠️ Image generation key not configured."}

    prompt = f"YouTube thumbnail idea for: {topic}. Text overlay: {thumbnail_text}. High contrast, clean, eye-catching."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=40)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt[:1000],
            size="1024x1024",
            quality="standard",
        )
        url = response.data[0].url
        if url:
            return {"ok": True, "image": url, "error": None}
    except Exception as exc:
        print("[HookSpike Image Error]:", exc)
    return {"ok": False, "image": None, "error": "⚠️ Thumbnail image server busy. Text concepts are safe!"}


# ============================================================
# STUDIO WORKFLOWS
# ============================================================

def generate_creator_pack(topic, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    if not topic:
        return None, "Please enter a topic first."

    research, _ = _gemini_research(topic, "creator_pack")
    prompt = f"""
Build a complete publish-ready creator system:
TOPIC: {topic}
VOICE: {brand_voice or 'Natural creator voice.'}
RESEARCH: {research or 'Standard creator context.'}

Output format:
🔥 TITLE OPTIONS (5 punchy options)
🪝 HOOK OPTIONS (7 distinct hooks numbered 1-7)
🎬 SCRIPT (HOOK, SETUP, BODY, PAYOFF, CTA)
🖼️ THUMBNAIL CONCEPTS (3 ideas with visual details)
#️⃣ HASHTAGS (8 relevant)
🔑 KEYWORDS (10 tags)
"""
    return _produce_creative_asset(topic, "script", prompt, brand_voice)


def refine_creator_content(topic, content, action, brand_voice=""):
    if not content:
        return None, "Content is empty."
    prompt = f"""
You are HookSpike's senior creator editor.
TOPIC: {topic}
ACTION: Make this {action}
CONTENT:
{content}

Return ONLY the refined content with maximum impact.
"""
    return _produce_creative_asset(topic, "refine", prompt, brand_voice)


def analyze_hook(hook, topic=""):
    if not hook:
        return None, "Please enter a hook."
    prompt = f"""
Analyze this hook for short/long form video:
TOPIC: {topic}
HOOK: {hook}

Provide:
🎯 CLARITY
🧲 CURIOSITY
⚡ FIRST-SECONDS IMPACT
🚨 BIGGEST WEAKNESS
🛠️ 3 STRONGER VERSIONS (Clear, Curiosity-led, Bold)
"""
    return _produce_creative_asset(topic, "analysis", prompt)


def discover_topics(category="general"):
    research, _ = _gemini_research(f"Trending opportunities in {category}", "radar")
    prompt = f"""
Based on this research:
{research}

Give 6 high-opportunity content ideas for creators in {category}:
For each: Topic, Why Now, Angle, and Title idea.
"""
    return _produce_creative_asset(category, "trends", prompt)


def generate_packaging_lab(topic, brand_voice=""):
    prompt = f"Create 3 distinct video packaging systems (Title + Thumbnail Text + Visual Concept + Opening Hook) for topic: {topic}"
    return _produce_creative_asset(topic, "packaging", prompt, brand_voice)


def generate_ab_packs(topic, brand_voice=""):
    prompt = f"Create 3 A/B test variations (Curiosity vs Search vs Bold) for topic: {topic}"
    return _produce_creative_asset(topic, "ab_pack", prompt, brand_voice)


def performance_coach(topic, metrics):
    prompt = f"Diagnose these video metrics for topic '{topic}':\n{metrics}\nProvide bottleneck analysis and top 3 fixes."
    return _produce_creative_asset(topic, "coach", prompt)


def generate_content_plan(niche, goal="growth"):
    prompt = f"Build a practical 7-day content schedule for niche '{niche}' with goal '{goal}'. Day-by-day ideas and hooks."
    return _produce_creative_asset(niche, "planner", prompt)


def repurpose_creator_content(content, source="YouTube", target="Instagram Reels"):
    prompt = f"Repurpose this {source} content for {target}. Keep it native, high tension and fast paced:\n{content}"
    return _produce_creative_asset("Repurpose", "repurpose", prompt)
