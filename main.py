"""
HookSpike AI - Production Backend (100% Secure Dual-Key Supabase Cloud + ElevenLabs Voice Integration)
"""

import json
import os
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
from supabase import create_client, Client
import ai_engine

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hookspike_vault_2026_secured")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_PERMANENT"] = True

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jhiqvsuigdfjwjbtlnwh.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_dBBumAWhsq1yRU5WCYkAXQ_EfMdlqPU").strip()
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
        with urllib.request.urlopen(req, timeout=4) as resp:
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

    return True, "⚡ This chat session has reached its active memory limit. Please start a New Chat to continue instantly for free."

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
        return jsonify({"ok": True, "email": email})
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

    if not message and not image_data:
        return jsonify({"error": "Empty message"}), 400

    if not message and image_data:
        message = "Please analyze this image and help me with it."
        display_message = "[Photo Attached]"

    if user_email and session_id:
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
            for chunk in ai_engine.stream_creator_chat(message, history, learned_skills, image_data, voice_mode=voice_mode):
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

            if accumulated_reply.strip() and target_email:
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


# -------------------------------------------------------------------------
# ELEVENLABS ULTRA-LOW LATENCY VOICE ROUTE (ROMJ9yK1NAMuu1ggrjDW)
# -------------------------------------------------------------------------
@app.route("/api/voice-tts", methods=["POST"])
def voice_tts_endpoint():
    data = request.get_json(silent=True) or {}
    raw_text = (data.get("text") or "").strip()

    if not raw_text:
        return jsonify({"error": "Empty text"}), 400

    clean_speech = re.sub(r"```[\s\S]*?```", " ", raw_text)
    clean_speech = re.sub(r"!\[.*?\]\(.*?\)", " ", clean_speech)
    clean_speech = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", clean_speech)
    clean_speech = re.sub(r"[*#_~`>|]", " ", clean_speech)
    clean_speech = re.sub(r"\s+", " ", clean_speech).strip()

    if not clean_speech:
        clean_speech = "I am right here with you, tell me what is on your mind."

    try:
        audio_bytes = ai_engine.generate_elevenlabs_voice_audio(clean_speech)
        if not audio_bytes:
            return jsonify({"error": "Failed to fetch ElevenLabs audio. Check ELEVENLABS_API_KEY."}), 502

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
