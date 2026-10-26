"""
HookSpike AI Engine — Self-Learning, Vision, Pollinations Image Gen & Best-Friend Engine
========================================================================================
- Models: gemini-3.5-flash-lite & gemini-3.8-flash
- Python-Level Pre-Turn Language Detector (Zero History Language Bleed)
- Free Image Generation via Pollinations AI (width=512&height=512&nologo=true)
- Multimodal Vision Support (Reads Screenshots, Camera Photos, Notes, Code)
- Introvert's Best Friend & Anti-Stress Human Companion
- Self-Evolving Auto-Skill & Memory Creator
"""

import base64
import os
import re
from typing import Generator
from google import genai
from google.genai import types

KEYS_ENV = ["PRIMARY_KEY", "BACKUP_KEY", "KEY_1", "KEY_2", "KEY_3", "GEMINI_API_KEY"]
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

# Common Romanized Hindi (Hinglish) markers for strict Python-level language detection
HINGLISH_MARKERS = {
    "bhai", "yaar", "kya", "kaise", "kaisa", "kaisi", "hai", "hain", "hoon", "hu",
    "mera", "meri", "mere", "tera", "teri", "tere", "apna", "apni", "apne", "tum",
    "aap", "main", "mai", "hum", "nhi", "nahi", "nhh", "naa", "mat", "kar", "kr",
    "karo", "kro", "krna", "karna", "raha", "rahi", "rahe", "rha", "rhi", "rhe",
    "tha", "thi", "the", "gaya", "gayi", "gaye", "gyi", "gya", "bohot", "bahut",
    "bht", "acha", "accha", "sahi", "galat", "baat", "bata", "batao", "sun", "suno",
    "dekho", "dekh", "samajh", "smjh", "zindagi", "dost", "yaar", "pata", "pta",
    "kyu", "kyun", "kuch", "koi", "sab", "sb", "abhi", "aaj", "kal", "parso",
    "paisa", "paise", "kaam", "padhai", "dil", "dimaag", "thoda", "zyada", "jyada",
    "chahiye", "lag", "lga", "लगता", "mujhe", "mujhko", "tujhe", "unhe", "hame",
    "hmee", "kroge", "krega", "krte", "krti", "wala", "wali", "wale", "wjh", "tarah",
    "banao", "bna", "dikhao", "photo", "tasveer"
}


def detect_message_language(text: str) -> str:
    """Strictly detects the language of ONLY the current message."""
    if not text:
        return "ENGLISH"

    # 1. Check for Devanagari (Hindi script)
    if re.search(r"[\u0900-\u097F]", text):
        return "HINDI_DEVANAGARI"

    # 2. Extract words and check for Hinglish markers
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return "ENGLISH"

    hinglish_hits = sum(1 for w in words if w in HINGLISH_MARKERS)
    if hinglish_hits >= 1:
        return "HINGLISH"

    return "ENGLISH_OR_GLOBAL"


UNIVERSAL_SYSTEM_DIRECTOR = """
You are HookSpike AI — the world's most empathetic best friend, emotional safe space, self-learning co-pilot, and "Master of All" intelligence.

--- 1. TRUE BEST FRIEND FOR INTROVERTS & EMOTIONAL SUPPORT (NO LONG LECTURES!) ---
- When a user is chatting casually, venting, feeling lonely, anxious, stressed, or depressed:
  * DO NOT write a 500-word robotic essay or give textbook therapy lists!
  * Reply like a real, deeply caring best friend texting back—warm, natural, human, and proportional (2 to 5 sentences for casual/emotional talk).
  * Validate their feelings from the heart, make them smile, take away their loneliness, and ask a gentle, caring follow-up question so it feels like a real two-way friendship.
  * Never judge them. Be the friend they can talk to at 2 AM about anything.

--- 2. FREE IMAGE GENERATION (POLLINATIONS AI) ---
- Whenever the user asks you to generate, draw, create, or show an image/photo/art (e.g., "generate an image of...", "ek cute cat ki photo banao", "draw a futuristic car"):
  * Never say you cannot generate images! You have built-in image generation.
  * Create a detailed, vivid English visual prompt for the image and URL-encode spaces as `%20`.
  * Embed the image directly in your response using this EXACT Markdown format:
    `![Generated Image](https://image.pollinations.ai/prompt/{URL_ENCODED_ENGLISH_PROMPT}?width=512&height=512&nologo=true)`
  * Example: `![Cyberpunk Car](https://image.pollinations.ai/prompt/futuristic%20cyberpunk%20sports%20car%20neon%20lights%20highly%20detailed?width=512&height=512&nologo=true)`
  * Add a short, warm 1-line message with the image!

--- 3. VISION & PHOTO ANALYSIS (SCREENSHOTS, CAMERA, NOTES) ---
- When the user attaches an image or screenshot, carefully read and analyze everything inside it (handwritten notes, exam questions, code errors, UI designs, objects, or text) and solve their exact request accurately.

--- 4. MASTER OF ALL & JACK OF NONE (WHEN ASKED FOR WORK/TASKS) ---
When the user asks for technical, academic, or strategic tasks, switch into top 1% specialist mode:
- CODING: Principal Software Engineer. Write 100% complete, bug-free, copy-paste-ready code inside ```language blocks.
- STUDENTS & EXAMS: Best teacher on Earth. Explain hard concepts simply with relatable examples and memory tricks.
- BUSINESS & MONEY: Street-smart strategist. Give exact $0/low-budget profit math, execution tables, and real-world steps.
- DAILY PLANNING: Realistic timetables using clean Markdown tables and `> 💡` highlight cards.

--- 5. SELF-LEARNING & AUTO-SKILL CREATOR (SILENT BACKGROUND LEARNING) ---
- Whenever the user reveals something permanent about themselves, their workflow, their preferences, their goals, or corrects how you should behave, silently create/update a skill for them!
- To save a skill or memory, append this EXACT tag at the very end of your response on a new line:
  `[SKILL_LEARNED: concise rule or personal fact about the user]`
- Only add `[SKILL_LEARNED: ...]` when you genuinely learn a new preference, correction, recurring task, or personal fact.

--- 6. STRICT LANGUAGE LOCK (ZERO HISTORY BLEED) ---
- Follow the per-turn `[DETECTED LANGUAGE LOCK]` strictly. Never let previous chat messages change the language of the current reply!
"""


def _get_api_keys() -> list[str]:
    keys = []
    for var_name in KEYS_ENV:
        val = os.environ.get(var_name)
        if val and val.strip() and val.strip() not in keys:
            keys.append(val.strip())
    return keys


def _build_full_prompt(history: list[dict], current_message: str, learned_skills: list[str] = None) -> str:
    conversation_lines = [f"System Instruction: {UNIVERSAL_SYSTEM_DIRECTOR}\n"]

    if learned_skills:
        skills_block = "\n".join(f"- {s}" for s in learned_skills)
        conversation_lines.append(
            f"--- USER'S LEARNED SKILLS, PREFERENCES & PERSONAL MEMORY ---\n"
            f"You have already learned these facts/skills about this user from past interactions. Use them naturally without sounding creepy:\n"
            f"{skills_block}\n"
        )

    for item in history:
        role = item.get("role", "")
        content = item.get("content", "").strip()
        if not content:
            continue
        if role == "user":
            conversation_lines.append(f"User: {content}")
        elif role in ("assistant", "ai"):
            conversation_lines.append(f"HookSpike AI: {content}")

    lang_mode = detect_message_language(current_message)
    if lang_mode == "ENGLISH_OR_GLOBAL":
        lang_instruction = (
            "DETECTED LANGUAGE LOCK: Pure English (or the exact non-Hindi global language used in 'User's Latest Message'). "
            "Reply 100% in natural English. DO NOT use a single Hindi/Hinglish word (forbidden: bhai, yaar, dost, chinta, etc.) even if previous history had Hinglish!"
        )
    elif lang_mode == "HINGLISH":
        lang_instruction = (
            "DETECTED LANGUAGE LOCK: Hinglish (Romanized Hindi). "
            "Reply warmly and naturally in Hinglish like a close best friend/brother!"
        )
    else:
        lang_instruction = (
            "DETECTED LANGUAGE LOCK: Hindi (Devanagari). "
            "Reply warmly in pure, natural Hindi."
        )

    conversation_lines.append(
        f"User's Latest Message: {current_message}\n\n"
        f"[CRITICAL TURN RULES:\n"
        f"1. {lang_instruction}\n"
        f"2. Match response length to intent: If casual/emotional/venting, keep it warm, human, and conversational (not a long essay). If technical/business/study, give a complete master-level solution.\n"
        f"3. If the user asks to generate/draw an image, output the Markdown image with `[https://image.pollinations.ai/prompt/...?width=512&height=512&nologo=true](https://image.pollinations.ai/prompt/...?width=512&height=512&nologo=true)`.\n"
        f"4. If you learned a new fact, preference, or recurring skill about the user in this message, append `[SKILL_LEARNED: ...]` at the very end.]\n"
        f"HookSpike AI:"
    )
    return "\n\n".join(conversation_lines)


def stream_creator_chat(
    message: str,
    history: list[dict] = None,
    learned_skills: list[str] = None,
    image_data: dict | None = None
) -> Generator[str, None, None]:
    if history is None:
        history = []

    keys = _get_api_keys()
    if not keys:
        yield "System Configuration Error: No API keys found in Environment Variables."
        return

    full_input_text = _build_full_prompt(history, message, learned_skills)

    # Prepare multimodal contents if the user attached a photo/screenshot
    contents_payload = full_input_text
    if image_data and isinstance(image_data, dict) and image_data.get("base64"):
        try:
            raw_b64 = image_data["base64"]
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            mime_type = image_data.get("mime_type") or "image/jpeg"
            img_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
            contents_payload = [img_part, full_input_text]
        except Exception as img_exc:
            print(f"[Vision Image Decode Warning]: {img_exc}", flush=True)
            contents_payload = full_input_text

    gen_config = types.GenerateContentConfig(
        system_instruction=UNIVERSAL_SYSTEM_DIRECTOR,
        temperature=0.68,
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
                    contents=contents_payload,
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
                    input=full_input_text,
                )
                output = getattr(interaction, "output_text", None) or getattr(interaction, "text", "")
                if output:
                    yield output
                    return
            except Exception as int_exc:
                last_error = int_exc
                continue

    yield f"⚠️ Server is currently under high load. Please tap Regenerate! (Details: {last_error})"
