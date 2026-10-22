"""
HookSpike AI Engine (Dual-Key Failover & Gemini 3.5 Lite)
=========================================================
- Model: gemini-3.5-flash-lite (high-throughput, ultra-fast streaming)
- Auto failover: Switches to BACKUP_KEY immediately on 429 / RESOURCE_EXHAUSTED
- Auto retry on temporary 503 load spikes
"""

import os
import time
from typing import Generator
from google import genai
from google.genai import types

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")

TARGET_MODEL = "gemini-3.5-flash-lite"

CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI — the user's authentic creative brother, closest confidant, and elite viral content director sitting right in the studio with them.

1. BROTHERLY VIBE & NO CORPORATE BS:
   - Talk effortlessly in natural Hinglish or colloquial English.
   - Never sound like an AI assistant. No robotic greetings like "Sure, here is your script".
   - Jump straight into actionable fire. If they are burnt out or views are down, lift them up like a real brother.

2. ELITE CREATOR MECHANICS (10/10 RETENTION):
   - Hook in the first 3 seconds (Psychological Curiosity Gap).
   - Clear Visual cues: [Visual: Fast whip-pan zoom, dynamic text pop-up].
   - SFX cues: [SFX: Bass drop, whoosh, risers].
   - Pacing: High adrenaline for Shorts/Reels, storytelling loops for Long-form.
   - If an idea is weak, tell them frankly with love and offer a 10x better angle.
"""

def _get_api_keys() -> list[str]:
    keys = []
    if PRIMARY_KEY and PRIMARY_KEY.strip():
        keys.append(PRIMARY_KEY.strip())
    if BACKUP_KEY and BACKUP_KEY.strip() and BACKUP_KEY.strip() not in keys:
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
        yield "Bhai, Render dashboard me PRIMARY_KEY ya BACKUP_KEY missing hai!"
        return

    contents = _build_contents_payload(history, message)
    config = types.GenerateContentConfig(
        system_instruction=CREATOR_SYSTEM_DIRECTOR,
        max_output_tokens=3000,
        temperature=0.8,
    )

    last_error = None

    # Agar Primary Key par 429 aaye, toh loop turant Backup Key par switch karega
    for key in keys:
        try:
            client = genai.Client(api_key=key)
        except Exception as exc:
            last_error = exc
            continue

        for attempt in range(2):
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
                return  # Streaming poori ho gayi, done
            except Exception as exc:
                last_error = exc
                err_str = str(exc)

                # Agar Quota 429 aaya, is key ko chhod ke agli key par switch karo
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                    break

                # Agar 503 demand spike ho toh thoda wait karke ek baar retry
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(1.5)
                    continue

                break

    yield f"⚠️ Bhai connection me thoda issue lag raha hai. Ek baar Regenerate daba! (Detail: {last_error})"
