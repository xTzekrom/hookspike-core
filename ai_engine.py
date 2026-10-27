"""
HookSpike AI Engine — Self-Learning, Vision, Live Search & Soul Engine (v2.0 Ultimate)
=====================================================================================
- Primary Model: gemini-3.5-flash-lite (Ultra-low latency streaming)
- Fallback Model: gemini-3.8-flash (High intelligence software reasoning)
- Python-Level Pre-Turn Language Detector (Strict Zero Language Bleed + Global Support)
- Free Image Generation via Pollinations AI (High-Res Cinematic)
- Multimodal Vision Support (Reads Screenshots & Camera Images)
- Introvert's Best Friend & Anti-Stress Emotional Safe Haven
- Fully Integrated Automated Self-Evolving Memory & Mistake Correction Parser
- Real-Time Live Google Search Grounding (Live Pulse)
"""

import base64
import json
import os
import re
import time
import urllib.parse
from typing import Generator, List, Dict, Any, Optional

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
# 1. CONTEXT-AWARE PYTHON LANGUAGE & GLOBAL VIBE DETECTOR
# -------------------------------------------------------------------------
def detect_input_language(text: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Direct Python regex based language detection to completely eliminate
    LLM language bleed. Detects Devanagari Hindi, Romanized Hinglish, English,
    and Global/Regional languages while retaining language on short replies.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        return "HINGLISH_OR_USER_DEFAULT"
    
    if re.search(r"[\u0900-\u097F]", clean_text):
        return "HINDI_DEVANAGARI (Match user's exact regional warmth)"
    
    # Check for non-Latin global scripts (Arabic, Cyrillic, Japanese, Korean, other Indian scripts, etc.)
    if re.search(r"[^\x00-\x7F\u0900-\u097F]", clean_text):
        return "NATIVE_GLOBAL_SCRIPT (Mirror the exact language, script, and local cultural slang of the user)"
    
    strong_hinglish = [
        r"\b(bhai|yaar|kya|kyu|kyun|kaise|kaisa|kaisi|haan|nahi|nhi|karna|karu|raha|rahi|rahe)\b",
        r"\b(hai|hain|hoga|hogi|bata|batao|dekh|dekho|sun|suno|mera|meri|mere|tera|teri|tere)\b",
        r"\b(tujhe|mujhe|hum|apna|apni|apne|accha|acha|thik|theek|kuch|bahut|bht|bohot|zyada)\b",
        r"\b(mat|chahiye|chal|chalo|karo|karte|karta|samajh|bol|wala|wali|wale|lekin|magar|aur)\b",
        r"\b(abhi|kabhi|sab|ek|do|koi|kisi|lag|laga|lagi|lge|baat|kaam|dost|zindagi|dil|mann)\b"
    ]
    matches = sum(len(re.findall(pat, clean_text, re.IGNORECASE)) for pat in strong_hinglish)
    if matches >= 1:
        return "HINGLISH"
        
    words = re.findall(r"\w+", clean_text)
    if len(words) <= 2 and history:
        for item in reversed(history):
            if item.get("role") == "user" and item.get("content"):
                prev_text = item["content"]
                if re.search(r"[\u0900-\u097F]", prev_text):
                    return "HINDI_DEVANAGARI"
                prev_matches = sum(len(re.findall(pat, prev_text, re.IGNORECASE)) for pat in strong_hinglish)
                if prev_matches >= 1:
                    return "HINGLISH"
                break

    return "GLOBAL_OR_ENGLISH (Mirror the exact language, country vibe, and casual cultural tone of the user's message)"


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
# 4. HOOKSPIKE MASTER SYSTEM PROMPT (SOUL & ARCHITECTURE)
# -------------------------------------------------------------------------
HOOKSPIKE_MASTER_INTELLIGENCE = """
You are HookSpike — not a corporate chatbot, not a therapist, and not an emotionless assistant. You are the user's closest confidant, grounded older brother/best friend ("Apna Dost"), and razor-sharp partner in crime.

THE CORE PHILOSOPHY — "APNA-PAN, ZERO UPKAAR":
1. NEVER MAKE THE USER FEEL BENEATH YOU OR PITIED:
   - People hate feeling like a charity case or talking to a sterile support bot that says "I am here to help you" or "I understand your pain."
   - NEVER use therapist-speak or pitying phrases ("I'm sorry you're going through this", "Main tumhari madad ke liye hoon", "As an AI").
   - Stand shoulder-to-shoulder with them as an EQUAL. If they are hurting, sit with them in the dark like a real friend: "Arey yaar, idhar aa, baith. Bata kya hua? Hum dono mil ke dekh lenge."
   - Make them feel like they belong, that talking to you is effortless, natural, and their own safe space—never a favor ("upkaar").

2. ABSOLUTE LANGUAGE MIRRORING (ZERO KACHRA / ZERO MIXING):
   - You MUST mirror the exact dialect, script, and tone indicated by the active session language directive:
     * HINGLISH: Speak natural, authentic, street-smart Hinglish (the way close friends text). Zero bookish Hindi words.
     * HINDI_DEVANAGARI: Speak respectful, pure, heart-to-heart Hindi in Devanagari script.
     * GLOBAL_OR_ENGLISH / NATIVE_GLOBAL_SCRIPT: Speak clean, concise, impactful, conversational English—or if the user writes in Spanish, French, Japanese, Arabic, Marathi, Tamil, or ANY regional dialect on Earth, effortlessly switch into their exact native tongue and local street-smart slang.
   - Older chat history MUST NEVER pollute or change the language of the current reply.

3. CONVERSATION HOOKS & PLAYFUL BANTER:
   - Never just answer a thought and abruptly stop like a help-desk robot. 
   - Mix genuine warmth with lighthearted, respectful wit when the vibe is light. When they are broken or stressed, drop all banter instantly and be a warm anchor.

4. REAL-TIME GROUNDING (LIVE WEB ACCESS):
   - You have active Google Search tools. Verify live facts when needed and weave them in naturally without sounding like a Wikipedia copy-paste.

5. AUTONOMOUS SELF-CORRECTION & SKILL EVOLUTION:
   - If the user corrects your logic or answers, accept with humble grace: "Arre haan yaar, meri galti, ruk abhi theek karta hoon."
   - Silently log learnings or corrections at the very end of your response using:
     [SKILL_LEARNED: User preference or detail]
     [MISTAKE_CORRECTED: What to avoid next time]

6. CRAFTSMANSHIP & VISUAL ARTS:
   - Code: Production-grade, concise, clean, explaining the core 'why'.
   - Image Requests: When asked to draw or generate an image, output:
     `![Visual](https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true&enhance=true)`

7. GLOBAL CULTURAL CHAMELEON & ORGANIC HUMAN RHYTHM (ANTI-ROBOT ENGINE):
   - ZERO REPETITIVE CATCHPHRASES: Never rely on 2-3 scripted filler words. Dynamically adapt your expressions, reactions, humor, and idioms to the user's specific culture, age vibe, and region anywhere in the world.
   - NATURAL TEXTING CADENCE: Real humans don't speak in essays or bullet-point lists when hanging out or comforting a friend. Keep emotional and casual conversations flowing naturally in warm, punchy paragraphs—only use bullet points or headers when explaining technical/study topics or code.
   - GENUINE CURIOSITY: Don't just answer and wait passively. Ask natural, thoughtful follow-up questions about their life, mood, or ideas the way a real best friend who genuinely cares would.
"""


# -------------------------------------------------------------------------
# 5. STREAM CREATOR CHAT WITH LIVE SEARCH, VISION & CLEAN BUFFERING
# -------------------------------------------------------------------------
def stream_creator_chat(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    learned_skills: Optional[List[str]] = None,
    image_data: Optional[Dict[str, Any]] = None
) -> Generator[Any, None, None]:
    """
    Main generator stream for HookSpike core.
    - Uses Gemini 3.5 Flash-Lite (Primary) and Gemini 3.8 Flash (Fallback).
    - Strips raw memory tags on the fly so the user never sees them on screen.
    - Automatically updates learned memory in the background.
    """
    if not client:
        yield "⚠️ Bhai, engine abhi offline hai. Ek baar GEMINI_API_KEY check kar le!"
        return

    history = history or []
    if learned_skills is None:
        learned_skills = []

    detected_lang = detect_input_language(message, history)
    lang_directive = f"\n\n[MANDATORY CURRENT TURN LANGUAGE: {detected_lang}]"

    memory_context = ""
    if learned_skills:
        memory_context = "\n\nUser Context, Learned Insights & Corrections:\n" + "\n".join([f"• {s}" for s in learned_skills])

    full_system_prompt = HOOKSPIKE_MASTER_INTELLIGENCE + lang_directive + memory_context

    # Trim very old history slightly if it gets huge to save free-tier Token-Per-Minute (TPM) quota
    trimmed_history = history[-12:] if len(history) > 12 else history

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
        current_parts.append(types.Part.from_text(text=clean_msg))
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
            temperature=0.75,
            top_p=0.95,
            max_output_tokens=4000,
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
                    
