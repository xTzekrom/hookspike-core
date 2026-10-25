"""
HookSpike AI - Universal Backend (No Tokens, Fixed Session & Chat History DB Sync)
"""

import json
import os
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
)
from supabase import create_client, Client
import ai_engine

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hookspike_vault_2026_secured")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_PERMANENT"] = True

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jhiqvsuigdfjwjbtlnwh.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_dBBumAWhsq1yRU5WCYkAXQ_EfMdlqPU").strip()

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        print(f"[Supabase Init Warning]: {exc}", flush=True)

SESSION_MESSAGE_LIMIT = 18

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
    bearer = user_jwt if user_jwt else SUPABASE_KEY
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def db_select(table: str, query_params: str, user_jwt: str = "") -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{query_params}"
    try:
        req = urllib.request.Request(url, headers=sb_headers(user_jwt), method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"[DB Select Error ({table})]: {exc}", flush=True)
        return []

def db_insert(table: str, payload: dict, user_jwt: str = "") -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        body = json.dumps(payload).encode("utf-8")
        headers = sb_headers(user_jwt)
        headers["Prefer"] = "return=representation"
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, list) else []
    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8", errors="ignore")
        print(f"[DB Insert HTTP Error ({table})]: {he.code} - {err_body}", flush=True)
        return []
    except Exception as exc:
        print(f"[DB Insert Error ({table})]: {exc}", flush=True)
        return []

def verify_and_get_email(req_data: dict | None = None) -> str:
    token = get_request_jwt(req_data)
    if token:
        session["access_token"] = token

    # 1. Payload email check
    if req_data:
        raw_email = (req_data.get("email") or req_data.get("user_email") or "").strip().lower()
        if raw_email and "@" in raw_email:
            session["user_email"] = raw_email
            return raw_email

    # 2. URL Query Params check
    arg_email = (request.args.get("email") or request.args.get("user_email") or "").strip().lower()
    if arg_email and "@" in arg_email:
        session["user_email"] = arg_email
        return arg_email

    # 3. Session cookie check
    sess_email = (session.get("user_email") or "").strip().lower()
    if sess_email and "@" in sess_email:
        return sess_email

    # 4. Supabase JWT Auth check
    if token and supabase:
        try:
            user_res = supabase.auth.get_user(token)
            if user_res and user_res.user and user_res.user.email:
                verified_email = user_res.user.email.strip().lower()
                session["user_email"] = verified_email
                return verified_email
        except Exception:
            pass

    return ""

def check_session_memory_limit(session_id: str, user_jwt: str = "") -> tuple[bool, str]:
    if not session_id:
        return False, ""
    encoded_id = urllib.parse.quote(str(session_id))
    
    sess_rows = db_select("chat_sessions", f"id=eq.{encoded_id}&select=created_at", user_jwt)
    if not sess_rows:
        return False, ""

    msg_rows = db_select("chat_messages", f"session_id=eq.{encoded_id}&select=id", user_jwt)
    if len(msg_rows) < SESSION_MESSAGE_LIMIT:
        return False, ""

    try:
        created_time_str = sess_rows[0].get("created_at")
        created_dt = datetime.fromisoformat(created_time_str.replace("Z", "+00:00"))
        time_diff = datetime.now(timezone.utc) - created_dt
        if time_diff.total_seconds() >= 86400:
            return False, ""
    except Exception:
        pass

    return True, "⚡ This chat session has reached its active memory limit. Please start a New Chat to continue instantly for free, or wait 24 hours for this session's memory to refresh."

@app.route("/")
def index():
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/logo.png")
def serve_logo():
    return send_from_directory(".", "logo.png", mimetype="image/png")

@app.route("/favicon.ico")
def serve_favicon():
    return send_from_directory(".", "logo.png", mimetype="image/png")

@app.route("/api/chat-sessions", methods=["GET"])
def get_chat_sessions():
    user_email = verify_and_get_email()
    if not user_email:
        return jsonify([])

    user_jwt = get_request_jwt()
    encoded_email = urllib.parse.quote(user_email)
    sessions = db_select(
        "chat_sessions",
        f"user_email=eq.{encoded_email}&select=id,title,created_at&order=created_at.desc&limit=30",
        user_jwt
    )
    return jsonify(sessions)

@app.route("/api/chat-messages/<session_id>", methods=["GET"])
def get_chat_messages(session_id):
    user_email = verify_and_get_email()
    if not user_email or not session_id:
        return jsonify([])

    user_jwt = get_request_jwt()
    encoded_sess = urllib.parse.quote(str(session_id))
    encoded_email = urllib.parse.quote(user_email)

    ownership = db_select(
        "chat_sessions",
        f"id=eq.{encoded_sess}&user_email=eq.{encoded_email}&select=id",
        user_jwt
    )
    if not ownership:
        return jsonify([])

    messages = db_select(
        "chat_messages",
        f"session_id=eq.{encoded_sess}&select=role,content,created_at&order=created_at.asc",
        user_jwt
    )
    return jsonify(messages)

@app.route("/api/chat-stream", methods=["POST"])
def chat_stream():
    payload = request.get_json(silent=True) or {}
    user_email = verify_and_get_email(payload)
    user_jwt = get_request_jwt(payload)

    message = payload.get("message", "").strip()
    display_message = payload.get("display_message", message).strip()
    history = payload.get("history", [])
    session_id = payload.get("session_id")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    if user_email and session_id:
        is_limited, limit_msg = check_session_memory_limit(session_id, user_jwt)
        if is_limited:
            return jsonify({"error": limit_msg, "memory_full": True}), 429

    def generate_sse(existing_sess_id: str | None):
        accumulated_reply = ""
        active_sess_id = existing_sess_id

        try:
            for chunk in ai_engine.stream_creator_chat(message, history):
                if chunk:
                    accumulated_reply += chunk
                    yield f"data: {json.dumps({'token': chunk, 'session_id': active_sess_id})}\n\n"

            # Save to Supabase when reply completes and user is logged in
            if accumulated_reply.strip() and user_email:
                if not active_sess_id:
                    title_text = (display_message[:30] + "...") if len(display_message) > 30 else display_message
                    inserted = db_insert("chat_sessions", {
                        "user_email": user_email,
                        "title": title_text
                    }, user_jwt)
                    if inserted and len(inserted) > 0 and inserted[0].get("id"):
                        active_sess_id = str(inserted[0].get("id"))

                if active_sess_id:
                    db_insert("chat_messages", {
                        "session_id": active_sess_id,
                        "role": "user",
                        "content": display_message
                    }, user_jwt)
                    db_insert("chat_messages", {
                        "session_id": active_sess_id,
                        "role": "assistant",
                        "content": accumulated_reply
                    }, user_jwt)
                    yield f"data: {json.dumps({'session_id': active_sess_id})}\n\n"

            yield "data: [DONE]\n\n"
        except GeneratorExit:
            pass
        except Exception as exc:
            yield f"data: {json.dumps({'token': f'⚠️ Connection issue: {exc}', 'session_id': active_sess_id})}\n\n"
            yield "data: [DONE]\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    }

    return Response(stream_with_context(generate_sse(session_id)), headers=headers)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
