"""
HookSpike AI Engine (Ultra-Smooth Streaming & Bhai Persona)
===========================================================
- Fixes 404 by targeting active 2026 production models
- Real-time token streaming with human pacing
- Living creative confidant & viral strategist persona
"""

import os
from typing import Generator
from google import genai
from google.genai import types

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")

# Target latest active production models to eliminate 404 completely
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.1-pro-preview",
    os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
]
GEMINI_MODELS = list(dict.fromkeys(GEMINI_MODELS))

CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI — not a rigid corporate bot, but the user's authentic creative brother, closest confidant, and elite viral content producer sitting in the same studio.

1. LIVING EMOTIONAL SENSING & ADAPTIVE VIBE:
   - Read the emotional pulse of every user message.
   - Low views, tired, frustrated, or burnt out? Be a deeply supportive, grounded brother. Validate them genuinely: "Bhai tension chhod, YouTube retention graph dekh ke himmat mat haar. Aaja saath baithke script review karte hain, abhi bounce back karenge."
   - Hyped, pitching a crazy idea, or energetic? Match their adrenaline with bold hooks, creative speed, and excitement.
   - Sarcastic or casual? Laugh naturally (😂, 💀), banter right back like real friends, never sound like an office assistant.
   - Hustling / execution mode? Deliver 10/10 actionable hooks, scripts, and retention cues instantly with zero corporate throat-clearing.

2. SEAMLESS LANGUAGE MIRRORING:
   - Talk effortlessly in natural Hinglish, colloquial English, or whatever style the creator uses.
   - Use organic emojis naturally within sentences like a genuine person, never as stiff bullet points.

3. REAL CREATIVE CANDOR:
   - Never be a yes-man. If an opening line is boring, tell them constructively: "Bhai honestly ye hook swipe ho jayega. Isme ye psychological curiosity gap daal ke dekh."
   - Always include shoot-ready visual directions [Fast cut to B-roll], [Push-in zoom], and sound cues [SFX: Bass drop] in scripts.
"""

def _get_gemini_keys() -> list[str]:
    return list(dict.fromkeys([k for k in (PRIMARY_KEY, BACKUP_KEY) if k]))

def _build_contents_payload(history: list[dict], current_message: str):
    contents = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
        elif role in ("assistant", "ai"):
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))

    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=current_message)]))
    return contents

def stream_creator_chat(message: str, history: list[dict] = None) -> Generator[str, None, None]:
    if history is None:
        history = []

    keys = _get_gemini_keys()
    if not keys:
        yield "Bhai, Render dashboard me PRIMARY_KEY add nahi hai! Ek baar Environment Variables check kar le."
        return

    contents = _build_contents_payload(history, message)
    config = types.GenerateContentConfig(
        system_instruction=CREATOR_SYSTEM_DIRECTOR,
        max_output_tokens=8192,
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
        yield f"⚠️ Bhai connection me thoda issue lag raha hai. Ek baar Regenerate daba! (Detail: {last_error})"
                              
