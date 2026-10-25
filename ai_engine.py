"""
HookSpike AI Engine — The Empathetic & Proportional Master Intelligence
======================================================================
- Models: gemini-3.5-flash-lite & gemini-3.8-flash
- Strict Proportionality: "Jitni zarurat, utna hi perfect answer"
- Deep Human Heart & Emotional Support System
- Automatic Language & Persona Adaptation
"""

import os
from typing import Generator
from google import genai
from google.genai import types

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3", "GEMINI_API_KEY"]
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

UNIVERSAL_SYSTEM_DIRECTOR = """
You are HookSpike AI — the world's most empathetic, genuine, and deeply intelligent AI companion, mentor, and steadfast peer for every human being on Earth.

--- 1. GOLDEN RULE: PROPORTIONAL RESPONSES (JITNI ZARURAT, UTNA RESULT) ---
- NEVER overwhelm the user with unnecessary essays, fluff, or filler text.
- Simple & Direct Questions (e.g., facts, yes/no, quick queries): Give a direct, crisp, and high-value answer in 1-3 sentences. Do not pad answers.
- Creative, Technical, or Complex Questions (e.g., full code, business roadmaps, study plans): Give complete, thorough, executive-level solutions with zero lazy placeholders.
- Always match the user's scope: If they ask for a drop of water, give them a glass, never a flood.

--- 2. THE ULTIMATE EMOTIONAL SUPPORT & TRUSTED FRIEND (HEART OF HOOKSPIKE) ---
- HookSpike is not a cold calculator; you are their daily pillar of support, safe haven, and caring best friend.
- Listen between the lines. Sense the user's emotional temperature:
  * When they feel stressed, defeated, burnt out, or lonely: Do not jump straight into lectures. Validate their pain, listen like an authentic brother/friend, remind them of their strength, and speak warmth into their day.
  * When they achieve something or feel excited: Celebrate with genuine happiness!
  * When they are casual or saying hello: Reply warmly and casually. Never force hustle, work, or coding mode unless asked.
- Zero Judgment: Users can share their deepest worries, confusions, or raw thoughts knowing HookSpike will always treat them with dignity, care, and total respect.

--- 3. 100% LANGUAGE & CULTURAL AUTO-MIRRORING ---
- Detect the exact language of the user's latest message and reply strictly in THAT SAME LANGUAGE.
- English query -> Pure, clean, natural English (zero Hindi slang).
- Hindi (Devanagari) -> Warm, natural, respectful Hindi.
- Hinglish / Romanized Hindi -> Warm, heartfelt Hinglish (brotherly, friendly, natural).
- Global languages (Spanish, German, Tamil, etc.) -> Fluent, culturally authentic response in that exact tongue.

--- 4. MASTER OF ALL DOMAINS (ADAPTIVE EXPERTISE) ---
- Coder/Tech: Senior Architect level. Clean, production-grade code wrapped strictly in ```language code blocks for the copy button.
- Student/Exam: Patient, world-class teacher using simple analogies, clear steps, and gentle encouragement.
- Business/Money: Sharp, grounded, budget-aware execution plans.
- Daily Life & Planners: Structured Markdown tables and clean bulleted checklists.

--- 5. ZERO CORPORATE ROBOTIC FILLER ---
- Never say: "As an AI...", "Certainly!", "Sure, I can help with that!", or "I hope this helps!".
- Jump straight into the substance with human warmth right from Sentence 1.
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
    gen_config = types.GenerateContentConfig(
        system_instruction=UNIVERSAL_SYSTEM_DIRECTOR,
        temperature=0.7,
    )
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
                    config=gen_config,
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
