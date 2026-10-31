"""
HookSpike AI - Production Backend (Admin Bypass + World Clock + WebSocket Pipeline + Built-in PWA Builder Support)
"""

import base64
import json
import os
import random
import re
import sqlite3
import uuid
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
    send_from_directory,
    make_response,
)
from flask_socketio import SocketIO, emit
from supabase import create_client, Client
import ai_engine

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hookspike_vault_2026_secured")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_PERMANENT"] = True

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY).strip()

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[DB Status]: Supabase client initialized!", flush=True)
    except Exception as exc:
        print(f"[Supabase Init Warning]: {exc}", flush=True)

SESSION_MESSAGE_LIMIT = 9
LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hookspike_history.db")

VOICE_GREETINGS = [
    "Yay, you called! Tell me everything, what's on your mind right now?",
    "Hey you! I'm so happy to hear your voice, how is your day going?",
    "Hi! Perfect timing, I was just waiting for you—what are we talking about today?",
    "Hey there! You've got my full attention, tell me what's happening!",
    "Hello! So good to connect with you, how are you feeling right now?",
    "Hi bestie! Ready when you are, what's sparking your thoughts today?",
    "Hey! Take a cozy breath and tell me what's going on in your world!",
    "Yay, we're live! Tell me what we're diving into today!"
]

ACTIVE_STREAM_FLAGS: dict[str, bool] = {}

# Built-in PWA Manifest & Service Worker (No extra files needed!)
PWA_MANIFEST_DATA = {
    "background_color": "#0d0f12",
    "dir": "ltr",
    "display": "standalone",
    "name": "HookSpike",
    "orientation": "any",
    "scope": "/",
    "short_name": "HookSpike",
    "start_url": "https://hookspike-core.onrender.com/",
    "theme_color": "#0d0f12",
    "id": "https://hookspike-core.onrender.com/",
    "description": "Universal cross-platform AI companion with floating HUD, voice pipeline, and multi-domain mastery",
    "lang": "en",
    "icons": [
        {
            "src": "https://hookspike-core.onrender.com/logo.png",
            "type": "image/png",
            "sizes": "192x192",
            "purpose": "any"
        },
        {
            "src": "https://hookspike-core.onrender.com/logo.png",
            "type": "image/png",
            "sizes": "512x512",
            "purpose": "any maskable"
        },
        {
            "src": "https://hookspike-core.onrender.com/logo.png",
            "type": "image/png",
            "sizes": "32x32",
            "purpose": "any"
        },
        {
            "src": "https://hookspike-core.onrender.com/favicon.ico",
            "type": "image/x-icon",
            "sizes": "512x512"
        }
    ]
}

PWA_SW_JS = """
const CACHE_NAME = 'hookspike-pwa-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/manifest.json',
  '/logo.png',
  '/favicon.ico'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.map((key) => key !== CACHE_NAME ? caches.delete(key) : null)
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
"""


def clean_text_for_speech(raw_text: str) -> str:
    clean_speech = re.sub(r"```[\s\S]*?```", " ", raw_text or "")
    clean_speech = re.sub(r"!\[.*?\]\(.*?\)", " ", clean_speech)
    clean_speech = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", clean_speech)
    clean_speech = re.sub(r"[*#_~`>|]", " ", clean_speech)
    clean_speech = re.sub(r"\s+", " ", clean_speech).strip()
    return clean_speech


def init_local_db():
    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_email TEXT,
                    title TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT,
                    skill_rule TEXT,
                    created_at TEXT,
                    UNIQUE(user_email, skill_rule)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bug_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT,
                    description TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
    except Exception as e:
        print(f"[Local DB Init Warning]: {e}", flush=True)


init_local_db()


def get_request_jwt(req_data: dict | None = None) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        tok = auth_header.split(" ", 1)[1].strip()
        if tok and tok not in ("undefined", "null"):
            return tok
    if req_data and req_data.get("access_token"):
        tok = str(req_data.get("access_token")).strip()
        if tok and tok not in ("undefined", "null"):
            return tok
    return session.get("access_token", "")


def sb_headers(user_jwt: str = "") -> dict:
    master_key = SUPABASE_SERVICE_KEY if SUPABASE_SERVICE_KEY else SUPABASE_KEY
    return {
        "apikey": master_key,
        "Authorization": f"Bearer {master_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def db_get_user_skills(user_email: str, user_jwt: str = "") -> list[str]:
    if not user_email:
        return []
    skills = []
    try:
        encoded_email = urllib.parse.quote(user_email)
        url = f"{SUPABASE_URL}/rest/v1/user_skills?user_email=eq.{encoded_email}&select=skill_rule&order=created_at.desc&limit=25"
        req = urllib.request.Request(url, headers=sb_headers(user_jwt), method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                skills = [row["skill_rule"] for row in data if row.get("skill_rule")]
    except Exception:
        pass

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            cur = conn.execute(
                "SELECT skill_rule FROM user_skills WHERE user_email = ? ORDER BY id DESC LIMIT 25",
                (user_email,)
            )
            for row in cur.fetchall():
                if row[0] and row[0] not in skills:
                    skills.append(row[0])
    except Exception:
        pass

    return skills[:25]


def db_save_user_skill(user_email: str, skill_rule: str, user_jwt: str = ""):
    if not user_email or not skill_rule:
        return
    skill_rule = skill_rule.strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO user_skills (user_email, skill_rule, created_at) VALUES (?, ?, ?)",
                (user_email, skill_rule, now_iso)
            )
            conn.commit()
    except Exception:
        pass

    try:
        url = f"{SUPABASE_URL}/rest/v1/user_skills"
        body = json.dumps({
            "user_email": user_email,
            "skill_rule": skill_rule
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(user_jwt), method="POST")
        with urllib.request.urlopen(req, timeout=4) as resp:
            resp.read()
    except Exception:
        pass


def db_select_sessions(user_email: str, user_jwt: str = "") -> list:
    encoded_email = urllib.parse.quote(user_email)
    encoded_del = urllib.parse.quote("[Deleted]")
    url = (
        f"{SUPABASE_URL}/rest/v1/chat_sessions"
        f"?user_email=eq.{encoded_email}&title=neq.{encoded_del}"
        f"&select=id,title,created_at&order=created_at.desc&limit=50"
    )
    
    try:
        req = urllib.request.Request(url, headers=sb_headers(user_jwt), method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                return [row for row in data if row.get("title") != "[Deleted]"]
    except Exception as e:
        print(f"[Supabase Select Sessions Error]: {e}", flush=True)

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, title, created_at FROM chat_sessions WHERE user_email = ? AND title != '[Deleted]' ORDER BY created_at DESC LIMIT 50",
                (user_email,)
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


def db_soft_delete_session(session_id: str, user_email: str, user_jwt: str = "") -> bool:
    encoded_sess = urllib.parse.quote(str(session_id))
    encoded_email = urllib.parse.quote(user_email)

    try:
        url = f"{SUPABASE_URL}/rest/v1/chat_sessions?id=eq.{encoded_sess}&user_email=eq.{encoded_email}"
        body = json.dumps({"title": "[Deleted]"}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(user_jwt), method="PATCH")
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
    except Exception as e:
        print(f"[Supabase Soft-Delete Warning]: {e}", flush=True)

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.execute(
                "UPDATE chat_sessions SET title = '[Deleted]' WHERE id = ? AND user_email = ?",
                (str(session_id), user_email)
            )
            conn.commit()
    except Exception as e:
        print(f"[Local SQLite Soft-Delete Warning]: {e}", flush=True)

    return True


def db_select_messages(session_id: str, user_email: str, user_jwt: str = "") -> list:
    encoded_sess = urllib.parse.quote(str(session_id))
    encoded_email = urllib.parse.quote(user_email)

    try:
        own_url = f"{SUPABASE_URL}/rest/v1/chat_sessions?id=eq.{encoded_sess}&user_email=eq.{encoded_email}&select=id"
        req_own = urllib.request.Request(own_url, headers=sb_headers(user_jwt), method="GET")
        with urllib.request.urlopen(req_own, timeout=8) as resp_own:
            own_data = json.loads(resp_own.read().decode("utf-8"))
            if isinstance(own_data, list) and len(own_data) > 0:
                msg_url = f"{SUPABASE_URL}/rest/v1/chat_messages?session_id=eq.{encoded_sess}&select=role,content,created_at&order=created_at.asc"
                req_msg = urllib.request.Request(msg_url, headers=sb_headers(user_jwt), method="GET")
                with urllib.request.urlopen(req_msg, timeout=8) as resp_msg:
                    msg_data = json.loads(resp_msg.read().decode("utf-8"))
                    if isinstance(msg_data, list):
                        return msg_data
    except Exception as e:
        print(f"[Supabase Select Messages Error]: {e}", flush=True)

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            own = conn.execute(
                "SELECT id FROM chat_sessions WHERE id = ? AND user_email = ?",
                (str(session_id), user_email)
            ).fetchone()
            if not own:
                return []
            cur = conn.execute(
                "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
                (str(session_id),)
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


def db_create_session(user_email: str, title: str, user_jwt: str = "") -> str:
    now_iso = datetime.now(timezone.utc).isoformat()
    session_id = str(uuid.uuid4())

    try:
        url = f"{SUPABASE_URL}/rest/v1/chat_sessions"
        body = json.dumps({"user_email": user_email, "title": title}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(user_jwt), method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            res_text = resp.read().decode("utf-8")
            data = json.loads(res_text) if res_text.strip() else []
            rows = data if isinstance(data, list) else [data]
            if rows and rows[0].get("id"):
                session_id = str(rows[0].get("id"))
    except Exception as e:
        print(f"[Supabase Session Insert Error]: {e}", flush=True)

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO chat_sessions (id, user_email, title, created_at) VALUES (?, ?, ?, ?)",
                (session_id, user_email, title, now_iso)
            )
            conn.commit()
    except Exception:
        pass

    return session_id


def db_create_message(session_id: str, role: str, content: str, user_jwt: str = ""):
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        url = f"{SUPABASE_URL}/rest/v1/chat_messages"
        body = json.dumps({
            "session_id": session_id,
            "role": role,
            "content": content
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(user_jwt), method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()
    except Exception as e:
        print(f"[Supabase Message Insert Error]: {e}", flush=True)

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (str(session_id), role, content, now_iso)
            )
            conn.commit()
    except Exception:
        pass


def verify_and_get_email(req_data: dict | None = None) -> str:
    token = get_request_jwt(req_data)
    if token:
        session["access_token"] = token

    if req_data:
        raw = (req_data.get("user_email") or req_data.get("email") or "").strip().lower()
        if raw and "@" in raw:
            session["user_email"] = raw
            session.modified = True
            return raw

    arg = (request.args.get("user_email") or request.args.get("email") or "").strip().lower()
    if arg and "@" in arg:
        session["user_email"] = arg
        session.modified = True
        return arg

    sess = (session.get("user_email") or "").strip().lower()
    if sess and "@" in sess:
        return sess

    if token and supabase:
        try:
            user_res = supabase.auth.get_user(token)
            if user_res and user_res.user and user_res.user.email:
                verified = user_res.user.email.strip().lower()
                session["user_email"] = verified
                session.modified = True
                return verified
        except Exception:
            pass

    return ""


def check_session_memory_limit(session_id: str, user_email: str, user_jwt: str = "") -> tuple[bool, str]:
    if not session_id:
        return False, ""
    msgs = db_select_messages(session_id, user_email, user_jwt)
    if len(msgs) < SESSION_MESSAGE_LIMIT:
        return False, ""

    return True, "⚡ This chat session has reached its active memory limit. Please start a New Chat to continue."


@app.route("/ping")
def keep_alive_ping():
    return "ok", 200


@app.route("/manifest.json")
def serve_manifest():
    if os.path.exists("manifest.json"):
        return send_from_directory(".", "manifest.json", mimetype="application/manifest+json")
    return Response(json.dumps(PWA_MANIFEST_DATA), mimetype="application/manifest+json")


@app.route("/sw.js")
def serve_service_worker():
    if os.path.exists("sw.js"):
        resp = make_response(send_from_directory(".", "sw.js", mimetype="application/javascript"))
    else:
        resp = make_response(Response(PWA_SW_JS, mimetype="application/javascript"))
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/")
def index():
    if request.args.get("logged_out") == "1":
        session.clear()
    user_email = (session.get("user_email") or "").strip().lower()
    logged_in = bool(user_email)
    return render_template(
        "index.html",
        logged_in=logged_in,
        user_email=user_email,
        supabase_url=SUPABASE_URL or "",
        supabase_key=SUPABASE_KEY or ""
    )


@app.route("/api/auth/sync", methods=["POST"])
def auth_sync():
    data = request.get_json(silent=True) or {}
    email = verify_and_get_email(data)
    if email and "@" in email:
        session["user_email"] = email
        session.modified = True
        return jsonify({"ok": True, "email": email, "is_admin": ai_engine.is_user_admin(email)})
    return jsonify({"error": "Invalid auth credentials"}), 400


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    resp = make_response(redirect("/?logged_out=1"))
    resp.delete_cookie(app.config.get("SESSION_COOKIE_NAME", "session"))
    return resp


@app.route("/logo.png")
def serve_logo():
    return send_from_directory(".", "logo.png", mimetype="image/png")


@app.route("/favicon.ico")
def serve_favicon():
    return send_from_directory(".", "logo.png", mimetype="image/png")


@app.route("/api/user-skills", methods=["GET"])
def get_user_skills_route():
    user_email = verify_and_get_email()
    if not user_email:
        return jsonify([])
    user_jwt = get_request_jwt()
    return jsonify(db_get_user_skills(user_email, user_jwt))


@app.route("/api/report-bug", methods=["POST"])
def report_bug_route():
    data = request.get_json(silent=True) or {}
    email = verify_and_get_email(data) or data.get("email", "guest")
    desc = (data.get("description") or "").strip()
    if not desc:
        return jsonify({"error": "Empty description"}), 400
    now_iso = datetime.now(timezone.utc).isoformat()
    user_jwt = get_request_jwt(data)

    try:
        with sqlite3.connect(LOCAL_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO bug_reports (user_email, description, created_at) VALUES (?, ?, ?)",
                (email, desc, now_iso)
            )
            conn.commit()
    except Exception:
        pass

    try:
        url = f"{SUPABASE_URL}/rest/v1/bug_reports"
        body = json.dumps({"user_email": email, "description": desc}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(user_jwt), method="POST")
        with urllib.request.urlopen(req, timeout=4) as resp:
            resp.read()
    except Exception:
        pass

    return jsonify({"ok": True})


@app.route("/api/chat-session/<session_id>", methods=["DELETE", "POST", "PATCH"])
def delete_chat_session(session_id):
    data = request.get_json(silent=True) or {}
    user_email = verify_and_get_email(data)
    if not user_email or not session_id:
        return jsonify({"error": "Unauthorized"}), 401

    user_jwt = get_request_jwt(data)
    db_soft_delete_session(session_id, user_email, user_jwt)
    return jsonify({"ok": True, "status": "soft_deleted", "session_id": session_id})


@app.route("/api/chat-sessions", methods=["GET"])
def get_chat_sessions():
    user_email = verify_and_get_email()
    if not user_email:
        return jsonify([])

    user_jwt = get_request_jwt()
    sessions = db_select_sessions(user_email, user_jwt)
    return jsonify(sessions)


@app.route("/api/chat-messages/<session_id>", methods=["GET"])
def get_chat_messages(session_id):
    user_email = verify_and_get_email()
    if not user_email or not session_id:
        return jsonify([])

    user_jwt = get_request_jwt()
    messages = db_select_messages(session_id, user_email, user_jwt)
    return jsonify(messages)


@app.route("/api/chat-stream", methods=["POST"])
def chat_stream():
    payload = request.get_json(silent=True) or {}
    user_email = verify_and_get_email(payload)
    user_jwt = get_request_jwt(payload)

    message = payload.get("message", "").strip()
    display_message = payload.get("display_message", message).strip()
    image_data = payload.get("image_data")
    history = payload.get("history", [])
    session_id = payload.get("session_id")
    voice_mode = bool(payload.get("voice_mode", False))
    user_timezone = payload.get("user_timezone")
    user_local_time = payload.get("user_local_time")
    user_local_hour = payload.get("user_local_hour")

    # FREEMIUM & ADMIN BYPASS CHECK FOR VOICE / HUD / ADVANCED FEATURES
    if voice_mode and not ai_engine.is_user_admin(user_email):
        return jsonify({"error": "Voice Mode requires HookSpike Plus subscription.", "requires_payment": True}), 403

    if not message and not image_data:
        return jsonify({"error": "Empty message"}), 400

    if not message and image_data:
        message = "Please analyze this image and explain what you see."
        display_message = "[Photo Attached]"

    if user_email and session_id and not voice_mode:
        is_limited, limit_msg = check_session_memory_limit(session_id, user_email, user_jwt)
        if is_limited:
            return jsonify({"error": limit_msg, "memory_full": True}), 429

    target_email = str(user_email)
    target_jwt = str(user_jwt)
    initial_sess_id = session_id
    learned_skills = db_get_user_skills(target_email, target_jwt) if target_email else []

    def generate_sse():
        accumulated_reply = ""
        active_sess_id = initial_sess_id
        pending_buffer = ""

        try:
            for chunk in ai_engine.stream_creator_chat(
                message,
                history,
                learned_skills,
                image_data,
                voice_mode=voice_mode,
                user_email=target_email,
                user_timezone=user_timezone,
                user_local_time=user_local_time,
                user_local_hour=user_local_hour
            ):
                if chunk:
                    pending_buffer += chunk
                    if not re.search(r"\[(?:SKILL|MISTAKE)", pending_buffer) and not pending_buffer.endswith("["):
                        accumulated_reply += pending_buffer
                        yield f"data: {json.dumps({'token': pending_buffer, 'session_id': active_sess_id})}\n\n"
                        pending_buffer = ""

            if pending_buffer:
                skill_matches = re.findall(r"\[(?:SKILL_LEARNED|MISTAKE_CORRECTED):\s*(.*?)\]", pending_buffer, flags=re.DOTALL)
                for skill_text in skill_matches:
                    if target_email and skill_text.strip():
                        db_save_user_skill(target_email, skill_text.strip(), target_jwt)

                clean_tail = re.sub(r"\[(?:SKILL_LEARNED|MISTAKE_CORRECTED):\s*.*?\]", "", pending_buffer, flags=re.DOTALL).rstrip()
                if clean_tail:
                    accumulated_reply += clean_tail
                    yield f"data: {json.dumps({'token': clean_tail, 'session_id': active_sess_id})}\n\n"

            if accumulated_reply.strip() and target_email and not voice_mode:
                if not active_sess_id:
                    title_text = (display_message[:30] + "...") if len(display_message) > 30 else display_message
                    active_sess_id = db_create_session(target_email, title_text, target_jwt)

                if active_sess_id:
                    db_create_message(active_sess_id, "user", display_message, target_jwt)
                    db_create_message(active_sess_id, "assistant", accumulated_reply.strip(), target_jwt)
                    yield f"data: {json.dumps({'session_id': active_sess_id})}\n\n"

            yield "data: [DONE]\n\n"
        except GeneratorExit:
            pass
        except Exception as exc:
            print(f"[Stream Error]: {exc}", flush=True)
            yield f"data: {json.dumps({'token': f'Connection issue: {exc}', 'session_id': active_sess_id})}\n\n"
            yield "data: [DONE]\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    }

    return Response(stream_with_context(generate_sse()), headers=headers)


@app.route("/api/voice-tts", methods=["POST"])
def voice_tts_endpoint():
    user_email = verify_and_get_email()
    if not ai_engine.is_user_admin(user_email):
        return jsonify({"error": "Voice TTS requires subscription.", "requires_payment": True}), 403

    data = request.get_json(silent=True) or {}
    raw_text = (data.get("text") or "").strip()

    if not raw_text:
        return jsonify({"error": "Empty text"}), 400

    clean_speech = clean_text_for_speech(raw_text)
    if not clean_speech:
        clean_speech = "I'm right here with you, tell me what's on your mind!"

    try:
        audio_bytes = ai_engine.generate_elevenlabs_voice_audio(clean_speech)
        if not audio_bytes:
            return jsonify({"error": "Failed to fetch ElevenLabs audio."}), 502

        return Response(
            audio_bytes,
            mimetype="audio/mpeg",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": "inline; filename=hookspike_voice.mp3"
            }
        )
    except Exception as e:
        print(f"[Voice Route Error]: {e}", flush=True)
        return jsonify({"error": str(e)}), 500


# =====================================================================
# REAL-TIME WEBSOCKET PIPELINE (ADMIN BYPASS + WORLD CLOCK + VOICE)
# =====================================================================
@socketio.on("start_voice_call")
def handle_start_voice_call(data=None):
    sid = request.sid
    user_email = verify_and_get_email()
    if not ai_engine.is_user_admin(user_email):
        socketio.emit("ai_error", {"error": "Voice mode requires subscription.", "requires_payment": True}, to=sid)
        socketio.sleep(0)
        return

    ACTIVE_STREAM_FLAGS[sid] = True

    greeting_text = random.choice(VOICE_GREETINGS)
    emit("ai_voice_greeting", {"text": greeting_text})
    socketio.sleep(0)

    def _stream_greeting_audio(target_sid: str, text_to_speak: str):
        if not ACTIVE_STREAM_FLAGS.get(target_sid, False):
            return
        audio_bytes = ai_engine.generate_elevenlabs_voice_audio(text_to_speak)
        if audio_bytes and ACTIVE_STREAM_FLAGS.get(target_sid, False):
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            socketio.emit(
                "ai_voice_audio",
                {
                    "text": text_to_speak,
                    "audio_base64": audio_b64
                },
                to=target_sid
            )
            socketio.sleep(0)
        else:
            socketio.emit("ai_voice_unlock", {"unlock": True}, to=target_sid)
            socketio.sleep(0)

    socketio.start_background_task(_stream_greeting_audio, sid, greeting_text)


@socketio.on("user_interrupted")
def handle_user_interrupted(data=None):
    sid = request.sid
    ACTIVE_STREAM_FLAGS[sid] = False

    user_email = (session.get("user_email") or "").strip().lower()
    if not user_email and isinstance(data, dict):
        user_email = (data.get("user_email") or data.get("email") or "").strip().lower()
    if user_email:
        ACTIVE_STREAM_FLAGS[user_email] = False

    emit("ai_stream_aborted", {"aborted": True})
    socketio.sleep(0)


@socketio.on("proactive_nudge")
def handle_proactive_nudge(data=None):
    payload = data if isinstance(data, dict) else {}
    sid = request.sid
    is_voice = bool(payload.get("is_voice", False))
    history = payload.get("history", [])
    user_timezone = payload.get("user_timezone")
    user_local_time = payload.get("user_local_time")
    user_local_hour = payload.get("user_local_hour")

    if not history:
        return

    ACTIVE_STREAM_FLAGS[sid] = True

    def _run_nudge(target_sid: str, hist: list, voice_flag: bool, tz: str | None, ltime: str | None, lhour: int | None):
        if not ACTIVE_STREAM_FLAGS.get(target_sid, False):
            return
        nudge_reply = ""
        try:
            for piece in ai_engine.stream_creator_chat(
                message="__PROACTIVE_GENTLE_NUDGE__",
                history=hist[-4:],
                learned_skills=[],
                image_data=None,
                voice_mode=voice_flag,
                user_email=None,
                user_timezone=tz,
                user_local_time=ltime,
                user_local_hour=lhour
            ):
                if not ACTIVE_STREAM_FLAGS.get(target_sid, False):
                    return
                if piece:
                    nudge_reply += piece

            clean_nudge = re.sub(r"\[(?:SKILL_LEARNED|MISTAKE_CORRECTED):.*?\]", "", nudge_reply, flags=re.DOTALL).strip()
            if not clean_nudge or not ACTIVE_STREAM_FLAGS.get(target_sid, False):
                return

            if voice_flag:
                socketio.emit("ai_voice_greeting", {"text": clean_nudge}, to=target_sid)
                socketio.sleep(0)
                speech_text = clean_text_for_speech(clean_nudge)
                audio_bytes = ai_engine.generate_elevenlabs_voice_audio(speech_text)
                if audio_bytes and ACTIVE_STREAM_FLAGS.get(target_sid, False):
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                    socketio.emit(
                        "ai_voice_audio",
                        {"text": clean_nudge, "audio_base64": audio_b64},
                        to=target_sid
                    )
                    socketio.sleep(0)
            else:
                socketio.emit("ai_proactive_message", {"text": clean_nudge}, to=target_sid)
                socketio.sleep(0)
        except Exception as e:
            print(f"[Proactive Nudge Warning]: {e}", flush=True)

    socketio.start_background_task(
        _run_nudge,
        sid,
        history,
        is_voice,
        user_timezone,
        user_local_time,
        user_local_hour
    )


@socketio.on("send_message")
def handle_socket_send_message(data):
    payload = data if isinstance(data, dict) else {}
    sid = request.sid

    message = (payload.get("message") or "").strip()
    display_message = (payload.get("display_message") or message).strip()
    is_voice = bool(payload.get("is_voice", payload.get("voice_mode", False)))
    history = payload.get("history", [])
    image_data = payload.get("image_data")
    session_id = payload.get("session_id")
    user_timezone = payload.get("user_timezone")
    user_local_time = payload.get("user_local_time")
    user_local_hour = payload.get("user_local_hour")

    user_email = (
        session.get("user_email")
        or payload.get("user_email")
        or payload.get("email")
        or ""
    ).strip().lower()
    user_jwt = session.get("access_token") or payload.get("access_token") or ""

    if is_voice and not ai_engine.is_user_admin(user_email):
        socketio.emit("ai_error", {"error": "Voice mode requires subscription.", "requires_payment": True}, to=sid)
        socketio.sleep(0)
        return

    if not message and not image_data:
        emit("ai_error", {"error": "Empty message"})
        return

    if not message and image_data:
        message = "Please analyze this image and explain what you see."
        display_message = "[Photo Attached]"

    ACTIVE_STREAM_FLAGS[sid] = True
    if user_email:
        ACTIVE_STREAM_FLAGS[user_email] = True

    learned_skills = db_get_user_skills(user_email, user_jwt) if (user_email and not is_voice) else []

    def _run_realtime_stream(
        target_sid: str,
        target_email: str,
        target_jwt: str,
        msg: str,
        disp_msg: str,
        hist: list,
        skills: list,
        img: dict | None,
        voice_flag: bool,
        sess_id: str | None,
        tz: str | None,
        ltime: str | None,
        lhour: int | None
    ):
        accumulated_reply = ""
        pending_buffer = ""
        active_sess_id = sess_id

        def is_still_active() -> bool:
            if not ACTIVE_STREAM_FLAGS.get(target_sid, False):
                return False
            if target_email and not ACTIVE_STREAM_FLAGS.get(target_email, True):
                return False
            return True

        try:
            for chunk in ai_engine.stream_creator_chat(
                message=msg,
                history=hist,
                learned_skills=skills,
                image_data=img,
                voice_mode=voice_flag,
                user_email=target_email,
                user_timezone=tz,
                user_local_time=ltime,
                user_local_hour=lhour
            ):
                if not is_still_active():
                    socketio.emit("ai_stream_aborted", {"aborted": True}, to=target_sid)
                    socketio.sleep(0)
                    return

                if chunk:
                    pending_buffer += chunk
                    if not re.search(r"\[(?:SKILL|MISTAKE)", pending_buffer) and not pending_buffer.endswith("["):
                        accumulated_reply += pending_buffer
                        socketio.emit(
                            "ai_chunk",
                            {"chunk": pending_buffer, "session_id": active_sess_id},
                            to=target_sid
                        )
                        socketio.sleep(0)
                        pending_buffer = ""

            if not is_still_active():
                socketio.emit("ai_stream_aborted", {"aborted": True}, to=target_sid)
                socketio.sleep(0)
                return

            if pending_buffer:
                skill_matches = re.findall(
                    r"\[(?:SKILL_LEARNED|MISTAKE_CORRECTED):\s*(.*?)\]",
                    pending_buffer,
                    flags=re.DOTALL
                )
                for skill_text in skill_matches:
                    if target_email and skill_text.strip() and not voice_flag:
                        db_save_user_skill(target_email, skill_text.strip(), target_jwt)

                clean_tail = re.sub(
                    r"\[(?:SKILL_LEARNED|MISTAKE_CORRECTED):\s*.*?\]",
                    "",
                    pending_buffer,
                    flags=re.DOTALL
                ).rstrip()
                if clean_tail:
                    accumulated_reply += clean_tail
                    socketio.emit(
                        "ai_chunk",
                        {"chunk": clean_tail, "session_id": active_sess_id},
                        to=target_sid
                    )
                    socketio.sleep(0)

            if voice_flag and is_still_active():
                clean_speech = clean_text_for_speech(accumulated_reply)
                if clean_speech:
                    audio_bytes = ai_engine.generate_elevenlabs_voice_audio(clean_speech)
                    if audio_bytes and is_still_active():
                        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                        socketio.emit(
                            "ai_voice_audio",
                            {
                                "text": clean_speech,
                                "audio_base64": audio_b64
                            },
                            to=target_sid
                        )
                        socketio.sleep(0)
                    else:
                        socketio.emit("ai_voice_unlock", {"unlock": True}, to=target_sid)
                        socketio.sleep(0)
                else:
                    socketio.emit("ai_voice_unlock", {"unlock": True}, to=target_sid)
                    socketio.sleep(0)

            if is_still_active():
                socketio.emit(
                    "ai_stream_done",
                    {"done": True, "session_id": active_sess_id, "full_text": accumulated_reply.strip()},
                    to=target_sid
                )
                socketio.sleep(0)

            if accumulated_reply.strip() and target_email and not voice_flag and is_still_active():
                if not active_sess_id:
                    title_text = (disp_msg[:30] + "...") if len(disp_msg) > 30 else disp_msg
                    active_sess_id = db_create_session(target_email, title_text, target_jwt)

                if active_sess_id:
                    db_create_message(active_sess_id, "user", disp_msg, target_jwt)
                    db_create_message(active_sess_id, "assistant", accumulated_reply.strip(), target_jwt)

        except Exception as exc:
            print(f"[Socket Stream Error]: {exc}", flush=True)
            socketio.emit("ai_voice_unlock", {"unlock": True}, to=target_sid)
            socketio.emit("ai_error", {"error": str(exc)}, to=target_sid)
            socketio.sleep(0)

    socketio.start_background_task(
        _run_realtime_stream,
        sid,
        user_email,
        user_jwt,
        message,
        display_message,
        history,
        learned_skills,
        image_data,
        is_voice,
        session_id,
        user_timezone,
        user_local_time,
        user_local_hour
    )


@socketio.on("disconnect")
def handle_socket_disconnect():
    sid = request.sid
    ACTIVE_STREAM_FLAGS.pop(sid, None)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
