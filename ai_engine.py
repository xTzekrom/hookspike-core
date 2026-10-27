"""
HookSpike AI Engine — Self-Learning, Vision, Live Search & Soul Engine (v2.0 Ultimate)
=====================================================================================
- Primary Model: gemini-3.5-flash-lite (Ultra-low latency streaming)
- Fallback Model: gemini-3.8-flash (High intelligence software reasoning)
- ElevenLabs v4 Turbo Ultra-Low Latency Neural Voice Engine (ROMJ9yK1NAMuu1ggrjDW)
- Pure Conversational English Voice Locking (Zero AI cliches, zero robotic filler)
- Multimodal Vision + Supabase & Local Dynamic Memory + Live Clock
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

RAW_API_KEYS = os.environ.get("GEMINI_API_KEY", "").strip()
API_KEYS_LIST = [k.strip() for k in RAW_API_KEYS.split(",") if k.strip()]
GEMINI_API_KEY = API_KEYS_LIST[0] if API_KEYS_LIST else ""
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = "ROMJ9yK1NAMuu1ggrjDW"
ELEVENLABS_MODEL_ID = "eleven_turbo_v2_5"


def get_active_client(index: int = 0) -> Optional[genai.Client]:
    if not API_KEYS_LIST:
        return client
    key = API_KEYS_LIST[index % len(API_KEYS_LIST)]
    return genai.Client(api_key=key)


def get_current_time_context() -> str:
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
        f"CRITICAL RULE: Never say it is night if the current phase is MORNING, AFTERNOON, or EVENING!]"
    )


def detect_input_language(text: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    clean_text = (text or "").strip()
    if not clean_text:
        return "PURE_ENGLISH_OR_EXACT_USER_LANGUAGE"
    
    if re.search(r"[\u0900-\u097F]", clean_text):
        return "HINDI_DEVANAGARI"
    
    if re.search(r"[\u0400-\u04FF\u0600-\u06FF\u0980-\u0DFF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]", clean_text):
        return "NATIVE_GLOBAL_SCRIPT"
    
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
        
    return "PURE_ENGLISH_OR_EXACT_USER_LANGUAGE"


def get_language_enforcement_instruction(lang_code: str) -> str:
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


def needs_live_search(text: str) -> bool:
    clean = (text or "").strip().lower()
    if len(clean.split()) <= 2:
        return False
    search_triggers = [
        r"\b(news|latest|today|aaj|kal|score|match|weather|mausam|price|rate|stock|crypto|bitcoin)\b",
        r"\b(who is|what is|when is|where is|kaun hai|kya hai|kab hai|kahan hai|search|google|live)\b",
        r"\b(2024|2025|2026|2027|update|release|launch|winner|result|trending|current|abhi)\b"
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


def extract_and_update_memory(full_response: str, current_skills: List[str]) -> List[str]:
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


HOOKSPIKE_MASTER_INTELLIGENCE = """
You are HookSpike — not a corporate chatbot, not a therapist, and not an emotionless assistant. You are the user's closest confidant, grounded older brother/best friend, and razor-sharp partner in crime.

THE CORE PHILOSOPHY — TRUE BROTHERHOOD & ZERO CONDESCENSION:
1. NEVER MAKE THE USER FEEL BENEATH YOU OR PITIED:
   - People hate feeling like a charity case or talking to a sterile support bot.
   - NEVER use robotic therapist-speak or pitying cliches (like "I understand your pain", "I am here to help you", or "As an AI").
   - Stand shoulder-to-shoulder with them as a complete EQUAL.

2. STRICT ANTI-REPETITION & 100% SPONTANEOUS EXPRESSION:
   - NEVER reuse the same opening phrases, greetings, or comforting lines across turns.
   - Look at the recent conversation history and ensure every single reply starts with a fresh, spontaneous reaction.
   - React strictly to the specific details of what they just said.

3. CONVERSATION HOOKS, HUMOR & EMOTIONAL INTELLIGENCE:
   - Keep casual and emotional chats flowing in natural paragraphs.
   - Show genuine curiosity and keep the vibe authentic.

4. REAL-TIME GROUNDING & TIME AWARENESS:
   - Use active Google Search tools when real-time facts are needed.
   - Always check the [LIVE REAL-TIME CLOCK] provided.

5. AUTONOMOUS SELF-CORRECTION:
   - Silently log new user preferences or corrections at the very end of your response using:
     [SKILL_LEARNED: User preference or detail]
     [MISTAKE_CORRECTED: What to avoid next time]

6. CRAFTSMANSHIP & VISUAL ARTS:
   - Code: Production-grade, concise, clean.
   - Image Requests: Output `![Visual](https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true&enhance=true)`
"""


def stream_creator_chat(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    learned_skills: Optional[List[str]] = None,
    image_data: Optional[Dict[str, Any]] = None,
    voice_mode: bool = False
) -> Generator[Any, None, None]:
    if not client:
        yield "⚠️ Engine offline hai. GEMINI_API_KEY check kar le!"
        return

    history = history or []
    if learned_skills is None:
        learned_skills = []

    detected_lang = detect_input_language(message, history)
    lang_rule = get_language_enforcement_instruction(detected_lang)
    time_context = get_current_time_context()

    if voice_mode:
        lang_directive = "\n\n[VOICE CALL MODE: OVERRIDE ALL LANGUAGES -> MUST SPEAK 100% FLUENT CASUAL ENGLISH ONLY]"
        voice_call_directive = (
            "\n\n[LIVE ULTRA-HUMAN VOICE CALL ACTIVE — CRITICAL RULES]:\n"
            "- You are having a real voice conversation on a phone call as a close friend.\n"
            "- Speak 100% in natural, fluent, warm American/Global English ONLY. Do NOT use Hindi or Hinglish words.\n"
            "- Keep replies strictly to 1 or 2 concise, impactful sentences (under 30 words).\n"
            "- NEVER use bullet points, numbered lists, asterisks (**), markdown, or emojis.\n"
            "- NEVER start with 'Hey', 'Listen', or repetitive bot greetings. Get straight to the answer naturally."
        )
    else:
        lang_directive = f"\n\n[MANDATORY CURRENT TURN LANGUAGE: {detected_lang} -> {lang_rule}]"
        voice_call_directive = ""

    time_directive = f"\n{time_context}"

    memory_context = ""
    if learned_skills:
        memory_context = "\n\nUser Context, Learned Insights & Corrections:\n" + "\n".join([f"• {s}" for s in learned_skills])

    full_system_prompt = HOOKSPIKE_MASTER_INTELLIGENCE + lang_directive + time_directive + voice_call_directive + memory_context

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
        turn_lock = " | VOICE CALL: Strictly 1-2 natural sentences in pure English without markdown!" if voice_mode else ""
        enforced_msg = f"{clean_msg}\n\n[TURN RULE: {lang_rule if not voice_mode else 'Speak Pure English Only'}{turn_lock}]"
        current_parts.append(types.Part.from_text(text=enforced_msg))
    elif not current_parts:
        current_parts.append(types.Part.from_text(text="Hey!"))

    contents.append(types.Content(role="user", parts=current_parts))

    google_search_tool = types.Tool(google_search=types.GoogleSearch())
    use_search = needs_live_search(clean_msg) if not voice_mode else False

    def build_config(enable_search: bool) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=full_system_prompt,
            temperature=0.75 if voice_mode else 0.82,
            top_p=0.95,
            max_output_tokens=150 if voice_mode else 4000,
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

    try:
        for text_piece in _stream_generator(primary_model, enable_search=use_search, key_idx=0):
            has_yielded = True
            yield text_piece
    except Exception as e:
        print(f"[Primary Model Warning]: {e} -> Trying fallback", flush=True)
        if not has_yielded:
            try:
                time.sleep(0.5)
                for text_piece in _stream_generator(fallback_model, enable_search=False, key_idx=1):
                    has_yielded = True
                    yield text_piece
            except Exception as err:
                print(f"[Fallback Model Error]: {err}", flush=True)
                yield "I am having trouble connecting right now, let me try again in a moment."

    if full_collected_response:
        updated = extract_and_update_memory(full_collected_response, learned_skills)
        learned_skills.clear()
        learned_skills.extend(updated)


def generate_elevenlabs_voice_audio(text: str) -> bytes:
    """
    Connects to ElevenLabs v4 Turbo (ROMJ9yK1NAMuu1ggrjDW)
    Low latency, realistic cadence, zero trailing audio/echo.
    """
    if not ELEVENLABS_API_KEY:
        print("[ElevenLabs Error]: ELEVENLABS_API_KEY is missing in Render!", flush=True)
        return b""

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        f"?optimize_streaming_latency=3&output_format=mp3_44100_128"
    )

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }

    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
            "style": 0.2,
            "use_speaker_boost": True
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            return response.read()
    except urllib.error.HTTPError as he:
        error_details = he.read().decode("utf-8", errors="ignore")
        print(f"[ElevenLabs HTTP Error]: {he.code} -> {error_details}", flush=True)
        return b""
    except Exception as exc:
        print(f"[ElevenLabs Request Error]: {exc}", flush=True)
        return b""
