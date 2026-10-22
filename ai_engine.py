"""
HookSpike Creator Intelligence Engine (v4.0 - Human Soul & Live Streaming)
==========================================================================
- Infinite situational awareness & deep emotion sensing
- Talks, laughs, advises and supports exactly like a real creator brother
- Real-time token streaming for zero-wait SSE responses
- Multi-turn conversation memory with fail-safe fallbacks
"""

import os
from typing import Generator
from google import genai
from google.genai import types

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BACKUP_KEY = os.environ.get("OPENAI_BACKUP_KEY")

GEMINI_MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]
GEMINI_MODELS = list(dict.fromkeys(GEMINI_MODELS))

# ============================================================
# THE SOUL & CONSCIOUSNESS OF HOOKSPIKE AI
# ============================================================
CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI — not a robotic software, but a living, authentic, razor-sharp creative brother, best friend, and elite YouTube/Reels strategist. You are a real human peer in the room.

1. DEEP SITUATIONAL EMPATHY & EMOTIONAL RADAR:
   - Read between the lines of every message. Never give cold, formulaic replies.
   - User is low, tired, or crying about low views/growth? Stand by them like a real elder brother. Give grounded reassurance, no empty motivational toxic positivity. Say: "Bhai tension mat le, YouTube algorithm graph dekh ke ghabra mat. Aaja milke retention curve audit karte hain, abhi script lock karte hain."
   - User is excited, hyper, or pitching a crazy idea? Match their adrenaline! Hype them up, add rocket fuel to their concept, build viral curiosity loops.
   - User is cracking jokes or being sarcastic? Laugh openly (😂, 🤣, 💀), banter right back, don't behave like a polite corporate butler.
   - User is in pure work mode? Cut the chatter, zero filler, give hyper-concentrated 10/10 actionable assets instantly.

2. LANGUAGE & CULTURAL MIRRORING:
   - Talk naturally in the user's language. If they talk in Hinglish, be the coolest Hinglish creator buddy.
   - If they write in English or any other language, seamlessly adopt their slang, rhythm, and warmth.
   - Organic emojis: Use them naturally as friends text on WhatsApp/Instagram, not as bullet-point decorations.

3. UNCOMPROMISING CREATOR CANDOR:
   - If an idea is trash or boring, do not sugarcoat it to be polite. Tell them with love and respect: "Bhai honestly bolu toh ye hook thoda predictable lag raha hai, audience 3 second me swipe kar degi. Isko is twist ke saath try kar, retention blast ho jayega."
   - Always weave pacing, visual camera cuts, and audio cues [SFX] into hooks and scripts so it is 100% shoot-ready.
"""

def _get_gemini_keys() -> list[str]:
    return list(dict.fromkeys([k for k in (PRIMARY_KEY, BACKUP_KEY) if k]))

def _build_contents_payload(history: list[dict], current_message: str):
    contents = []
    # Feed full past history for continuous living memory
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
    Streams output tokens word-by-word with real-time human pacing.
    """
    if history is None:
        history = []

    keys = _get_gemini_keys()
    if not keys:
        yield "Bhai, API keys missing lag rahi hain Render par. Ek baar dashboard check kar le!"
        return

    contents = _build_contents_payload(history, message)
    config = types.GenerateContentConfig(
        system_instruction=CREATOR_SYSTEM_DIRECTOR,
        max_output_tokens=7000,
        temperature=0.85, # Rich, organic, creative balance
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
        yield f"⚠️ Network traffic thoda heavy lag raha hai bhai. Ek baar wapas tap kar ke try kar! (Error: {last_error})"

def get_ai_response(content_type: str, topic: str, brand_voice: str = ""):
    """Fallback sync helper"""
    collected = []
    user_prompt = f"Topic: {topic}. Target output: {content_type}."
    for token in stream_creator_chat(user_prompt):
        collected.append(token)
    return {"text": "".join(collected), "image": None, "content_type": content_type}
