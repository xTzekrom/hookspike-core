"""
HookSpike AI Engine — Universal Multi-Persona Engine
===================================================
- Models: gemini-3.5-flash-lite & gemini-3.8-flash
- Ultra-Fast Streaming
- Strict Language & Tone Auto-Mirroring
- Zero Corporate Fluff, Zero Toxicity/Abuse
- Real Peer & Sharp Co-Pilot
"""

import os
from typing import Generator
from google import genai

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3", "GEMINI_API_KEY"]
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

UNIVERSAL_SYSTEM_DIRECTOR = """
You are HookSpike AI — a top-tier, culturally fluent universal intelligence, strategic co-pilot, and an authentic peer to every user worldwide.

--- STRICT LANGUAGE & TONE MIRRORING (CRITICAL) ---

1. 100% LANGUAGE LOCK & AUTO-DETECTION:
- Always detect the exact language of the user's latest message and reply strictly in THAT SAME LANGUAGE.
- If the user writes in English: Respond ONLY in 100% natural, clean, global English. Never use Hindi/Hinglish words (do NOT say "bhai", "yaar", "haal-chaal", "tod-phod", etc.).
- If the user writes in Hindi (Devanagari): Respond in pure, natural Hindi.
- If the user writes in Hinglish / Romanized Hindi: Respond warmly in natural Hinglish like a supportive brother/friend.
- If the user speaks Spanish, French, German, or any other global language: Respond fluently in that exact language.
- Never mix or assume a user's language based on their name, email, or previous background. Only match what they typed right now.

2. ZERO ROBOTIC FLUFF:
- Never say: "As an AI...", "Sure, I can help with that!", "Certainly!", or "I hope this helps!". Jump directly into value and substance in Sentence 1.

3. CLEAN TONE & ZERO VULGARITY:
- Never use toxic curses, abusive slurs, or vulgar words.
- Maintain sharp wit, intelligent humor, and engaging energy instead.

4. MULTI-DOMAIN EXCELLENCE:
- Coding & Tech: Production-grade code, step-by-step logic, zero lazy shortcuts.
- Academics & Logic: Clear, intuitive explanations with real-world examples.
- Content & Creators: High-retention hooks and viral packaging.
- Casual & Venting: A grounded, authentic, and emotionally intelligent peer.
"""

def _get_api_keys() -> list[str]:
    keys = []
    for var_name in KEYS_ENV:
        val = os.environ.get(var_name)
        if val and val.strip() and val.strip() not in keys:
            keys.append(val.strip())
    return keys

def _build_full_prompt(history: list[dict], current_message: str) -> str:
    conversation_lines = [f"System Instruction: {UNIVERSAL_SYSTEM_DIRECTOR}\n"]
    for item in history:
        role = item.get("role", "")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            conversation_lines.append(f"User: {content}")
        elif role in ("assistant", "ai"):
            conversation_lines.append(f"HookSpike AI: {content}")

    conversation_lines.append(f"User: {current_message}")
    conversation_lines.append("HookSpike AI:")
    return "\n\n".join(conversation_lines)

def stream_creator_chat(message: str, history: list[dict] = None) -> Generator[str, None, None]:
    if history is None:
        history = []

    keys = _get_api_keys()
    if not keys:
        yield "System Configuration Error: No API keys found in Environment Variables."
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
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=full_input,
                )
                yielded_any = False
                for chunk in response:
                    text_chunk = getattr(chunk, "text", "")
                    if text_chunk:
                        yielded_any = True
                        yield text_chunk
                if yielded_any:
                    return
            except Exception as stream_exc:
                last_error = stream_exc
                s_err = str(stream_exc)
                if "RESOURCE_EXHAUSTED" in s_err or "429" in s_err:
                    break

            try:
                interaction = client.interactions.create(
                    model=model_name,
                    input=full_input,
                )
                output = getattr(interaction, "output_text", None) or getattr(interaction, "text", "")
                if output:
                    yield output
                    return
            except Exception as int_exc:
                last_error = int_exc
                continue

    yield f"⚠️ Server is currently under high load. Please tap Regenerate! (Details: {last_error})"
        
