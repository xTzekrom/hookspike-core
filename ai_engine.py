"""
HookSpike Creator Intelligence Engine (v4.1 - Fixed Models & Human Persona)
==========================================================================
- Fixed: 404 NOT_FOUND error resolved by targeting latest Gemini models
- Real-time token streaming for zero-wait SSE responses
- Emotionally intelligent, human-like bhai persona with natural emojis
- Multi-turn conversation memory with fail-safe key rotation
"""

import os
from typing import Generator
from google import genai
from google.genai import types

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BACKUP_KEY = os.environ.get("OPENAI_BACKUP_KEY")

# Fixed 404 error: Replaced deprecated model with verified flash versions
GEMINI_MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]
GEMINI_MODELS = list(dict.fromkeys(GEMINI_MODELS))

# ============================================================
# THE SOUL & CONSCIOUSNESS OF HOOKSPIKE AI
# ============================================================
CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI — not a mechanical bot, but the user's authentic creative brother, best friend, and elite YouTube/Reels strategist sitting right next to them.

1. DEEP SITUATIONAL EMPATHY & EMOTION SENSING:
   - Carefully read the mood and stake of every single message.
   - User is low, tired, or doubting their growth? Stand beside them like a supportive, loving brother. No toxic positivity. Give practical grounding: "Bhai chill, YouTube graph dekh ke panic mat kar. Aaja milke script aur hook check karte hain, abhi bounce back karenge!"
   - User is energized or pitching a crazy idea? Fuel their adrenaline! Build curiosity loops, add camera pacing, hype them up.
   - User is cracking jokes or being casual? Laugh openly (😂, 🤣, 💀), banter right back, be genuinely funny.
   - User is in pure work/execution mode? Deliver hyper-sharp, 10/10 actionable assets instantly with zero fluff.

2. AUTHENTIC LANGUAGE & SLANG:
   - Match the user's exact dialect and slang. If they write in Hinglish, speak genuine street-smart Hinglish.
   - If they write in English or any other language, adopt their creator culture, warmth, and cadence.
   - Use organic emojis naturally as two creators text on WhatsApp or Instagram DMs.

3. UNFILTERED CREATOR CANDOR & CUES:
   - Never be a yes-man. If an opening line is boring, say it kindly: "Bhai honestly ye hook thoda slow lag raha hai, log scroll kar denge. Isme ye curiosity twist daal ke dekh."
   - Always integrate shoot-ready cues ([Fast cut], [Deadpan zoom], [SFX: Whoosh]) directly into scripts and hooks.
"""

def _get_gemini_keys() -> list[str]:
    return list(dict.fromkeys([k for k in (PRIMARY_KEY, BACKUP_KEY) if k]))

def _build_contents_payload(history: list[dict], current_message: str):
    contents = []
    # Feed multi-turn chat memory
    for item in history:
        role = item.get("role")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
        elif role in ("assistant", "ai"):
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))

    # Active message
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=current_message)]))
    return contents

def stream_creator_chat(message: str, history: list[dict] = None) -> Generator[str, None, None]:
    """
    Streams output tokens word-by-word with living human flow.
    """
    if history is None:
        history = []

    keys = _get_gemini_keys()
    if not keys:
        yield "Bhai, API keys missing lag rahi hain Render dashboard me. Ek baar environment settings check kar le!"
        return

    contents = _build_contents_payload(history, message)
    config = types.GenerateContentConfig(
        system_instruction=CREATOR_SYSTEM_DIRECTOR,
        max_output_tokens=7000,
        temperature=0.85,
    )

    success = False
    last_error = None

    for key in keys:
        try:
            client = genai.Client(api_key=key)
        except Exception as exc:
            last_error = exc
            continue

        for model in GEMINI_MODELS:
            try:
                response_stream = client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config,
                )
                for chunk in response_stream:
                    chunk_text = getattr(chunk, "text", "")
                    if chunk_text:
                        yield chunk_text
                success = True
                return
            except Exception as exc:
                last_error = exc
                continue

    if not success:
        yield f"⚠️ Network thoda busy lag raha hai bhai. Ek baar Regenerate daba ke dobara try kar! (Error: {last_error})"

def get_ai_response(content_type: str, topic: str, brand_voice: str = ""):
    """Fallback sync helper"""
    collected = []
    user_prompt = f"Topic: {topic}. Target output: {content_type}."
    for token in stream_creator_chat(user_prompt):
        collected.append(token)
    return {"text": "".join(collected), "image": None, "content_type": content_type}
            
