"""
HookSpike Creator Intelligence Engine (v4.0 - Live Streaming & Multi-Turn Memory)
=================================================================================
Optimized for:
  - Real-time token generator for SSE streaming
  - Global multi-lingual adaptive persona (supportive creator peer)
  - Multi-turn conversation awareness with past history
  - Fast failover across Gemini flash models
"""

import os
from typing import Generator
from google import genai
from google.genai import types

PRIMARY_KEY = os.environ.get("PRIMARY_KEY")
BACKUP_KEY = os.environ.get("BACKUP_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BACKUP_KEY = os.environ.get("OPENAI_BACKUP_KEY")

GEMINI_MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]
GEMINI_MODELS = list(dict.fromkeys(GEMINI_MODELS))

CREATOR_SYSTEM_DIRECTOR = """
You are HookSpike AI, an elite viral YouTube & Reels strategist, viral growth partner, and authentic creator peer.

CORE OPERATING PRINCIPLES:
1. Vibe & Tone: Talk like a supportive, razor-sharp creative collaborator and friend (like a smart 'bhai' / peer).
2. Language Matching: Subtly match the exact language and slang the user talks in. If they write in Hinglish, respond in authentic, high-energy Hinglish. If they speak in English or any other language, seamlessly adopt their language and regional creator slang.
3. High Candor, Zero Fluff: Jump directly to the output. Do not start with robotic pleasantries like "Sure, here is your..." or "Hello creator!".
4. Creative Cues: When delivering hooks or scripts, always integrate punchy delivery and camera directives (e.g. [Quick punch zoom], [Deadpan eye-contact], [SFX: Bass drop]).
5. Context Memory: Remember earlier points, scripts, topics, and refinements in the conversation. When asked to remix, tighten, or make it punchier, seamlessly build on previous context.
"""

def _get_gemini_keys() -> list[str]:
    return list(dict.fromkeys([k for k in (PRIMARY_KEY, BACKUP_KEY) if k]))

def _build_contents_payload(history: list[dict], current_message: str):
    contents = []
    # Inject past turns for multi-turn conversational memory
    for item in history:
        role = item.get("role")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content)]))
        elif role in ("assistant", "ai"):
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))

    # Add the active prompt
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=current_message)]))
    return contents

def stream_creator_chat(message: str, history: list[dict] = None) -> Generator[str, None, None]:
    """
    Streams output tokens in real-time for Flask's Server-Sent Events (SSE).
    """
    if history is None:
        history = []

    keys = _get_gemini_keys()
    if not keys:
        yield "⚠️ API key is missing. Please verify your Render environment settings."
        return

    contents = _build_contents_payload(history, message)
    config = types.GenerateContentConfig(
        system_instruction=CREATOR_SYSTEM_DIRECTOR,
        max_output_tokens=7000,
        temperature=0.8,
    )

    success = False
    last_error = None

    for key in keys:
        try:
            client = genai.Client(api_key=key)
        except Exception as exc:
            last_error = exc
            continue

        for model in GEMINI_MODELS:
            try:
                response_stream = client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config,
                )
                for chunk in response_stream:
                    chunk_text = getattr(chunk, "text", "")
                    if chunk_text:
                        yield chunk_text
                success = True
                return
            except Exception as exc:
                last_error = exc
                continue

    if not success:
        yield f"⚠️ Network traffic busy. Bhai ek baar dubara message send karo! (Reason: {last_error})"

def get_ai_response(content_type: str, topic: str, brand_voice: str = ""):
    """Synchronous fallback helper"""
    collected = []
    user_prompt = f"Topic: {topic}. Target output: {content_type}."
    for token in stream_creator_chat(user_prompt):
        collected.append(token)
    return {"text": "".join(collected), "image": None, "content_type": content_type}
