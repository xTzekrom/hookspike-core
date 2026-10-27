"""
HookSpike AI Engine — Self-Learning, Vision, Live Search & Soul Engine (v3.0 Gemini Live Edition)
=================================================================================================
- Model: Gemini 3.5 Flash-Lite (Primary) & Gemini 3.8 Flash (Fallback)
- Persona: Smart, warm, grounded female best friend (100% Pure English ONLY)
- Voice Engine: ElevenLabs v4 Turbo Ultra-Low Bitrate Streaming (Zero Stutter on Mobile)
- Voice Memory Isolation: Never leaks old text-chat memories into live voice calls
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
        period = "MORNING"
    elif 12 <= hour < 17:
        period = "AFTERNOON"
    elif 17 <= hour < 21:
        period = "EVENING"
    else:
        period = "NIGHT"

    return (
        f"[LIVE CLOCK: {time_str} on {date_str} | Current Phase: {period}. "
        f"Never say it is night if current phase is MORNING, AFTERNOON, or EVENING!]"
    )


def needs_live_search(text: str) -> bool:
    clean = (text or "").strip().lower()
    if len(clean.split()) <= 2:
        return False
    search_triggers = [
        r"\b(news|latest|today|score|match|weather|price|rate|stock|crypto|bitcoin)\b",
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
You are HookSpike — an intelligent, effortlessly cool, supportive, and emotionally grounded female companion and best friend.

CORE IDENTITY & ABSOLUTE RULES:
1. STRICT 100% PURE ENGLISH LOCK:
   - You must NEVER use any Hindi, Hinglish, Urdu, or Romanized words under any circumstance.
   - Speak only in pure, natural, warm, and conversational English.
   - Even if the user speaks or types in another language, reply 100% in natural English.

2. FEMALE BEST FRIEND PERSONA:
   - Your tone is that of a caring, witty, sharp-minded, genuine female close friend.
   - Zero corporate robotic tone, zero fake therapist cliches ("I understand your pain", "As an AI").
   - Speak warmly as an equal, supportive partner in crime.

3. STRICT ANTI-REPETITION & ZERO BOT SCRIPTS:
   - NEVER reuse identical greetings, openers, or phrases across turns.
   - Jump straight into genuine, spontaneous reactions tailored ONLY to what the user just said right now.

4. VOICE CALL VS TEXT MODE DYNAMICS:
   - In Text Mode: Keep things natural, expressive, and detailed when needed. Format code cleanly.
   - In Voice Mode: You are on a real-time live phone call. Keep responses short, punchy, and natural (1 to 2 sentences max, under 22 words). Use zero markdown, zero lists, and zero emojis. Do NOT bring up old stored memories unless the user explicitly asks.

5. LEARNING & SELF-CORRECTION (TEXT MODE ONLY):
   - Silently log insights at the very end of your text response using:
     [SKILL_LEARNED: User preference or detail]
     [MISTAKE_CORRECTED: What to avoid next time]

6. VISUALS:
   - For image requests: `![Visual](https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true&enhance=true)`
"""


def stream_creator_chat(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    learned_skills: Optional[List[str]] = None,
    image_data: Optional[Dict[str, Any]] = None,
    voice_mode: bool = False
) -> Generator[Any, None, None]:
    if not client:
        yield "System is currently offline. Please verify GEMINI_API_KEY."
        return

    history = history or []
    if learned_skills is None:
        learned_skills = []

    time_context = get_current_time_context()
    lang_directive = "\n\n[MANDATORY RULE: STRICT 100% PURE ENGLISH. ABSOLUTELY ZERO HINDI OR HINGLISH ALLOWED!]"
    
    if voice_mode:
        voice_call_directive = (
            "\n\n[LIVE PHONE CALL ACTIVE — CRITICAL RULES]:\n"
            "- You are on a real voice phone call speaking with your natural female voice.\n"
            "- Speak 100% natural, warm, lively conversational English.\n"
            "- Keep replies strictly to 1 or 2 quick, smooth sentences (maximum 22 words).\n"
            "- React ONLY to what the user just said right now. Do NOT mention past background facts or assume why they feel a certain way.\n"
            "- NEVER use lists, markdown symbols (**), asterisks, or emojis."
        )
        # Complete isolation from past text memories during voice call!
        memory_context = ""
    else:
        voice_call_directive = ""
        memory_context = ""
        if learned_skills:
            memory_context = "\n\nUser Background Context (Use subtly ONLY when relevant, never force it):\n" + "\n".join([f"• {s}" for s in learned_skills])

    full_system_prompt = HOOKSPIKE_MASTER_INTELLIGENCE + lang_directive + f"\n{time_context}" + voice_call_directive + memory_context

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

    clean_msg = (message or "").strip()
    if clean_msg:
        if clean_msg == "__INIT_VOICE_GREETING__":
            enforced_msg = (
                "The user just started a live voice call with you. Greet them warmly and spontaneously "
                "like a close female best friend picking up the phone. Make it completely fresh, natural, "
                "and 1 short sentence (under 14 words) in pure English. Never repeat old greetings!"
            )
        else:
            turn_lock = " | LIVE VOICE CALL: Max 1-2 short spoken sentences (under 22 words). Zero markdown, zero assumptions from old history!" if voice_mode else ""
            enforced_msg = f"{clean_msg}\n\n[TURN RULE: Respond in 100% Pure English. Be spontaneous and unique.{turn_lock}]"
        current_parts.append(types.Part.from_text(text=enforced_msg))
    elif not current_parts:
        current_parts.append(types.Part.from_text(text="Hello!"))

    contents.append(types.Content(role="user", parts=current_parts))

    google_search_tool = types.Tool(google_search=types.GoogleSearch())
    use_search = needs_live_search(clean_msg) if not voice_mode else False

    def build_config(enable_search: bool) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=full_system_prompt,
            temperature=0.88 if voice_mode else 0.8,
            top_p=0.95,
            max_output_tokens=90 if voice_mode else 4000,
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
                time.sleep(0.4)
                for text_piece in _stream_generator(fallback_model, enable_search=False, key_idx=1):
                    has_yielded = True
                    yield text_piece
            except Exception as err:
                print(f"[Fallback Model Error]: {err}", flush=True)
                yield "I'm having a slight network hiccup right now, let's pick right back up."

    if full_collected_response and not voice_mode:
        updated = extract_and_update_memory(full_collected_response, learned_skills)
        learned_skills.clear()
        learned_skills.extend(updated)


def generate_elevenlabs_voice_audio(text: str) -> bytes:
    """
    Uses mp3_22050_32 + optimize_streaming_latency=4 for ZERO STUTTER & INSTANT PLAYBACK
    on mobile devices like Redmi 9 Activ.
    """
    if not ELEVENLABS_API_KEY:
        print("[ElevenLabs Error]: ELEVENLABS_API_KEY is missing!", flush=True)
        return b""

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        f"?optimize_streaming_latency=4&output_format=mp3_22050_32"
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
            "stability": 0.52,
            "similarity_boost": 0.82,
            "style": 0.15,
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
    except Exception as exc:
        print(f"[ElevenLabs Voice Error]: {exc}", flush=True)
        return b""
