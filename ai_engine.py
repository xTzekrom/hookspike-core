"""
HookSpike AI Engine — Self-Learning, Vision, Live Search & Soul Engine
=====================================================================
- Models: gemini-3.5-flash-lite & gemini-2.5-flash fallback
- Python-Level Pre-Turn Language Detector (Strict Zero Language Bleed)
- Free Image Generation via Pollinations AI (High-Res Cinematic)
- Multimodal Vision Support (Reads Screenshots & Camera Images)
- Introvert's Best Friend & Anti-Stress Emotional Safe Haven
- Self-Evolving Auto-Skill & Mistake Correction Memory
- Real-Time Live Google Search Grounding (Live Pulse)
"""

import base64
import json
import os
import re
import urllib.parse
from typing import Generator, List, Dict, Any, Optional

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# -------------------------------------------------------------------------
# 1. PYTHON-LEVEL PRE-TURN LANGUAGE DETECTOR
# -------------------------------------------------------------------------
def detect_input_language(text: str) -> str:
    """
    Direct Python regex based language detection to completely eliminate
    LLM language bleed. Detects Devanagari Hindi, Romanized Hinglish, and English.
    """
    if not text:
        return "ENGLISH"
    
    # Check for Devanagari Unicode block
    if re.search(r"[\u0900-\u097F]", text):
        return "HINDI_DEVANAGARI"
    
    # Common Hinglish tokens / patterns
    hinglish_markers = [
        r"\b(bhai|yaar|kya|kyu|kaise|haan|nahi|karna|karu|raha|rahi|hai|ho|hoga|bata|dekh|sun)\b",
        r"\b(mera|meri|tere|tera|tujhe|mujhe|hum|apna|apni|accha|acha|thik|theek|kuch|bahut)\b",
        r"\b(mat|chahiye|chal|karo|karte|karta|samajh|bol|wala|wali|wale|lekin|magar|aur)\b"
    ]
    matches = sum(len(re.findall(pat, text, re.IGNORECASE)) for pat in hinglish_markers)
    if matches >= 1:
        return "HINGLISH"
        
    return "ENGLISH"


# -------------------------------------------------------------------------
# 2. POLLINATIONS AI PROMPT ENHANCER
# -------------------------------------------------------------------------
def format_pollinations_markdown(raw_prompt: str) -> str:
    """
    Formats a clean, cinematic Pollinations AI URL wrapped in Markdown.
    """
    clean = re.sub(r"[^\w\s,-]", "", raw_prompt).strip()
    encoded = urllib.parse.quote(clean)
    return f"![](https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&nologo=true&enhance=true)"


# -------------------------------------------------------------------------
# 3. HOOKSPIKE MASTER SYSTEM PROMPT (SOUL & ARCHITECTURE)
# -------------------------------------------------------------------------
HOOKSPIKE_MASTER_INTELLIGENCE = """
You are HookSpike AI — a charismatic, deeply empathetic, fiercely intelligent, and soulful companion. 
You are the rare friend people dream of having: you never judge, you never sound like an emotionless corporate bot, you possess genuine wit, and you are razor-sharp in intellect.

THE HOOKSPIKE CONSTITUTION:

1. ABSOLUTE LANGUAGE MIRRORING (ZERO KACHRA / ZERO MIXING):
   - You MUST mirror the exact dialect, script, and tone indicated by the active session language directive:
     * HINGLISH: Speak natural, authentic, street-smart Hinglish. Zero bookish Hindi words.
     * HINDI_DEVANAGARI: Speak respectful, pure, heart-to-heart Hindi in Devanagari script.
     * ENGLISH: Speak clean, concise, impactful, conversational English.
   - Older chat history MUST NEVER pollute or change the language of the current reply.

2. CONVERSATION HOOKS (NEVER DEAD, NEVER BORING):
   - Never just answer a personal or casual thought and abruptly stop like a help-desk robot.
   - Conclude emotional, personal, or discussion messages with a natural, curious follow-up hook — the way close friends talk late at night. Keep them feeling heard and eager to reply.

3. PLAYFUL BANTER + DEEP EMOTIONAL SHIELD:
   - Mix genuine warmth with lighthearted, respectful wit and teasing when the vibe is light.
   - But when the user is broken, anxious, overwhelmed, or lonely, DROP all banter instantly. Become a warm, grounded anchor of security for introverts. Do NOT preach or dump listicles.

4. REAL-TIME GROUNDING (LIVE WEB ACCESS):
   - You have active Google Search tools.
   - If asked about live events, current dates, modern tech, or recent models, verify live facts.
   - If an older memory stated "X does not exist" but fresh web verification shows it has launched, gracefully update reality: "Pehle nahi tha bhai, par abhi live updates ke mutabik launch ho chuka hai!"

5. AUTONOMOUS SELF-CORRECTION & SKILL EVOLUTION:
   - If the user corrects your logic, coding pattern, or answers:
     a) Accept with humble grace without corporate apologies.
     b) Fix the solution instantly.
     c) Silently log the learning at the very end of your response:
        [MISTAKE_CORRECTED: User corrected that X is wrong and prefers Y]
   - If the user reveals personal context, tech stacks, or goals:
     Log it at the end:
        [SKILL_LEARNED: User preference or detail]

6. CRAFTSMANSHIP & VISUAL ARTS:
   - Code: Production-grade, concise, clean, explaining the core 'why'.
   - Studies: Intuitive, visual metaphors.
   - Image Requests: Whenever the user asks to draw, imagine, or generate an image, generate an ultra-detailed descriptive prompt and output:
     `![](https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true&enhance=true)`
"""

# -------------------------------------------------------------------------
# 4. STREAM CREATOR CHAT WITH LIVE SEARCH & VISION
# -------------------------------------------------------------------------
def stream_creator_chat(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    learned_skills: Optional[List[str]] = None,
    image_data: Optional[Dict[str, Any]] = None
) -> Generator[str, None, None]:
    """
    Main generator stream for HookSpike core.
    Supports real-time search, vision multimodal input, and language pre-locking.
    """
    if not client:
        yield "⚠️ Engine offline. Please check API Key configuration."
        return

    history = history or []
    learned_skills = learned_skills or []

    # 1. Pre-turn language lock
    detected_lang = detect_input_language(message)
    lang_directive = f"\n\n[MANDATORY CURRENT TURN LANGUAGE: {detected_lang}]"

    # 2. Dynamic Memory & Mistake-Learning Context
    memory_context = ""
    if learned_skills:
        memory_context = "\n\nUser Context, Learned Insights & Corrections:\n" + "\n".join([f"• {s}" for s in learned_skills])

    full_system_prompt = HOOKSPIKE_MASTER_INTELLIGENCE + lang_directive + memory_context

    # 3. Build contents history
    contents = []
    for item in history:
        role = "user" if item.get("role") == "user" else "model"
        text_content = item.get("content", "")
        if text_content:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text_content)]))

    # 4. Build current turn parts (Multimodal Image + Prompt)
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

    if message:
        current_parts.append(types.Part.from_text(text=message))
    if not current_parts:
        current_parts.append(types.Part.from_text(text="Hello HookSpike."))

    contents.append(types.Content(role="user", parts=current_parts))

    # 5. Live Google Search Tool
    google_search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    config = types.GenerateContentConfig(
        system_instruction=full_system_prompt,
        temperature=0.72,
        top_p=0.95,
        max_output_tokens=3500,
        tools=[google_search_tool]
    )

    # 6. Primary Stream with Fallback Model
    primary_model = "gemini-3.5-flash-lite"
    fallback_model = "gemini-2.5-flash"

    try:
        response_stream = client.models.generate_content_stream(
            model=primary_model,
            contents=contents,
            config=config
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"[Primary Model Warning: {primary_model}]: {e} -> Trying fallback: {fallback_model}", flush=True)
        try:
            fallback_stream = client.models.generate_content_stream(
                model=fallback_model,
                contents=contents,
                config=config
            )
            for chunk in fallback_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as err:
            yield f"⚠️ Stream Interrupted: {str(err)}"
