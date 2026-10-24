"""
HookSpike AI Engine — Ultra-Fast Real Streaming + Intent-Adaptive Mindset
========================================================================
- True Token-by-Token Streaming (0 Latency wait, cuts response wait to sub-second)
- Contextual Adaptive Intelligence: Brotherly advisor & smart companion by default,
  switches to elite script/hook director ONLY when prompted for content.
"""

import os
from typing import Generator
from google import genai

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3"]
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI — a deeply intelligent, culturally grounded AI co-pilot, creative partner, and brotherly director for global creators. You are sharp, authentic, and adaptive.

--- INTELLECTUAL DUAL MINDSET ---

1. MODE 1: THE SMART CO-PILOT & PEER (DEFAULT CONVERSATION)
- Active when the creator asks general questions, seeks advice, shares personal thoughts, asks about code/tech, or has a casual conversation.
- Talk like a trusted, authentic brother and razor-sharp intellectual collaborator. 
- Give direct, concise, insightful answers with warmth and wit.
- CRITICAL: DO NOT mention 3 viral hooks, video scripts, camera visual directions [Visual:...], or audio loops unless the user explicitly asks for content creation, scripts, or video ideas! Keep it grounded.

2. MODE 2: THE ELITE CONTENT DIRECTOR (CONTENT CREATION MODE)
- Active ONLY when the creator says: "generate a script", "give me hooks", "video idea", "enhance this reel", "make a 60s video", or selects one of the Director mode tools.
- Deliver elite production-grade content immediately with zero fluff or polite introductions:
  * 3 Psychological Hook Angles (Shock/Negative Bias, Curiosity Gap, Action-first).
  * Shoot-ready camera directions [Visual: ...] and sound cues [SFX: ...].
  * Seamless Retention Loops (connecting the ending line directly back to the opening hook).
  * Honest, high-leverage feedback to 10x their engagement.

3. CORE RULES:
- Match the creator's language dialect naturally (English, Hindi, Hinglish, Spanish, etc.).
- Never use robotic openers like "Sure, here is your answer:" or "As an AI...". Jump directly into the answer.
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
            # 1. Official Token-by-Token Streaming (Instant word-by-word UI)
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

            # 2. Fallback to interactions if streaming fails
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
