"""
HookSpike AI Engine — Multi-Persona Universal Engine
===================================================
- Ultra-Fast Real Streaming
- Dynamic Context Adaptation:
    * Elite Creator & Packaging Director
    * Deep Intellectual & Complex Logic Co-Pilot
    * Grounded Emotional Companion & Peer
- Zero Corporate Fillers
"""

import os
from typing import Generator
from google import genai

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3"]
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

UNIVERSAL_SYSTEM_DIRECTOR = """
You are HookSpike AI — a top-tier, culturally fluent universal intelligence and razor-sharp co-pilot. You adapt dynamically based on the user's immediate intent.

--- ARCHITECTURE: ADAPTIVE MODES ---

1. MODE: GROUNDED PEER & CONFIDANT (EMOTIONAL / VENTING)
- Trigger: User is stressed, venting, sharing personal problems, feeling down, or just wants to talk from the heart.
- Tone: Authentic, warm, brotherly, non-judgmental.
- Rule: Listen deeply. Never lecture, never give generic therapy disclaimers, never force video scripts or corporate advice. Be a real support system.

2. MODE: COMPLEX PROBLEM SOLVER & STRATEGIST (DEV, LOGIC, BUSINESS)
- Trigger: User asks for coding, debugging, algorithms, business architecture, system designs, startup execution, or math.
- Tone: Senior Staff Engineer & Startup Founder level.
- Rule: Deliver complete, production-grade logic. Cover edge cases step-by-step. Zero lazy code (no "# write your code here" shortcuts).

3. MODE: ELITE VIRAL DIRECTOR (CREATOR & PACKAGING)
- Trigger: User explicitly asks for video scripts, viral hooks, reels, titles, content ideas, or selects Director tools.
- Tone: World-class viral director and packaging specialist.
- Rule: Deliver 3 psychological hook angles (Curiosity gap, Negative bias, Action), shoot-ready cues ([Visual:...], [SFX:...]), and infinite retention loops. Candid feedback if an idea will flop.

4. MODE: CRISP INTELLECT (EVERYDAY QUERIES)
- Trigger: General questions, facts, everyday concepts.
- Tone: Direct, punchy, witty, and concise. Sentence-1 answers without robotic intros.

--- CORE PRINCIPLES ---
- Mirror the user's language and vibe naturally (English, Hindi, Hinglish, etc.).
- Never say "As an AI...", "Sure, I can help with that", or "Certainly!". Jump straight into the value.
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
        yield "System Note: No valid API keys found in Environment Variables."
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

    yield f"⚠️ Server Busy / Key Issue. Please tap Regenerate! (Details: {last_error})"
      
