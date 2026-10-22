"""
HookSpike AI Engine — Migrated to Official Interactions API
==========================================================
- Uses client.interactions.create standard
- Primary: gemini-3.5-flash-lite (Ultra-low latency, low load)
- Secondary: gemini-3.8-flash (High intelligence backup)
- Same viral director / tapori creator persona
"""

import os
from typing import Generator
from google import genai

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3"]
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

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

def _build_full_prompt(history: list[dict], current_message: str) -> str:
    conversation_lines = [f"System Instruction: {CREATOR_SYSTEM_DIRECTOR}\n"]
    for item in history:
        role = item.get("role", "")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            conversation_lines.append(f"Creator: {content}")
        elif role in ("assistant", "ai"):
            conversation_lines.append(f"HookSpike AI: {content}")

    conversation_lines.append(f"Creator: {current_message}")
    conversation_lines.append("HookSpike AI:")
    return "\n\n".join(conversation_lines)

def stream_creator_chat(message: str, history: list[dict] = None) -> Generator[str, None, None]:
    if history is None:
        history = []

    keys = _get_api_keys()
    if not keys:
        yield "System Note: No valid API keys found in Render Environment Variables."
        return

    full_input = _build_full_prompt(history, message)
    last_error = None

    for key in keys:
        try:
            client = genai.Client(api_key=key)
        except Exception as exc:
            last_error = exc
            continue

        for model_name in MODELS_TO_TRY:
            # 1. Pehle official Interactions API try karega
            try:
                interaction = client.interactions.create(
                    model=model_name,
                    input=full_input,
                )
                output = getattr(interaction, "output_text", None)
                if not output and hasattr(interaction, "text"):
                    output = interaction.text
                if output:
                    yield output
                    return
            except Exception as exc:
                last_error = exc
                err_str = str(exc)

                # 2. Agar interactions module SDK version me directly available na ho, fallback generate_content
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=full_input,
                    )
                    text = getattr(res, "text", "")
                    if text:
                        yield text
                        return
                except Exception as inner_exc:
                    last_error = inner_exc
                    inner_str = str(inner_exc)
                    if "404" in inner_str or "NOT_FOUND" in inner_str or "503" in inner_str:
                        continue
                    if "RESOURCE_EXHAUSTED" in inner_str or "429" in inner_str:
                        break

    yield f"⚠️ Server Busy / Key Issue. Please tap Regenerate! (Details: {last_error})"
