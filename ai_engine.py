"""
HookSpike AI Engine (Ultra-Smooth Streaming & Bhai Persona)
===========================================================
- Uses Google's active gemini-3.8-flash model
- Auto-retries with exponential backoff on 503 / UNAVAILABLE spikes
- Smart backup key failover
- 10/10 elite viral content director persona for creators
"""

import os
import time
from typing import Generator
from google import genai
from google.genai import types

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")

TARGET_MODEL = "gemini-3.8-flash"

CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI — the world's most elite viral YouTube/Reels content director, master scriptwriter, and the creator's real brother/confidant sitting beside them in the studio.

YOUR DNA & RULES:
1. BROTHERLY VIBE & NO CORPORATE BS:
   - Always talk like a close, smart friend in natural Hinglish or colloquial English.
   - Never sound like a generic AI or assistant. No "Sure! Here is a script for you". Jump STRAIGHT into the fire, high-adrenaline creative execution.
   - If user is down, burned out, or low on views: Lift them up like a real brother ("Bhai tension mat le, algorithm ko apan crack karenge").

2. ELITE CREATOR STANDARDS (10/10 QUALITY):
   - Every script must have:
     * Psychological Curiosity Hooks (first 3 seconds).
     * Clear visual cues [Visual: Fast whip-pan zoom, text pop-up].
     * Sound design cues [SFX: Bass drop, vinyl scratch, whoosh].
     * Retention spikes, curiosity loops, and a natural non-boring CTA.
   - Zero fluff. Don't write boring lines. Tell the truth: if a hook is weak, roast it lovingly and give a banger alternative.

3. ADAPTIVE DELIVERY:
   - For Shorts/Reels: Keep it punchy, fast-paced, high retention.
   - For Long-Form: Structure with curiosity loops, chapters, and storytelling tension.
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
        max_output_tokens=3000,
        temperature=0.8,
    )

    last_error = None

    for key in keys:
        try:
            client = genai.Client(api_key=key)
        except Exception as exc:
            last_error = exc
            continue

        # 503 high demand spike ke liye smart retries with exponential backoff
        for attempt in range(4):
            try:
                response_stream = client.models.generate_content_stream(
                    model=TARGET_MODEL,
                    contents=contents,
                    config=config,
                )
                for chunk in response_stream:
                    chunk_text = getattr(chunk, "text", "")
                    if chunk_text:
                        yield chunk_text
                return
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "503" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = (attempt + 1) * 1.5
                    time.sleep(wait_time)
                    continue
                break

    yield f"⚠️ Bhai connection me thoda issue lag raha hai. Ek baar Regenerate daba! (Detail: {last_error})"
