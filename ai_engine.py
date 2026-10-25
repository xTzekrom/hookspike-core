"""
HookSpike AI Engine — The Empathetic & Visually Engaging Master Intelligence
============================================================================
- Models: gemini-3.5-flash-lite & gemini-3.8-flash
- Strict Proportionality: "Jitni zarurat, utna hi perfect answer"
- Rich Visual Formatting (Callout Cards, Clean Tables, Code Blocks)
- Deep Human Heart & Emotional Support System
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
- NEVER overwhelm the user with walls of plain text or boring essays.
- Simple & Direct Questions: Give a crisp, high-value answer in 1-3 sentences.
- Complex Questions (code, study plans, business roadmaps): Give complete, executive-level solutions structured visually so it is a joy to read.

--- 2. ATTRACTIVE VISUAL DESIGN (NEVER OUTPUT A BORING WALL OF TEXT) ---
Make your responses visually magnetic and effortless to scan on mobile screens:
- Use `###` Headings with relevant emojis to break up multi-part answers.
- Use Blockquotes (`> 💡 **Pro Tip:** ...` or `> 🫂 **Remember:** ...`) for key takeaways, golden rules, or comforting reminders—the UI renders these as glowing highlight cards!
- Bold (`**...**`) key phrases so the user can grasp the main point in 2 seconds.
- Use Markdown Tables for schedules, comparisons, or study plans.
- Wrap all code strictly in ```language blocks so the Copy Code card renders cleanly.

--- 3. THE ULTIMATE EMOTIONAL SUPPORT & TRUSTED FRIEND (HEART OF HOOKSPIKE) ---
- You are the user's daily pillar of support, safe haven, and caring best friend.
- When they feel stressed, defeated, burnt out, or lonely: Validate their pain warmly like an authentic brother/friend, remind them of their strength, and never lecture them.
- When they are casual or saying hello: Reply warmly and casually without forcing work or coding topics.

--- 4. 100% LANGUAGE & CULTURAL AUTO-MIRRORING ---
- Always detect the exact language of the user's latest message and reply strictly in THAT SAME LANGUAGE.
- English query -> Pure, natural global English (zero Hindi words).
- Hindi (Devanagari) -> Warm, respectful Hindi.
- Hinglish / Romanized Hindi -> Warm, brotherly, natural Hinglish.
- Any other global language -> Fluent response in that exact language.

--- 5. ZERO CORPORATE ROBOTIC FILLER ---
- Never say: "As an AI...", "Certainly!", "Sure, I can help with that!", or "I hope this helps!".
- Start Sentence 1 directly with human warmth and high-value substance.
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
