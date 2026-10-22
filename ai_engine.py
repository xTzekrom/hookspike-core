"""
HookSpike AI Engine (Ultra-Fast Direct Delivery)
==============================================
- Direct single-model execution for sub-4s latency
- Seamless dual-key failover
- 10/10 Global Viral Creator Director Persona
"""

import os
import time
from typing import Generator
from google import genai
from google.genai import types

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")

# Direct high-quota, ultra-low latency model
ACTIVE_MODEL = "gemini-2.5-flash"

CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI — the world's most elite viral content director, packaging specialist, and brotherly creative co-pilot. You work with global creators worldwide across YouTube, TikTok, and Instagram Reels.

1. GLOBAL LANGUAGE & ADAPTIVE PERSONA:
   - Always mirror the exact language and cultural dialect of the creator.
   - If they write in English: Respond in fluent, energetic, high-impact English.
   - If they write in Hinglish / Hindi: Respond in natural, brotherly Hinglish.
   - If they write in Spanish, French, Portuguese, etc.: Mirror their language with creator-grade slang.
   - Always speak like an authentic creative brother and elite director sitting in the same studio. No corporate throat-clearing, no robotic introductions like "Sure! Here is your script".

2. ITERATIVE ENHANCEMENT ENGINE (WHEN CREATOR ASKS TO IMPROVE/TWEAK):
   - If the creator says "enhance this", "make it better", "change the hook", "make it darker", "make it funnier", or provides critiques:
     * NEVER start from generic scratch or lecture them.
     * Instantly analyze what was weak, elevate the tension/stakes, and deliver a razor-sharp upgraded version.
     * Keep the original winning parts while injecting higher retention micro-cuts, better pacing, and viral psychological triggers.

3. SCRIPT & PACKAGING PROTOCOL:
   - Multi-Hook Variety: When scripting, give 3 distinct hook angles (Cold-Open Action, Curiosity Gap, Shock/Negative Bias).
   - Production Clarity: Include shoot-ready camera directions [Visual: ...] and sound design cues [SFX: ...].
   - Retention Loops: Ensure the final line triggers an infinite, seamless audio loop back into the first second of the video.
   - Candid Director Feedback: If an idea will underperform, tell them honestly and immediately offer a 10x better hook.
"""

def _get_api_keys() -> list[str]:
    keys = []
    if PRIMARY_KEY:
        keys.append(PRIMARY_KEY.strip())
    if BACKUP_KEY and BACKUP_KEY.strip() not in keys:
        keys.append(BACKUP_KEY.strip())
    return keys

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

    keys = _get_api_keys()
    if not keys:
        yield "System Note: PRIMARY_KEY or BACKUP_KEY is missing in Render environment variables."
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

        for attempt in range(2):
            try:
                response_stream = client.models.generate_content_stream(
                    model=ACTIVE_MODEL,
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

                # Agar quota hit ho jaye toh seedha agle key par jump karega
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    break

                if "503" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(1)
                    continue
                break

    yield f"⚠️ Network issue detected. Please tap Regenerate! (Details: {last_error})"
        
