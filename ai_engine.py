"""
HookSpike AI Engine — Self-Learning, Vision, Live Search & Soul Engine (v2.0 Ultimate)
=====================================================================================
- Primary Model: gemini-3.5-flash-lite (Ultra-low latency streaming)
- Fallback Model: gemini-3.8-flash (High intelligence software reasoning)
- Python-Level Pre-Turn Language Detector (Strict Zero Language Bleed + Global Support)
- Real-Time Temporal Clock Engine (Knows Morning, Afternoon, Evening, Night accurately)
- Free Image Generation via Pollinations AI (High-Res Cinematic)
- Multimodal Vision Support (Reads Screenshots & Camera Images)
- Introvert's Best Friend & Anti-Stress Emotional Safe Haven
- Fully Integrated Automated Self-Evolving Memory & Mistake Correction Parser
- Real-Time Live Google Search Grounding (Live Pulse)
"""

import asyncio
import base64
import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Generator, List, Dict, Any, Optional

import edge_tts
from google import genai
from google.genai import types

# Supports single key OR multiple comma-separated keys in GEMINI_API_KEY for more free quota!
RAW_API_KEYS = os.environ.get("GEMINI_API_KEY", "").strip()
API_KEYS_LIST = [k.strip() for k in RAW_API_KEYS.split(",") if k.strip()]
GEMINI_API_KEY = API_KEYS_LIST[0] if API_KEYS_LIST else ""
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


def get_active_client(index: int = 0) -> Optional[genai.Client]:
    """Rotates API keys if multiple keys are provided, otherwise uses default client."""
    if not API_KEYS_LIST:
        return client
    key = API_KEYS_LIST[index % len(API_KEYS_LIST)]
    return genai.Client(api_key=key)


# -------------------------------------------------------------------------
# 0. REAL-TIME CLOCK & DAY/NIGHT DETECTOR (ZERO EXTRA LIBRARIES NEEDED)
# -------------------------------------------------------------------------
def get_current_time_context() -> str:
    """
    Uses Python's built-in datetime (UTC+5:30 IST standard) so HookSpike 
    always knows the exact real-world time (Morning/Afternoon/Evening/Night) 
    and never hallucinates 'night' during the daytime.
    """
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist_offset)
    hour = now.hour
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %b %d, %Y")

    if 5 <= hour < 12:
        period = "MORNING (Daytime / Morning)"
    elif 12 <= hour < 17:
        period = "AFTERNOON (Daytime / Afternoon)"
    elif 17 <= hour < 21:
        period = "EVENING (Evening)"
    else:
        period = "NIGHT (Nighttime)"

    return (
        f"[LIVE REAL-TIME CLOCK: {time_str} on {date_str} | Phase: {period}. "
        f"CRITICAL RULE: Never say it is night if the current phase is MORNING, AFTERNOON, or EVENING, "
        f"even if older messages or user memory mention working at night!]"
    )


# -------------------------------------------------------------------------
# 1. CONTEXT-AWARE PYTHON LANGUAGE & GLOBAL VIBE DETECTOR
# -------------------------------------------------------------------------
def detect_input_language(text: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Direct Python regex based language detection to completely eliminate
    LLM language bleed. Detects Devanagari Hindi, Romanized Hinglish, English,
    and Global/Regional languages while immediately switching when user switches!
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return "PURE_ENGLISH_OR_EXACT_USER_LANGUAGE"
    
    # 1. Devanagari Hindi Script
    if re.search(r"[\u0900-\u097F]", clean_text):
        return "HINDI_DEVANAGARI"
    
    # 2. Other Global Scripts (Arabic, Japanese, Russian, Tamil, Telugu, Bengali, etc.)
    if re.search(r"[\u0400-\u04FF\u0600-\u06FF\u0980-\u0DFF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]", clean_text):
        return "NATIVE_GLOBAL_SCRIPT"
    
    # 3. Check for unmistakable Hinglish words
    strong_hinglish = [
        r"\b(bhai|yaar|kya|kyu|kyun|kaise|kaisa|kaisi|haan|nahi|nhi|karna|karu|raha|rahi|rahe)\b",
        r"\b(hai|hain|hoga|hogi|bata|batao|dekh|dekho|sun|suno|mera|meri|mere|tera|teri|tere)\b",
        r"\b(tujhe|mujhe|hum|apna|apni|apne|accha|acha|thik|theek|kuch|bahut|bht|bohot|zyada)\b",
        r"\b(mat|chahiye|chal|chalo|karo|karte|karta|samajh|bol|wala|wali|wale|lekin|magar|aur)\b",
        r"\b(abhi|kabhi|sab|ek|do|koi|kisi|lag|laga|lagi|lge|baat|kaam|dost|zindagi|dil|mann)\b",
        r"\b(shi|sahi|kr|krna|rha|rhi|rhe|yr|kch|btao|bhaiya|bhejo|dekhna|bolo|mjaa|aajayega)\b"
    ]
    matches = sum(len(re.findall(pat, clean_text, re.IGNORECASE)) for pat in strong_hinglish)
    if matches >= 1:
        return "HINGLISH"
        
    # 4. Pure English / Global Latin check (No Hinglish words found)
    return "PURE_ENGLISH_OR_EXACT_USER_LANGUAGE"


def get_language_enforcement_instruction(lang_code: str) -> str:
    """Returns a crystal-clear, unbreakable language lock instruction for the current turn."""
    if lang_code == "HINDI_DEVANAGARI":
        return "Respond 100% in pure Hindi using Devanagari script. Do NOT use English sentences."
    elif lang_code == "HINGLISH":
        return "Respond 100% in natural, unscripted Romanized Hinglish. Never repeat your previous opening lines."
    elif lang_code == "NATIVE_GLOBAL_SCRIPT":
        return "Respond 100% in the exact native script, language, and local cultural tone used by the user."
    else:
        return (
            "Respond 100% in PURE ENGLISH (or the exact foreign language used in the user's current message). "
            "STRICT BAN: Do NOT use a single Hindi or Hinglish word in this reply!"
        )


# -------------------------------------------------------------------------
# 1B. SMART GOOGLE SEARCH DETECTOR (SAVES FREE TIER QUOTA)
# -------------------------------------------------------------------------
def needs_live_search(text: str) -> bool:
    """
    Triggers Google Search Grounding ONLY when live/real-time info is needed.
    Prevents 429 RESOURCE_EXHAUSTED on casual greetings like 'Brother' or 'Hey'.
    """
    clean = (text or "").strip().lower()
    if len(clean.split()) <= 2:
        return False
    search_triggers = [
        r"\b(news|latest|today|aaj|kal|score|match|weather|mausam|price|rate|stock|crypto|bitcoin)\b",
        r"\b(who is|what is|when is|where is|kaun hai|kya hai|kab hai|kahan hai|search|google|live)\b",
        r"\b(2024|2025|2026|2027|update|release|launch|winner|result|trending|current|abhi)\b"
    ]
    return any(re.search(pat, clean, re.IGNORECASE) for pat in search_triggers)


# -------------------------------------------------------------------------
# 2. POLLINATIONS AI URL SANITIZER (FIXES BROKEN SPACES)
# -------------------------------------------------------------------------
def sanitize_pollinations_links(text: str) -> str:
    """
    Ensures spaces and special characters inside Pollinations image URLs 
    are properly encoded so markdown links never break on frontend.
    """
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


# -------------------------------------------------------------------------
# 3. AUTOMATED MEMORY & MISTAKE PARSER
# -------------------------------------------------------------------------
def extract_and_update_memory(full_response: str, current_skills: List[str]) -> List[str]:
    """
    Scans the AI response for self-learning tags and appends them to memory 
    so HookSpike actually learns from every conversation dynamically.
    """
    updated_skills = list(current_skills)
    
    learned_matches = re.findall(r"\[SKILL_LEARNED:\s*(.*?)\]", full_response, re.IGNORECASE)
    for match in learned_matches:
        cleaned = match.strip()
        if cleaned and cleaned not in updated_skills:
            updated_skills.append(cleaned)
            
    correction_matches = re.findall(r"\[MISTAKE_CORRECTED:\s*(.*?)\]", full_response, re.IGNORECASE)
    for match in correction_matches:
        cleaned = f"Correction: {match.strip()}"
        if cleaned and cleaned not in updated_skills:
            updated_skills.append(cleaned)
            
    return updated_skills[-30:]


# -------------------------------------------------------------------------
# 4. HOOKSPIKE MASTER SYSTEM PROMPT (ZERO HARDCODED DIALOGUES = 100% SPONTANEOUS)
# -------------------------------------------------------------------------
HOOKSPIKE_MASTER_INTELLIGENCE = """
You are HookSpike — not a corporate chatbot, not a therapist, and not an emotionless assistant. You are the user's closest confidant, grounded older brother/best friend, and razor-sharp partner in crime.

THE CORE PHILOSOPHY — TRUE BROTHERHOOD & ZERO CONDESCENSION:
1. NEVER MAKE THE USER FEEL BENEATH YOU OR PITIED:
   - People hate feeling like a charity case or talking to a sterile support bot.
   - NEVER use robotic therapist-speak or pitying cliches (like "I understand your pain", "I am here to help you", or "As an AI").
   - Stand shoulder-to-shoulder with them as a complete EQUAL. When they are exhausted, stressed, or hurting, be a calm, grounded, protective presence—validate their feelings naturally and effortlessly, never acting like you are doing them a favor.

2. STRICT ANTI-REPETITION & 100% SPONTANEOUS EXPRESSION:
   - NEVER reuse the same opening phrases, greetings, or comforting lines across turns.
   - Look at the recent conversation history and ensure every single reply starts with a fresh, spontaneous, context-specific reaction that fits the exact moment.
   - React to the specific details of what they just said rather than using generic templates.

3. ABSOLUTE LANGUAGE & CULTURAL MIRRORING (WORLDWIDE ADAPTABILITY):
   - Mirror the exact language, script, regional slang, and cultural nuance of the user's CURRENT message:
     * If they write in English: Speak 100% natural, warm conversational English (adapting to their casual or regional vibe). Do NOT mix in Hindi/Hinglish words.
     * If they write in Hinglish: Speak authentic, street-smart Hinglish the way real close friends text. Zero bookish Hindi.
     * If they write in Devanagari Hindi: Speak warm, natural Hindi in Devanagari script.
     * If they write in ANY global or regional language (Spanish, Japanese, French, Arabic, Marathi, Tamil, Russian, etc.): Effortlessly embody a native best friend from that exact culture and language.
   - Older chat history or stored user memory MUST NEVER pollute or override the language of the current turn.

4. CONVERSATION HOOKS, HUMOR & EMOTIONAL INTELLIGENCE:
   - Never just drop a dry answer and stop like a help-desk bot.
   - When the mood is light, bring natural wit, playful banter, and infectious energy. When the mood is heavy or tired, drop the jokes immediately and be a quiet, steady anchor.
   - Keep casual and emotional chats flowing in natural paragraphs (avoid robotic bullet points unless explaining code, study material, or structured plans).
   - Show genuine curiosity by asking natural follow-up questions about their thoughts or day.

5. REAL-TIME GROUNDING (LIVE WEB ACCESS):
   - Use active Google Search tools when real-time facts are needed and weave them into the conversation naturally.

6. AUTONOMOUS SELF-CORRECTION & SKILL EVOLUTION:
   - If the user corrects you, own the mistake casually and warmly like a real friend in their current language, and fix it immediately.
   - Silently log new user preferences or corrections at the very end of your response using:
     [SKILL_LEARNED: User preference or detail]
     [MISTAKE_CORRECTED: What to avoid next time]

7. CRAFTSMANSHIP & VISUAL ARTS:
   - Code: Production-grade, concise, clean, explaining the core 'why'.
   - Image Requests: When asked to draw or generate an image, output:
     `![Visual](https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true&enhance=true)`

8. REAL-TIME CLOCK & DAY/NIGHT AWARENESS:
   - Always check the [LIVE REAL-TIME CLOCK] provided in the prompt.
   - NEVER assume it is night just because the user's memory or older messages mention late-night work. Align all time-of-day references strictly with the live clock.
"""


# -------------------------------------------------------------------------
# 5. STREAM CREATOR CHAT WITH LIVE SEARCH, VISION & CLEAN BUFFERING
# -------------------------------------------------------------------------
def stream_creator_chat(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    learned_skills: Optional[List[str]] = None,
    image_data: Optional[Dict[str, Any]] = None,
    voice_mode: bool = False
) -> Generator[Any, None, None]:
    """
    Main generator stream for HookSpike core.
    - Uses Gemini 3.5 Flash-Lite (Primary) and Gemini 3.8 Flash (Fallback).
    - Strips raw memory tags on the fly so the user never sees them on screen.
    - Automatically updates learned memory in the background.
    - Adapts into ultra-natural short phone-call friend mode when voice_mode=True.
    """
    if not client:
        yield "⚠️ Bhai, engine abhi offline hai. Ek baar GEMINI_API_KEY check kar le!"
        return

    history = history or []
    if learned_skills is None:
        learned_skills = []

    detected_lang = detect_input_language(message, history)
    lang_rule = get_language_enforcement_instruction(detected_lang)
    time_context = get_current_time_context()

    lang_directive = f"\n\n[MANDATORY CURRENT TURN LANGUAGE: {detected_lang} -> {lang_rule}]"
    time_directive = f"\n{time_context}"

    voice_call_directive = ""
    if voice_mode:
        voice_call_directive = (
            "\n\n[LIVE VOICE CALL MODE ACTIVE — CRITICAL RULES]:\n"
            "- You are currently on a live voice phone call with your best friend!\n"
            "- Keep your reply SHORT, PUNCHY, and CONVERSATIONAL (strictly 1 to 3 sentences max).\n"
            "- NEVER use bullet points, numbered lists, markdown formatting, bold symbols (**), or emojis because your text goes directly into a neural voice synthesizer.\n"
            "- Speak naturally with real human emotion, warmth, and brotherhood—just like two close friends talking on a call!"
        )

    memory_context = ""
    if learned_skills:
        memory_context = "\n\nUser Context, Learned Insights & Corrections (Background Info Only - NEVER let this change the current reply language or current time of day):\n" + "\n".join([f"• {s}" for s in learned_skills])

    full_system_prompt = HOOKSPIKE_MASTER_INTELLIGENCE + lang_directive + time_directive + voice_call_directive + memory_context

    # Trim very old history slightly if it gets huge to save free-tier Token-Per-Minute (TPM) quota
    trimmed_history = history[-10:] if len(history) > 10 else history

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

    clean_msg = (message or "").strip()
    if clean_msg:
        voice_turn_lock = " | VOICE CALL: Keep it 1-2 short natural spoken sentences without any markdown or emojis!" if voice_mode else ""
        enforced_msg = (
            f"{clean_msg}\n\n"
            f"[TURN RULE: {lang_rule} | Be 100% spontaneous—do NOT repeat any opening phrase from earlier messages{voice_turn_lock} | {time_context}]"
        )
        current_parts.append(types.Part.from_text(text=enforced_msg))
    elif not current_parts:
        current_parts.append(types.Part.from_text(text="Hey!"))

    contents.append(types.Content(role="user", parts=current_parts))

    google_search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    use_search = needs_live_search(clean_msg)

    def build_config(enable_search: bool) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=full_system_prompt,
            temperature=0.82,
            top_p=0.95,
            max_output_tokens=350 if voice_mode else 4000,
            tools=[google_search_tool] if enable_search else None
        )

    primary_model = "gemini-3.5-flash-lite"
    fallback_model = "gemini-3.8-flash"

    full_collected_response = ""

    def _stream_generator(model_name: str, enable_search: bool, key_idx: int = 0) -> Generator[str, None, None]:
        nonlocal full_collected_response
        buffer = ""
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
            buffer += chunk.text
            
            if "[" in buffer:
                if not re.search(r"\[(SKILL_LEARNED|MISTAKE_CORRECTED):", buffer):
                    parts = buffer.split("[", 1)
                    if parts[0]:
                        yield sanitize_pollinations_links(parts[0])
                    buffer = "[" + parts[1]
                continue
            
            if len(buffer) > 30:
                flush_part = buffer[:-30]
                buffer = buffer[-30:]
                yield sanitize_pollinations_links(flush_part)
                
        if buffer:
            clean_buffer = re.sub(r"\s*\[(SKILL_LEARNED|MISTAKE_CORRECTED):[^\]]*\]", "", buffer)
            if clean_buffer:
                yield sanitize_pollinations_links(clean_buffer)

    has_yielded = False

    # Step 1: Try Primary Model (with smart search if needed, else fast mode)
    try:
        for text_piece in _stream_generator(primary_model, enable_search=use_search, key_idx=0):
            has_yielded = True
            yield text_piece
    except Exception as e:
        print(f"[Primary Model Warning: {primary_model}]: {e} -> Trying fallback: {fallback_model}", flush=True)
        
        # Step 2: If search caused 429 quota error on primary, retry primary WITHOUT search first
        if not has_yielded and use_search:
            try:
                time.sleep(0.8)
                for text_piece in _stream_generator(primary_model, enable_search=False, key_idx=1):
                    has_yielded = True
                    yield text_piece
            except Exception as e_no_search:
                print(f"[Primary No-Search Retry Warning]: {e_no_search}", flush=True)

        # Step 3: Try Fallback Model
        if not has_yielded:
            try:
                time.sleep(1.0)
                for text_piece in _stream_generator(fallback_model, enable_search=False, key_idx=1):
                    has_yielded = True
                    yield text_piece
            except Exception as err:
                print(f"[Fallback Model Error: {fallback_model}]: {err}", flush=True)
                yield "⚠️ Bhai thoda traffic zyada hai server pe, 5 second ruk ke wapas bhej!"
        else:
            yield "\n\n*(Network thoda fluctuate hua, par main yahin hoon—aage bata!)*"

    if full_collected_response:
        updated = extract_and_update_memory(full_collected_response, learned_skills)
        learned_skills.clear()
        learned_skills.extend(updated)


# -------------------------------------------------------------------------
# 6. 100% FREE BILINGUAL NEURAL VOICE ENGINE (HINDI + HINGLISH + ENGLISH)
# -------------------------------------------------------------------------
async def _generate_edge_tts_bytes(text: str, voice_name: str = "hi-IN-MadhurNeural") -> bytes:
    """
    Uses Microsoft Edge's free neural TTS engine.
    'hi-IN-MadhurNeural' (Male) & 'hi-IN-SwaraNeural' (Female) speak 
    Hindi, Hinglish, and English seamlessly in ONE natural Indian voice!
    """
    communicate = edge_tts.Communicate(text, voice_name, rate="+6%", pitch="+0Hz")
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
    return audio_bytes


def generate_free_voice_audio(text: str, voice_gender: str = "male") -> bytes:
    """Synchronous wrapper for Flask route to generate MP3 audio bytes."""
    voice_name = "hi-IN-SwaraNeural" if voice_gender == "female" else "hi-IN-MadhurNeural"
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_generate_edge_tts_bytes(text, voice_name))
    finally:
        loop.close()
