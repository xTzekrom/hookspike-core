"""
HookSpike Creator Intelligence Engine (v3.0 - 10/10 Agency Grade)
=================================================================
Architecture:
  1. Live Web Research & Fact Verification -> Gemini 3.8 Flash + Google Search
  2. Primary Creative Engine -> OpenAI (when credits available)
  3. Seamless Instant Failover -> Gemini 3.8 Flash (if OpenAI is out of credits)
  4. Dedicated 10/10 Prompts for Dashboard + All 10 Creator Studio Tools
"""

import os
import time

from google import genai
from google.genai import types

# ============================================================
# CONFIGURATION
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
    "gemini-2.5-flash",
]))

OPENAI_PRIMARY_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MODELS = list(dict.fromkeys([
    OPENAI_PRIMARY_MODEL,
    "gpt-4o-mini",
    "gpt-4o",
]))

MAX_RESEARCH_CHARS = 28000
MAX_TOPIC_CHARS = 12000
MAX_CREATIVE_CHARS = 40000
OPENAI_TIMEOUT_SECONDS = 25.0
MAX_RETRIES = 2


# ============================================================
# HELPERS
# ============================================================

def _get_gemini_keys():
    return list(dict.fromkeys([x for x in (PRIMARY_KEY, BACKUP_KEY) if x]))


def _get_openai_keys():
    return list(dict.fromkeys([x for x in (OPENAI_API_KEY, OPENAI_BACKUP_KEY) if x]))


def _backoff(attempt):
    time.sleep(min(2.0, 0.5 * attempt))


# ============================================================
# GEMINI LAYER (RESEARCH + CREATIVE FALLBACK)
# ============================================================

def _build_research_prompt(content_type: str, topic: str) -> str:
    return f"""
You are HookSpike's real-time verification and research intelligence engine for creators.
REQUEST TYPE: {content_type}
EXACT TOPIC: {topic}

Use Google Search to gather accurate, up-to-date facts.

RESEARCH RULES:
1. Verify current facts, official announcements, dates, and ground reality.
2. Clearly separate CONFIRMED FACTS from RUMORS/LEAKS.
3. Never invent dates, quotes, numbers, or release windows.
4. Identify the strongest psychological angles that make audiences care right now.

Return a crisp intelligence brief:
- VERIFIED FACTS:
- CURRENT STATUS (Confirmed vs Rumored):
- HIGH-RETENTION CREATOR ANGLES:
- CLAIMS TO AVOID (Fake or unverified):
"""


def _gemini_generate_text(prompt: str, use_search: bool = True, system_instruction: str = None):
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
            for search_mode in ([True, False] if use_search else [False]):
                tools = [types.Tool(google_search=types.GoogleSearch())] if search_mode else []
                config_args = {"max_output_tokens": 8192}
                if tools:
                    config_args["tools"] = tools
                if system_instruction:
                    config_args["system_instruction"] = system_instruction

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
                        break
                    except Exception as exc:
                        last_error = f"{model}: {exc}"
                        if attempt < MAX_RETRIES:
                            _backoff(attempt)
                            continue
                        break
    return None, last_error or "Gemini generation failed."


def _gemini_research(topic: str, content_type: str):
    prompt = _build_research_prompt(content_type, topic)
    res, err = _gemini_generate_text(prompt, use_search=True)
    if res:
        return res[:MAX_RESEARCH_CHARS], None
    return None, err


# ============================================================
# CORE GENERATION ROUTER (OPENAI PRIMARY -> GEMINI FALLBACK)
# ============================================================

SYSTEM_DIRECTOR = (
    "You are HookSpike's Senior Creative Director and Viral YouTube/Short-Form Strategist. "
    "You write natural, high-retention, shoot-ready creator assets backed by verified research. "
    "Never use generic AI filler ('in today's digital age', 'game-changer', 'buckle up'). "
    "Output ONLY the requested asset cleanly formatted."
)


def _generate_openai(prompt: str, system: str = SYSTEM_DIRECTOR):
    keys = _get_openai_keys()
    if not keys:
        return None, "OpenAI key not configured."

    try:
        from openai import OpenAI
    except ImportError:
        return None, "OpenAI SDK not installed."

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
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                )
                text = completion.choices[0].message.content
                if text and text.strip():
                    return text.strip()[:MAX_CREATIVE_CHARS], None
            except Exception:
                continue

    return None, "OpenAI credits exhausted or unavailable."


def _execute_creative_prompt(prompt: str):
    """
    Tries OpenAI first for creative polish.
    If OpenAI fails (e.g., 0 credits), seamlessly falls back to Gemini 3.8 Flash.
    """
    # 1. Try OpenAI Primary
    openai_res, _ = _generate_openai(prompt, system=SYSTEM_DIRECTOR)
    if openai_res:
        return openai_res, None

    # 2. Seamless Fallback to Gemini
    gemini_res, gemini_err = _gemini_generate_text(
        prompt,
        use_search=False,
        system_instruction=SYSTEM_DIRECTOR
    )
    if gemini_res:
        return gemini_res[:MAX_CREATIVE_CHARS], None

    return None, gemini_err or "⚠️ AI engines are temporarily busy. Please try again."


# ============================================================
# 10/10 DASHBOARD PROMPTS (HOOKS, SCRIPT, THUMBNAIL)
# ============================================================

def _build_dashboard_prompt(content_type: str, topic: str, research: str, brand_voice: str = "") -> str:
    voice = brand_voice.strip()[:4000] if brand_voice else "Confident, conversational, high-retention modern creator tone."

    if content_type == "hooks":
        task = """
Create 7 genuinely distinct, scroll-stopping spoken opening hooks (numbered 1 to 7).
For every hook, include a bracketed camera/delivery cue like `[Rapid snap zoom]` or `[Lean into mic, deadpan]`.

1. THE CURIOSITY GAP: Open an irresistible loop that viewers must stay to close.
2. THE CONTRARIAN / MYTH-BUSTER: Challenge what 99% of people currently believe about this topic.
3. THE VIEWER STAKES / PAIN POINT: Hit a direct frustration, fear, or missed opportunity.
4. THE VERIFIED BOMBSHELL: Lead with the sharpest, most surprising verified fact from research.
5. THE IN-MEDIA-RES STORY: Drop the viewer straight into the middle of the tension.
6. THE PROVOCATIVE QUESTION: Force the viewer's brain to pause and answer.
7. THE FAST VALUE PROMISE: High-speed clarity on the exact payoff they will get in 60 seconds.

Each hook must be 1 to 2 spoken sentences—natural, punchy, and ready to say on camera.

At the bottom, add:
🏆 **WINNER HOOK TO TEST FIRST**
Pick the #1 strongest hook for this exact topic and explain the viewer psychology in one sharp sentence.
"""
    elif content_type == "script":
        task = """
Write a complete, 10/10 shoot-ready video script engineered for 80%+ audience retention.
Include bracketed production cues (`[Quick snap zoom]`, `[B-roll cue: ...]`, `[Cut to Angle B]`) and pacing notes.

Structure the script with these exact sections:

### 🎯 HOOK
*(Pacing & delivery note)*
Immediate payoff on the topic's core tension in the first 5 seconds. Zero "Hey guys" or channel intros.

### 🧩 SETUP
*(Pacing & delivery note)*
Separate internet rumors from confirmed reality. Establish why this matters right now and open the main story loop.

### 🔥 MAIN BODY
*(Pacing & delivery note)*
Deliver 2 to 3 hard-hitting insights backed by the verified research.
CRITICAL: Use smooth conversational bridges between points (especially when transitioning into technical details or behind-the-scenes facts) so it sounds like a human storyteller, not a listicle.

### 💥 PAYOFF
*(Pacing & delivery note)*
The big-picture takeaway—what this changes for the audience, game, or industry going forward.

### 📣 CTA
*(Pacing & delivery note)*
A specific, polarizing debate question tied to the topic that compels viewers to argue in the comments, followed by a natural subscribe/follow line.
"""
    else:  # thumbnail
        task = """
Design 3 high-CTR, mobile-first thumbnail concepts built to dominate the YouTube browse feed.

For each concept (CONCEPT 1, CONCEPT 2, CONCEPT 3), provide:
- **CONCEPT NAME**: Short memorable title for the angle
- **THUMBNAIL TEXT**: 2 to 4 punchy words MAX (must complement, NOT repeat, the video title)
- **VISUAL COMPOSITION**: Exact foreground subject, background action, and depth separation
- **FACIAL EXPRESSION / TENSION**: Clear human or character emotion readable on a 6-inch phone screen
- **COLOR & LIGHTING CONTRAST**: Specific hex/color clash (e.g., Neon Amber against Dark Slate)
- **WHY THEY CLICK (PSYCHOLOGY)**: The exact curiosity trigger this visual creates

At the bottom, add:
🏆 **BEST THUMBNAIL TO LAUNCH WITH**: Which concept should go live first and what A/B test to run second.
"""

    return f"""
TOPIC: {topic}
CREATOR VOICE / STYLE: {voice}

VERIFIED RESEARCH BRIEF (SOURCE OF TRUTH):
{research}

TASK:
{task}

STRICT RULES:
- Never contradict the verified research or fabricate dates/leaks.
- Write for the ear (natural spoken rhythm, short punchy sentences).
"""


def get_ai_response(content_type, topic, brand_voice=""):
    if not str(topic or "").strip():
        return "❌ Please enter a question or topic first."

    topic = str(topic).strip()[:MAX_TOPIC_CHARS]
    content_type = str(content_type or "hooks").strip().lower()
    if content_type not in {"hooks", "script", "thumbnail"}:
        content_type = "hooks"

    research, _ = _gemini_research(topic, content_type)
    if not research:
        research = "Live search unavailable. Rely on verified foundational knowledge and avoid fabricating current dates."

    prompt = _build_dashboard_prompt(content_type, topic, research, brand_voice)
    creative, error = _execute_creative_prompt(prompt)
    if creative:
        return {"text": creative, "image": None, "content_type": content_type}

    return "⚠️ AI is temporarily busy right now. Please try again in a few seconds."


# ============================================================
# THUMBNAIL IMAGE GENERATOR
# ============================================================

def generate_thumbnail_image(topic, thumbnail_text):
    api_key = OPENAI_IMAGE_API_KEY or OPENAI_API_KEY or OPENAI_BACKUP_KEY
    if not api_key:
        return {"ok": False, "image": None, "error": "⚠️ Image generation API key is not active right now. Your text concepts above are ready to use!"}

    prompt = f"""
High-CTR YouTube thumbnail concept visual for topic: {str(topic or '')[:2000]}.
Concept direction: {str(thumbnail_text or '')[:3000]}.
Style: Cinematic lighting, strong foreground subject, high contrast, ultra-clean mobile readability, space for 3-word text overlay, no watermarks.
"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=45)
        for img_model in ["gpt-image-1", "dall-e-3"]:
            try:
                response = client.images.generate(
                    model=img_model,
                    prompt=prompt[:3500],
                    size="1024x1024",
                )
                data = getattr(response, "data", None) or []
                if data:
                    b64 = getattr(data[0], "b64_json", None)
                    if b64:
                        return {"ok": True, "image": "data:image/png;base64," + b64, "error": None}
                    url = getattr(data[0], "url", None)
                    if url:
                        return {"ok": True, "image": url, "error": None}
            except Exception:
                continue
    except Exception as exc:
        print("[HookSpike IMAGE Error]:", exc, flush=True)

    return {
        "ok": False,
        "image": None,
        "error": "⚠️ Image server has no active credits right now — use your 3 detailed visual concepts above!"
    }


# ============================================================
# 10/10 CREATOR STUDIO WORKFLOW TOOLS
# ============================================================

def generate_creator_pack(topic, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    if not topic:
        return None, "⚠️ Please enter a working topic first."

    research, _ = _gemini_research(topic, "creator_pack")
    research = research or "Use verified foundational facts; do not invent dates."

    prompt = f"""
Build a 10/10 Complete Publish-Ready Creator Pack for this topic.

TOPIC: {topic}
CREATOR VOICE: {brand_voice or 'Natural, high-retention creator voice'}
VERIFIED RESEARCH:
{research}

Format your response with these exact sections:

🔥 **5 HIGH-CTR TITLE OPTIONS**
1. (Curiosity-driven)
2. (Search / Authority)
3. (Contrarian / Warning)
4. (Story / Timeline angle)
5. (Short & Punchy)

🪝 **7 SCROLL-STOPPING HOOKS**
Numbered 1 to 7 with `[Visual/Delivery cues]`. Cover curiosity, contrast, pain-point, verified fact, story, question, and fast promise.

🎬 **SHOOT-READY CORE SCRIPT**
Include `[Camera/B-roll cues]` and smooth transitions:
- 🎯 HOOK
- 🧩 SETUP
- 🔥 MAIN BODY
- 💥 PAYOFF
- 📣 CTA

🖼️ **3 THUMBNAIL CONCEPTS**
For each: Concept Name, Thumbnail Text (2-4 words), Visual Composition, and Color Contrast.

📝 **SEO VIDEO DESCRIPTION**
Ready-to-paste YouTube/Reels description with a strong first 2 lines.

#️⃣ **HASHTAGS & 🔑 KEYWORDS**
10 relevant hashtags and 12 high-intent search keywords.

🧠 **PACKAGING STRATEGY NOTE**
One sharp paragraph on how the Title + Thumbnail + First 5 Seconds work together without repeating each other.
"""
    return _execute_creative_prompt(prompt)


def refine_creator_content(topic, content, action, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    content = str(content or "").strip()[:MAX_CREATIVE_CHARS]
    action = str(action or "").strip().lower()

    if not content and not topic:
        return None, "⚠️ Please enter a topic or generate content first."

    source_material = content or f"Create content around topic: {topic}"

    actions_map = {
        "more-curious": "Amplify the open loops and curiosity gap so viewers feel compelled to keep watching, without clickbait lies.",
        "more-viral": "Sharpen the pacing, emotional stakes, and first-5-second punch for maximum shareability and retention.",
        "more-natural": "Rewrite in a conversational, authentic human creator voice—remove all stiff or robotic phrasing.",
        "shorter": "Cut all fluff and compress by 40% while keeping every high-impact punchline and core insight.",
        "cinematic": "Add vivid visual storytelling, atmospheric B-roll cues, and dramatic pacing shifts.",
        "shorts": "Transform this into a 45-to-60 second vertical Short/Reel script with `[Fast cuts]`, 3-second hook, loopable ending, and punchy lines.",
        "gaming": "Inject authentic gaming-community energy, terminology, and hype while staying 100% factual.",
        "anime": "Inject passionate anime-community energy, lore tension, and hype while staying 100% factual.",
        "thumbnail-clickable": "Upgrade into 3 ultra-clickable thumbnail layouts with 3-word text overlays and extreme visual contrast.",
    }
    instruction = actions_map.get(action, "Polish and upgrade this creator content for higher retention and clarity.")

    # If user is in Shorts mode with only a topic, pull quick research first
    research_context = ""
    if action == "shorts" and len(source_material) < 250:
        res, _ = _gemini_research(topic or source_material, "shorts_script")
        if res:
            research_context = f"\nVERIFIED RESEARCH:\n{res}\n"

    prompt = f"""
TOPIC: {topic or 'Creator Content'}
CREATOR VOICE: {brand_voice or 'Natural, punchy creator tone'}
TRANSFORMATION GOAL: {instruction}
{research_context}
SOURCE MATERIAL:
{source_material}

Deliver ONLY the upgraded, ready-to-use creator asset.
"""
    return _execute_creative_prompt(prompt)


def analyze_hook(hook, topic=""):
    hook = str(hook or "").strip()[:8000]
    topic = str(topic or "").strip()[:4000]
    if not hook:
        return None, "⚠️ Please paste or type a hook to analyze first."

    prompt = f"""
Act as a ruthless, world-class YouTube & Short-Form Retention Editor.
Diagnose this opening hook:

TOPIC: {topic or 'General Creator Video'}
HOOK TO ANALYZE: "{hook}"

Provide a structured 10/10 diagnostic:

📊 **RETENTION SCORECARD**
- **Clarity (0-10)**: Does the viewer instantly know what the video is about?
- **Curiosity Gap (0-10)**: Does it open an unanswered question in the viewer's mind?
- **First-3-Seconds Speed (0-10)**: How fast does it get to the tension?

🚨 **THE #1 WEAKNESS (WHY VIEWERS MIGHT SWIPE AWAY)**
Identify the exact word, pacing issue, or missing stake that hurts retention.

🛠️ **3 UPGRADED 10/10 REWRITES**
- **Option A (High Clarity & Authority)**: Direct, sharp, zero fluff.
- **Option B (Maximum Curiosity Loop)**: Forces the brain to stay for the answer.
- **Option C (Bold Contrarian / Pattern Interrupt)**: Challenges viewer expectations immediately.
Include a `[Delivery/Camera cue]` for each rewrite.
"""
    return _execute_creative_prompt(prompt)


def discover_topics(category="general"):
    category = str(category or "general").strip()[:200]
    research, _ = _gemini_research(
        f"Latest trending news, updates, controversies, and viral topics in {category} for YouTube and Reels creators",
        "topic_radar"
    )
    research = research or "Provide evergreen high-performing opportunities in this category."

    prompt = f"""
Turn this live web research into a 10/10 Creator Opportunity Radar.
CATEGORY: {category.upper()}
LIVE RESEARCH BRIEF:
{research}

Provide 6 high-opportunity video ideas right now. For each (#1 to #6):
🔥 **OPPORTUNITY TITLE / TOPIC**
- **Why Now (The Trigger)**: What just happened or why search interest is spiking.
- **Confirmed vs Rumored**: What facts the creator can safely state.
- **Winning Angle**: How to frame the video differently from everyone else.
- **Best Format**: Long-form / Shorts / Both
- **Clickable Title + 3-Word Thumbnail Idea**

End with:
🏆 **TOP 2 BETS TO RECORD TODAY**: Rank the best two ideas by urgency and audience demand.
"""
    return _execute_creative_prompt(prompt)


def generate_packaging_lab(topic, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    if not topic:
        return None, "⚠️ Please enter your video topic in the Working Topic box above."

    research, _ = _gemini_research(topic, "packaging_lab")
    prompt = f"""
Build a 10/10 Video Packaging Decision System where Title + Thumbnail + Spoken Hook work as one unified click-and-retain machine.

TOPIC: {topic}
CREATOR VOICE: {brand_voice or 'Confident creator voice'}
VERIFIED RESEARCH:
{research or 'Use core topic knowledge.'}

Create 3 complete, distinct packaging systems:

📦 **PACKAGE 1 — HIGH CLARITY & BROAD APPEAL**
- **TITLE**:
- **THUMBNAIL VISUAL & EMOTION**:
- **THUMBNAIL TEXT (2-4 words, never repeating the title)**:
- **FIRST 5-SECOND SPOKEN HOOK** (pays off the click immediately):
- **PSYCHOLOGY**: Why this combination earns the click and keeps the viewer.

📦 **PACKAGE 2 — INTENSE CURIOSITY / OPEN LOOP**
- **TITLE**:
- **THUMBNAIL VISUAL & EMOTION**:
- **THUMBNAIL TEXT (2-4 words)**:
- **FIRST 5-SECOND SPOKEN HOOK**:
- **PSYCHOLOGY**:

📦 **PACKAGE 3 — CONTRARIAN / BOLD STAKES**
- **TITLE**:
- **THUMBNAIL VISUAL & EMOTION**:
- **THUMBNAIL TEXT (2-4 words)**:
- **FIRST 5-SECOND SPOKEN HOOK**:
- **PSYCHOLOGY**:

🧠 **PACKAGING DIAGNOSTIC**
- **Golden Rule Check**: What the thumbnail must show visually so the title doesn't have to say it.
- **Recommended Launch Package**: Which package to publish with first.
"""
    return _execute_creative_prompt(prompt)


def generate_ab_packs(topic, brand_voice=""):
    topic = str(topic or "").strip()[:MAX_TOPIC_CHARS]
    if not topic:
        return None, "⚠️ Please enter your video topic in the Working Topic box above."

    research, _ = _gemini_research(topic, "ab_pack")
    prompt = f"""
Create 3 genuinely different A/B/C Test Angles for the same video so the creator can test which viewer psychology wins the highest CTR and retention.

TOPIC: {topic}
VOICE: {brand_voice or 'Natural creator voice'}
VERIFIED RESEARCH:
{research or 'Standard context.'}

🅰️ **TEST ANGLE A — SEARCH & AUTHORITY (Direct Value)**
- **Title**:
- **Thumbnail Concept & 3-Word Text**:
- **Opening Hook**:
- **Target Viewer Mindset**:

🅱️ **TEST ANGLE B — CURIOSITY GAP (Mystery / Unanswered Question)**
- **Title**:
- **Thumbnail Concept & 3-Word Text**:
- **Opening Hook**:
- **Target Viewer Mindset**:

🆎 **TEST ANGLE C — FEAR / WARNING / CONTRARIAN (High Emotion)**
- **Title**:
- **Thumbnail Concept & 3-Word Text**:
- **Opening Hook**:
- **Target Viewer Mindset**:

🏁 **A/B TESTING PLAYBOOK**
- Which angle to launch with in the first 2 hours.
- What CTR / First-30s retention signal tells you to swap to Backup B.
"""
    return _execute_creative_prompt(prompt)


def performance_coach(topic, metrics):
    topic = str(topic or "").strip()[:4000]
    metrics = str(metrics or "").strip()[:10000]
    if not metrics:
        return None, "⚠️ Please paste your video metrics (Views, CTR, Retention, AVD) first."

    prompt = f"""
Act as HookSpike's Senior YouTube & Short-Form Analytics Strategist.
Diagnose these real creator metrics with surgical precision:

VIDEO TOPIC: {topic or 'Not specified'}
SUPPLIED METRICS:
{metrics}

Return a 10/10 Actionable Diagnosis:

📊 **1. WHAT THE NUMBERS ACTUALLY SAY**
Plain-English translation of how these metrics interact (e.g., high CTR + low AVD = packaging overpromised or slow intro).

🎯 **2. THE #1 BOTTLENECK**
Identify whether the primary problem is **Packaging (Impressions -> Click)**, **Hook (First 30s drop-off)**, or **Body Pacing (Mid-video bleed)**.

🧲 **3. PACKAGING AUDIT (CTR)**
Specific diagnosis and how to adjust the title/thumbnail right now if CTR is underperforming.

🎬 **4. RETENTION AUDIT (AVD & 30s Hold)**
What likely happened in the opening 30 seconds and middle segments.

🚨 **5. TOP 3 PRIORITIZED FIXES (DO THIS NEXT)**
1. (Immediate action for this video)
2. (Structural change for the next upload)
3. (Experiment to run)

⚠️ **6. WHAT NOT TO CHANGE**
One thing that is working or normal that the creator should NOT panic-edit.
"""
    return _execute_creative_prompt(prompt)


def generate_content_plan(niche, goal="growth"):
    niche = str(niche or "").strip()[:3000]
    goal = str(goal or "growth").strip()[:1000]
    if not niche:
        return None, "⚠️ Please enter your niche or content area first."

    research, _ = _gemini_research(f"Current trends and high-performing topics in {niche}", "content_planner")
    prompt = f"""
Build a realistic, high-momentum 7-Day Creator Operating Plan.

NICHE: {niche}
PRIMARY GOAL: {goal.upper()}
CURRENT NICHE INTELLIGENCE:
{research or 'Use proven niche pillars.'}

For **DAY 1 through DAY 7**, provide:
- **DAY & FORMAT**: (e.g., Long-Form Pillar / High-Retention Short / Community Post)
- **VIDEO IDEA**: Specific, timely topic
- **PSYCHOLOGICAL ANGLE**: Why the audience cares
- **TITLE & 3-WORD THUMBNAIL DIRECTION**:
- **OPENING HOOK (1 Sentence)**:
- **EFFORT LEVEL**: Low / Medium / High

End with:
♻️ **THE WEEKLY FLYWHEEL**: How to turn the biggest video of this week into 3 extra pieces of short-form content in 20 minutes.
"""
    return _execute_creative_prompt(prompt)


def repurpose_creator_content(content, source_platform="YouTube", target_platform="Instagram Reels"):
    content = str(content or "").strip()[:MAX_CREATIVE_CHARS]
    if not content:
        return None, "⚠️ Please paste your script, summary, or post to repurpose first."

    prompt = f"""
Transform and repurpose this content from **{source_platform}** into a 10/10 platform-native asset for **{target_platform}**.

SOURCE CONTENT:
{content}

Return ONLY:

🎯 **1. PLATFORM RE-ANGLE**
How we are shifting the pacing and hook style specifically for {target_platform}'s algorithm and viewer behavior.

🪝 **2. 3 PLATFORM-NATIVE HOOK OPTIONS**
With `[Visual/Text-on-screen cues]` for the first 2 seconds.

🎬 **3. COMPLETE READY-TO-POST SCRIPT / POST**
Formatted with fast cuts, spoken rhythm, and visual cues tailored for {target_platform}.

✂️ **4. EDITING & RETENTION CUES**
3 specific editing notes (captions, B-roll timing, loop transition).

📣 **5. NATIVE CTA**
A natural call-to-action that drives shares, saves, or comments on {target_platform}.
"""
    return _execute_creative_prompt(prompt)


def get_ai_engine_status():
    return {
        "gemini_configured": bool(_get_gemini_keys()),
        "openai_configured": bool(_get_openai_keys()),
        "gemini_primary_model": GEMINI_MODELS[0],
        "openai_primary_model": OPENAI_MODELS[0],
        "engine_version": "3.0-agency",
    }
