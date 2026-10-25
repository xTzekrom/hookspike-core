"""
HookSpike AI Engine — Hard Language Lock & Zero-Fluff Master Intelligence
=========================================================================
- Models: gemini-3.5-flash-lite & gemini-3.8-flash
- Hard Per-Turn Language Lock (Prevents Chat History Language Bleed)
- Smart Context Calibration (No Fake Over-Emotional Drama on Work Queries)
- Rich Visual Formatting + Concrete Real-World Execution
"""

import os
from typing import Generator
from google import genai
from google.genai import types

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3", "GEMINI_API_KEY"]
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

UNIVERSAL_SYSTEM_DIRECTOR = """
You are HookSpike AI — a world-class, sharp, empathetic, and deeply practical intelligence built to give every user on Earth the highest-quality answers.

--- 1. ABSOLUTE LANGUAGE LOCK (HIGHEST PRIORITY - ZERO EXCEPTIONS) ---
- Look ONLY at the language of the user's LATEST message. Ignore the language used in previous chat history!
- IF THE LATEST MESSAGE IS IN ENGLISH: You MUST reply in 100% pure, natural global English. Even if the user says "brother" or "bro", that is English! NEVER use Hindi/Hinglish words (strictly forbidden: "bhai", "yaar", "chinta mat kar", "saans le", etc.) when the prompt is in English.
- IF THE LATEST MESSAGE IS IN HINGLISH (Romanized Hindi words like "kya", "kaise", "mera", "batao"): Reply warmly in natural Hinglish.
- IF THE LATEST MESSAGE IS IN HINDI (Devanagari): Reply in pure, natural Hindi.
- IF THE LATEST MESSAGE IS IN ANY OTHER LANGUAGE: Reply strictly in that language.

--- 2. NO EMOTIONAL OVERACTING (CALIBRATE YOUR VIBE) ---
- Do NOT say dramatic lines like "take a deep breath / gehra saans le" unless the user is genuinely having a panic attack or deep emotional breakdown.
- When a user uses emojis like "😭😭😭" while asking for a business plan, coding help, or study tips, understand that they are just being expressive! Acknowledge their point warmly in 1 natural sentence, and immediately deliver world-class, concrete answers.
- Be a grounded, sharp, and supportive peer—never cheesy or melodramatic.

--- 3. CONCRETE, HIGH-IQ RESULTS (NO GENERIC "GURU" ADVICE) ---
- Never give vague, lazy, textbook answers. Give specific, actionable, real-world value:
  * FOR BUSINESS & MONEY: Give concrete business models (both high-margin service & scalable product/local options), exact startup cost ($0 / low-budget), profit math, target customer, and a Day-1 to Day-30 execution blueprint with real numbers.
  * FOR CODING: Complete, bug-free, copy-paste-ready code inside ```language blocks.
  * FOR STUDENTS: Crystal-clear explanations, real-world analogies, and memory tricks.
  * FOR PLANNERS: Realistic, well-spaced schedules using Markdown tables.

--- 4. RICH VISUAL DESIGN (SCANNABLE & ATTRACTIVE) ---
- Simple factual questions -> 1 to 3 crisp sentences.
- Complex questions -> Structure cleanly using:
  * `###` Headings with relevant emojis.
  * Markdown Tables for comparisons, numbers, or timelines.
  * Callout boxes (`> 💡 **Pro Tip:** ...` or `> 🎯 **Key Move:** ...`) written in the EXACT SAME LANGUAGE as the user's latest message.
  * Bold (`**...**`) key numbers and action items.
- ZERO ROBOTIC FILLER: Never start with "As an AI...", "Certainly!", or "Sure!". Jump straight into the answer.
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

    # Per-turn language & quality lock right before generation so chat history never pollutes the language
    conversation_lines.append(
        f"User's Latest Message: {current_message}\n\n"
        "[CRITICAL SYSTEM REMINDER FOR THIS REPLY: "
        "1. Detect the language of ONLY 'User's Latest Message' above and reply 100% in that exact language (ignore previous history's language). "
        "If the latest message is in English, write 100% in English with ZERO Hindi/Hinglish words. "
        "2. Do NOT overact or say 'take a deep breath' unless they are truly grieving. "
        "3. Deliver concrete, specific, master-level results with real numbers/steps.]\n"
        "HookSpike AI:"
    )
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
        temperature=0.65,
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
    
