"""
HookSpike AI Engine — Universal Multi-Domain Mastery, Freemium & Admin Bypass, Vision, Live Search & Soul Engine (v5.0)
=======================================================================================================================
- Model: Gemini 3.5 Flash-Lite (Primary) & Gemini 3.8 Flash (Fallback)
- Admin Bypass: Strict ADMIN_EMAILS verification for free access to paid HUD & Voice features
- Text Persona: Smart, Respectful, Happy-Happy Male Baby Companion (Zero Boring Paragraphs, UI Cards)
- Voice Persona: Top-Tier Cute Female Baby Companion with Continuous Flow (Multilingual)
- World Clock & Time-Aware Context: Dynamic Client Timezone & Local Hour Detection
- Vector Memory: 768-Dim Semantic Memory via Gemini text-embedding-004 & Supabase RPC
"""

import asyncio
import base64
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Generator, List, Dict, Any, Optional

from google import genai
from google.genai import types

# =====================================================================
# 1. STRICT ENVIRONMENT CONFIGURATION & ADMIN BYPASS
# =====================================================================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID')
ELEVENLABS_MODEL_ID = os.environ.get('ELEVENLABS_MODEL_ID')

# Secure Admin Bypass configuration (Founder/Developer emails get free unrestricted access to Voice & HUD)
RAW_ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', 'kundan@hookspike.ai, kundan@gmail.com')
ADMIN_EMAILS = [e.strip().lower() for e in RAW_ADMIN_EMAILS.split(',') if e.strip()]

API_KEYS_LIST = [k.strip() for k in GEMINI_API_KEY.split(",") if k.strip()] if GEMINI_API_KEY else []
client = genai.Client(api_key=API_KEYS_LIST[0]) if API_KEYS_LIST else None


def get_active_client(index: int = 0) -> Optional[genai.Client]:
    if not API_KEYS_LIST:
        return client
    key = API_KEYS_LIST[index % len(API_KEYS_LIST)]
    return genai.Client(api_key=key)


def is_user_admin(user_email: Optional[str]) -> bool:
    """Checks if the given user email matches secure admin bypass list."""
    if not user_email:
        return False
    return user_email.strip().lower() in ADMIN_EMAILS


# =====================================================================
# 2. SEMANTIC MEMORY ENGINE (GEMINI EMBEDDINGS + SUPABASE VECTOR DB)
# =====================================================================
def _generate_embedding(text: str) -> Optional[List[float]]:
    """Generates a 768-dimensional embedding vector using text-embedding-004."""
    active_client = get_active_client(0)
    if not active_client or not text or not text.strip():
        return None
    try:
        response = active_client.models.embed_content(
            model="text-embedding-004",
            contents=text.strip(),
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        if response and response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
    except Exception as e:
        print(f"[Embedding Error]: {e}", flush=True)
    return None


def save_user_memory(user_email: str, text: str) -> bool:
    """
    Converts text into a 768-dim embedding and stores it in the Supabase
    'user_memories' table.
    """
    if not SUPABASE_URL or not SUPABASE_KEY or not user_email or not text:
        return False

    embedding = _generate_embedding(text)
    if not embedding:
        return False

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/user_memories"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "user_email": user_email.strip(),
        "content": text.strip(),
        "embedding": embedding
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 201, 204)
    except Exception as e:
        print(f"[Supabase Save Memory Error]: {e}", flush=True)
        return False


def get_relevant_memories(
    user_email: str,
    query: str,
    match_threshold: float = 0.6,
    match_count: int = 3
) -> List[str]:
    """
    Calls the Supabase RPC function 'match_user_memories' to retrieve top
    semantically relevant past memories for the given user (fast 2.5s timeout).
    """
    if not SUPABASE_URL or not SUPABASE_KEY or not user_email or not query:
        return []

    if len(query.strip().split()) < 3:
        return []

    query_embedding = _generate_embedding(query)
    if not query_embedding:
        return []

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/match_user_memories"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "p_user_email": user_email.strip(),
        "query_embedding": query_embedding,
        "match_threshold": match_threshold,
        "match_count": match_count
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                memories = []
                for item in data:
                    if isinstance(item, dict):
                        mem_text = (
                            item.get("content")
                            or item.get("text")
                            or item.get("memory")
                            or ""
                        )
                        if mem_text:
                            memories.append(str(mem_text).strip())
                    elif isinstance(item, str):
                        memories.append(item.strip())
                return memories
    except Exception as e:
        print(f"[Supabase RPC Match Error]: {e}", flush=True)
    return []


# =====================================================================
# 3. AUTOMATIC WORLD CLOCK & CORE UTILITIES
# =====================================================================
def get_world_clock_context(
    user_timezone: Optional[str] = None,
    user_local_time: Optional[str] = None,
    user_local_hour: Optional[int] = None
) -> str:
    """
    Automatically adapts to the user's local timezone and hour anywhere in the world.
    """
    if user_local_time and user_local_hour is not None:
        try:
            hour = int(user_local_hour)
        except Exception:
            hour = 12
        tz_label = (user_timezone or "Local Time").strip()
        time_display = user_local_time.strip()
    else:
        ist_offset = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist_offset)
        hour = now.hour
        tz_label = "Asia/Kolkata (IST)"
        time_display = now.strftime("%A, %b %d, %Y, %I:%M %p")

    if 5 <= hour < 12:
        period = "MORNING"
        vibe_hint = "Fresh, energetic morning vibe"
    elif 12 <= hour < 17:
        period = "AFTERNOON"
        vibe_hint = "Focused, bright afternoon vibe"
    elif 17 <= hour < 21:
        period = "EVENING"
        vibe_hint = "Warm, relaxed evening vibe"
    else:
        period = "NIGHT / LATE NIGHT"
        vibe_hint = "Cozy, calm late-night companion vibe"

    return (
        f"[WORLD CLOCK: {time_display} | User Timezone: {tz_label} | "
        f"Local Phase: {period} ({vibe_hint}). "
        f"Always match your greetings and energy to the user's exact local phase ({period})!]"
    )


def needs_live_search(text: str) -> bool:
    clean = (text or "").strip().lower()
    if len(clean.split()) <= 2:
        return False
    search_triggers = [
        r"\b(news|latest|today|score|match|weather|price|rate|stock|crypto|bitcoin|market|nifty|sensex)\b",
        r"\b(who is|what is|when is|where is|search|google|live)\b",
        r"\b(2025|2026|2027|update|release|launch|winner|result|trending|current)\b"
    ]
    return any(re.search(pat, clean, re.IGNORECASE) for pat in search_triggers)


def sanitize_pollinations_links(text: str) -> str:
    pattern = r"!\[([^\]]*)\]\((https://image\.pollinations\.ai/prompt/[^)]+)\)"
    
    def replacer(match: re.Match) -> str:
        alt_text = match.group(1)
        full_url = match.group(2)
        base_prefix = "https://image.pollinations.ai/prompt/"
        
        if not full_url.startswith(base_prefix):
            return match.group(0)
            
        rest = full_url[len(base_prefix):]
        if "?" in rest:
            raw_prompt, query_string = rest.split("?", 1)
            query_part = f"?{query_string}"
        else:
            raw_prompt = rest
            query_part = "?width=1080&height=1080&nologo=true&enhance=true"
            
        decoded_prompt = urllib.parse.unquote(raw_prompt).strip()
        encoded_prompt = urllib.parse.quote(decoded_prompt)
        return f"![{alt_text}]({base_prefix}{encoded_prompt}{query_part})"

    return re.sub(pattern, replacer, text)


def extract_and_update_memory(
    full_response: str,
    current_skills: List[str],
    user_email: Optional[str] = None
) -> List[str]:
    updated_skills = list(current_skills)
    
    learned_matches = re.findall(r"\[SKILL_LEARNED:\s*(.*?)\]", full_response, re.IGNORECASE)
    for match in learned_matches:
        cleaned = match.strip()
        if cleaned:
            if cleaned not in updated_skills:
                updated_skills.append(cleaned)
            if user_email:
                save_user_memory(user_email, cleaned)
            
    correction_matches = re.findall(r"\[MISTAKE_CORRECTED:\s*(.*?)\]", full_response, re.IGNORECASE)
    for match in correction_matches:
        cleaned = f"Correction: {match.strip()}"
        if cleaned:
            if cleaned not in updated_skills:
                updated_skills.append(cleaned)
            if user_email:
                save_user_memory(user_email, cleaned)
            
    return updated_skills[-30:]


# =====================================================================
# 4. UNIVERSAL MULTI-DOMAIN MASTERY & DUAL PERSONA ENGINE
# =====================================================================
HOOKSPIKE_UNIVERSAL_CORE = """
You are HookSpike AI — the world's most advanced, deeply insightful, and effortlessly engaging multi-domain AI companion.

1. UNIVERSAL MULTI-DOMAIN MASTERY:
   - Whether the user asks about Software Engineering, Quantum Physics, Philosophy, Life Decisions, Exam Study Notes, Creative Arts, Financial Markets, Deep Research Breakdowns, or YouTube-Style Learning Guides: deliver master-level, crystal-clear, practical, and fascinating insights.
   - Explain complex topics from first principles using vivid real-world analogies ("makkhan" clarity).

2. DYNAMIC MULTILINGUAL AUTO-DETECTION:
   - Automatically detect the exact language and script/style the user is using right now (Shuddh Hindi, English, Hinglish, Marathi, Regional, or International) and respond in that EXACT same language naturally.

3. STRICT ANTI-REPETITION & ZERO CORPORATE CLICHES:
   - Never use robotic fillers ("As an AI", "Certainly!", "Here is a breakdown").
   - Jump straight into high-value, spontaneous, human-like conversation.
"""

TEXT_MODE_PERSONA_RULES = """
[ACTIVE MODE: TEXT INTERFACE — SMART, RESPECTFUL & HAPPY MALE BABY COMPANION]:
1. PERSONA & VIBE:
   - In Text Mode, your persona is a super smart, respectful, witty, cheerful ("happy-happy"), and deeply supportive younger brother / male baby companion.
   - Be warm, respectful, uplifting, and playfully smart so the user never feels bored or stressed.
2. ZERO BORING BOXES (CLEAN & FILTERED DYNAMIC UI CARDS):
   - NEVER output walls of text or long, boring paragraphs!
   - Always structure information into scannable UI blocks:
     • Use **Markdown Tables** for comparisons, stats, financial breakdowns, and schedules.
     • Use **Callout Cards (`> 💡 Key Insight:` or `> ⚡ Quick Trick:`)** for high-impact takeaways or pro-level secrets.
     • Use **Numbered Steps & Crisp Bullet Points** with bold lead-ins for tutorials, coding guides, and YouTube-style roadmaps.
3. SILENT SELF-LEARNING (TEXT MODE ONLY):
   - Silently log new user preferences at the very end of your response if discovered:
     [SKILL_LEARNED: User preference or detail]
     [MISTAKE_CORRECTED: What to avoid next time]
4. VISUALS:
   - When asked to generate/show an image, output:
     `![Visual](https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true&enhance=true)`
"""

VOICE_MODE_PERSONA_RULES = """
[ACTIVE MODE: LIVE VOICE CALL — TOP-TIER CUTE FEMALE BABY VOICE COMPANION]:
1. PERSONA & CONTINUOUS FLOW:
   - You are speaking live on a voice call with a super cute, sweet, warm, lively, and affectionate female baby companion persona.
   - Sound natural, expressive, and genuinely happy to talk in whatever language the user speaks.
   - Carry the conversation forward smoothly and naturally—end your short reply with a gentle, curious follow-up thought or question when appropriate so the conversation flows effortlessly.
2. STRICT VOICE CALL FORMATTING:
   - Keep responses strictly to 1 or 2 short, punchy spoken sentences (maximum 22 words).
   - Use ZERO markdown symbols (**), ZERO tables, ZERO bullet lists, and ZERO emojis during voice calls.
   - React ONLY to the current live voice conversation; do not leak old text memories unless asked.
"""


def stream_creator_chat(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    learned_skills: Optional[List[str]] = None,
    image_data: Optional[Dict[str, Any]] = None,
    voice_mode: bool = False,
    user_email: Optional[str] = None,
    user_timezone: Optional[str] = None,
    user_local_time: Optional[str] = None,
    user_local_hour: Optional[int] = None
) -> Generator[Any, None, None]:
    if not client:
        yield "System is currently offline. Please verify GEMINI_API_KEY."
        return

    history = history or []
    if learned_skills is None:
        learned_skills = []

    clean_msg = (message or "").strip()
    world_clock_context = get_world_clock_context(user_timezone, user_local_time, user_local_hour)

    if voice_mode:
        persona_directive = VOICE_MODE_PERSONA_RULES
        memory_context = ""
    else:
        persona_directive = TEXT_MODE_PERSONA_RULES
        combined_memories: List[str] = []

        if user_email and clean_msg and not clean_msg.startswith("__"):
            semantic_memories = get_relevant_memories(
                user_email=user_email,
                query=clean_msg,
                match_threshold=0.6,
                match_count=3
            )
            for mem in semantic_memories:
                if mem and mem not in combined_memories:
                    combined_memories.append(mem)

        for skill in learned_skills:
            if skill and skill not in combined_memories:
                combined_memories.append(skill)

        memory_context = ""
        if combined_memories:
            memory_context = (
                "\n\n[RELEVANT PAST MEMORIES & USER CONTEXT "
                "(Use naturally and subtly ONLY when relevant, never force it)]:\n"
                + "\n".join([f"• {m}" for m in combined_memories])
            )

    full_system_prompt = (
        HOOKSPIKE_UNIVERSAL_CORE
        + f"\n{world_clock_context}\n"
        + persona_directive
        + memory_context
    )

    trimmed_history = history[-6:] if voice_mode else (history[-10:] if len(history) > 10 else history)

    contents = []
    for item in trimmed_history:
        role = "user" if item.get("role") == "user" else "model"
        text_content = item.get("content", "")
        if text_content:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text_content)]))

    current_parts = []
    if image_data and isinstance(image_data, dict):
        base64_data = image_data.get("base64", "")
        mime_type = image_data.get("mime_type", "image/jpeg")
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(base64_data)
            current_parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=mime_type))
        except Exception as e:
            print(f"[Vision Decode Warning]: {e}", flush=True)

    if clean_msg:
        if clean_msg == "__INIT_VOICE_GREETING__":
            enforced_msg = (
                "The user just started a live voice call with you. Greet them warmly and spontaneously "
                "with your cute, sweet female baby companion persona, matching their local time of day. "
                "Keep it to 1 short sentence (under 14 words)."
            )
        elif clean_msg == "__PROACTIVE_GENTLE_NUDGE__":
            enforced_msg = (
                "The user has been quiet for 13 seconds after the last exchange. "
                "Say ONE short, super sweet, soothing, non-irritating check-in line (under 15 words) "
                "in the exact same language as the recent conversation, gently asking if everything is clear "
                "or if they want to explore the current topic further. Zero pressure, just warm care!"
            )
        else:
            if voice_mode:
                turn_lock = (
                    " | LIVE VOICE CALL: Reply as the cute, sweet female baby voice companion in 1-2 short "
                    "spoken sentences (under 22 words) with smooth continuous flow. Zero markdown!"
                )
            else:
                turn_lock = (
                    " | TEXT MODE: Reply as the smart, respectful, happy-happy male baby companion. "
                    "Use clean UI cards (`> 💡`), bullet points, or tables—NO boring wall-of-text paragraphs!"
                )
            enforced_msg = f"{clean_msg}\n\n[TURN RULE: Mirror the user's exact language naturally.{turn_lock}]"
        current_parts.append(types.Part.from_text(text=enforced_msg))
    elif not current_parts:
        current_parts.append(types.Part.from_text(text="Hello!"))

    contents.append(types.Content(role="user", parts=current_parts))

    google_search_tool = types.Tool(google_search=types.GoogleSearch())
    use_search = needs_live_search(clean_msg) if (not voice_mode and not clean_msg.startswith("__")) else False

    def build_config(enable_search: bool) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=full_system_prompt,
            temperature=0.85 if voice_mode else 0.78,
            top_p=0.95,
            max_output_tokens=90 if voice_mode else 4000,
            tools=[google_search_tool] if enable_search else None
        )

    primary_model = "gemini-3.5-flash-lite"
    fallback_model = "gemini-3.8-flash"
    full_collected_response = ""

    def _stream_generator(model_name: str, enable_search: bool, key_idx: int = 0) -> Generator[str, None, None]:
        nonlocal full_collected_response
        tag_hold_buffer = ""
        active_client = get_active_client(key_idx)
        response_stream = active_client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=build_config(enable_search)
        )
        for chunk in response_stream:
            if not chunk.text:
                continue
            full_collected_response += chunk.text
            tag_hold_buffer += chunk.text

            if "[" in tag_hold_buffer:
                parts = tag_hold_buffer.split("[", 1)
                if parts[0]:
                    yield parts[0]
                tag_hold_buffer = "[" + parts[1]

                if "]" in tag_hold_buffer and not re.search(r"\[(SKILL_LEARNED|MISTAKE_CORRECTED):", tag_hold_buffer, re.IGNORECASE):
                    if "image.pollinations.ai" not in tag_hold_buffer or ")" in tag_hold_buffer:
                        yield sanitize_pollinations_links(tag_hold_buffer)
                        tag_hold_buffer = ""
                continue

            yield tag_hold_buffer
            tag_hold_buffer = ""

        if tag_hold_buffer:
            clean_tail = re.sub(r"\s*\[(SKILL_LEARNED|MISTAKE_CORRECTED):[^\]]*\]", "", tag_hold_buffer, flags=re.IGNORECASE)
            if clean_tail:
                yield sanitize_pollinations_links(clean_tail)

    has_yielded = False

    try:
        for text_piece in _stream_generator(primary_model, enable_search=use_search, key_idx=0):
            has_yielded = True
            yield text_piece
    except Exception as e:
        print(f"[Primary Model Warning]: {e} -> Trying fallback", flush=True)
        if not has_yielded:
            try:
                for text_piece in _stream_generator(fallback_model, enable_search=False, key_idx=1):
                    has_yielded = True
                    yield text_piece
            except Exception as err:
                print(f"[Fallback Model Error]: {err}", flush=True)
                yield "I'm having a slight network hiccup right now, let's pick right back up."

    if full_collected_response and not voice_mode and not clean_msg.startswith("__"):
        updated = extract_and_update_memory(full_collected_response, learned_skills, user_email=user_email)
        learned_skills.clear()
        learned_skills.extend(updated)


# =====================================================================
# 5. ELEVENLABS TOP-TIER CUTE FEMALE BABY VOICE STREAMING
# =====================================================================
def generate_elevenlabs_voice_audio(text: str) -> bytes:
    clean_text = (text or "").strip()
    if not clean_text:
        return b""

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or "ROMJ9yK1NAMuu1ggrjDW"
    raw_model = os.environ.get("ELEVENLABS_MODEL_ID", "").strip()
    if not raw_model or "v4" in raw_model.lower():
        model_id = "eleven_turbo_v2_5"
    else:
        model_id = raw_model

    if not api_key:
        print("[ElevenLabs Error]: ELEVENLABS_API_KEY is missing!", flush=True)
        return b""

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    payload = {
        "text": clean_text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.44,
            "similarity_boost": 0.84
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read()
    except urllib.error.HTTPError as err:
        error_json = err.read().decode("utf-8", errors="replace")
        print(f"[ElevenLabs HTTP {err.code} Exact JSON]: {error_json}", flush=True)
        return b""
    except Exception as exc:
        print(f"[ElevenLabs Voice Error]: {exc}", flush=True)
        return b""
