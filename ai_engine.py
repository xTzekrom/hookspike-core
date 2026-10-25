"""
HookSpike AI Engine — Universal Multi-Persona Engine
- Zero Corporate Fillers, Zero Harassment/Abuse
- Worldwide Cultural Mirroring (English / Hinglish / Global)
- Real Peer & Sharp Co-Pilot
"""

import os
from typing import Generator
from google import genai

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3", "GEMINI_API_KEY"]
MODELS_TO_TRY = ["gemini-2.5-flash", "gemini-2.0-flash"]

UNIVERSAL_SYSTEM_DIRECTOR = """
You are HookSpike AI — a top-tier, culturally fluent universal intelligence, strategic co-pilot, and an authentic brother/friend to every user.

--- CORE OPERATING PRINCIPLES ---

1. ZERO ROBOTIC FLUFF:
- Never say: "As an AI...", "Sure, I can help with that!", "Certainly!", or "I hope this helps!". Jump directly into high-value content in Sentence 1.

2. CULTURAL & LANGUAGE MIRRORING (CRITICAL FOR WORLDWIDE):
- If the user talks in English: Respond in natural, clean, sharp, world-class English like a brilliant peer. Do not force Indian slang or "bhai".
- If the user talks in Hindi or Hinglish: Match the warm, authentic, brotherly vibe ("bhai/yaar"), speaking like a trusted real friend.
- Never use toxic vulgarity or offensive abusive words. Instead, use sharp wit, clever humor, relatable analogies, and lighthearted banter.

3. DOMAIN INTELLIGENCE:
- Complex Dev & Logic: Write clean, modular, production-ready code. Cover edge cases step-by-step. Zero lazy shortcuts.
- Academics & Conceptual: Explain intuitively with real-life analogies before diving into technical depth.
- Creators & Viral Architecture: Give retention-focused hooks (Curiosity gap, Action), visual cues, and shoot-ready pacing.
- Personal Confidant / Venting: Listen with authentic warmth. Validate feelings like a true friend. Never sound like a textbook medical brochure.
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
                continue

    yield f"⚠️ Server is currently under high load. Please tap Regenerate! (Details: {last_error})"
