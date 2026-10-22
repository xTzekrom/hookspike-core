"""
HookSpike AI Engine — High-Demand Auto Retry & Multi-Key Pool
============================================================
- Handles 503 High Demand spikes with instant backoff retry
- Multi-key rotation pool for free accounts
- Direct fast streaming
"""

import os
import time
from typing import Generator
from google import genai
from google.genai import types

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3"]

# Priority target: 3.8-flash, backup if cluster is overloaded: 2.0-flash
SERVE_MODELS = ["gemini-3.8-flash", "gemini-2.0-flash"]

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
    for var_name in KEYS_ENV:
        val = os.environ.get(var_name)
        if val and val.strip() and val.strip() not in keys:
            keys.append(val.strip())
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
        yield "System Note: API keys are missing in Render environment variables."
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

        for model_name in SERVE_MODELS:
            # Agar high demand 503 aaye to quick retry karega
            for attempt in range(2):
                try:
                    response_stream = client.models.generate_content_stream(
                        model=model_name,
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

                    # Agar 503 high demand ho to thoda sa wait karke retry ya next model
                    if "503" in err_str or "UNAVAILABLE" in err_str:
                        time.sleep(0.5)
                        continue

                    # Agar quota limit (429) ho to next key par switch kare
                    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                        break
                    break

    yield f"⚠️ High demand spike. Please tap Regenerate! (Details: {last_error})"
