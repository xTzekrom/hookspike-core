"""
HookSpike AI - Production Backend (Supabase Auth & Streaming + Permanent Chat Memory)
Features:
- Paused / Aborted generations are NOT saved to Supabase until completed or refined.
- Strict session ownership check so users can only view their own chat history.
- Added /favicon.ico route for browser URL bars & search suggestions.
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
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
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hookspike_vault_key_2026")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jhiqvsuigdfjwjbtlnwh.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_dBBumAWhsq1yRU5WCYkAXQ_EfMdlqPU").strip()

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[DB Status]: Supabase SDK client initialized!", flush=True)
    except Exception as exc:
        print(f"[DB SDK Warning - Fallback Direct REST]: {exc}", flush=True)

ADMIN_EMAILS = {
    "playerofwar99@gmail.com",
    "unbbirlin1@gmail.com"
}


def sb_headers() -> dict:
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if SUPABASE_KEY.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    return headers


def db_select(table: str, query_params: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{query_params}"
    try:
        req = urllib.request.Request(url, headers=sb_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"[DB Select Error ({table})]: {exc}", flush=True)
        return []


def db_insert(table: str, payload: dict) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(), method="POST")
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


def db_update(table: str, match_query: str, payload: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_query}"
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(), method="PATCH")
        with urllib.request.urlopen(req, timeout=8) as _:
            return True
    except Exception as exc:
        print(f"[DB Update Error ({table})]: {exc}", flush=True)
        return False


def verify_and_get_email(req_data: dict | None = None) -> str:
    # 1. Flask verified session check
    sess_email = (session.get("user_email") or "").strip().lower()
    if sess_email and "@" in sess_email:
        return sess_email

    # 2. Bearer Token Auth via Supabase
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif req_data and req_data.get("access_token"):
        token = str(req_data.get("access_token")).strip()

    if token and supabase:
        try:
            user_res = supabase.auth.get_user(token)
            if user_res and user_res.user and user_res.user.email:
                verified_email = user_res.user.email.strip().lower()
                session["user_email"] = verified_email
                return verified_email
        except Exception as exc:
            print(f"[Token Auth Note]: {exc}", flush=True)

    # 3. Synchronized Payload check
    if req_data:
        raw_email = (req_data.get("email") or req_data.get("user_email") or "").strip().lower()
        if raw_email and "@" in raw_email:
            session["user_email"] = raw_email
            return raw_email

    return ""


def get_user_tokens(user_email: str) -> int:
    user_email = (user_email or "").strip().lower()
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        return 99999999

    encoded_email = urllib.parse.quote(user_email)
    rows = db_select("user_tokens", f"email=eq.{encoded_email}&select=tokens_left")
    if rows and len(rows) > 0:
        return int(rows[0].get("tokens_left", 0))

    db_insert("user_tokens", {"email": user_email, "tokens_left": 5})
    return 5


def deduct_user_token(user_email: str) -> int:
    user_email = (user_email or "").strip().lower()
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        return 99999999

    curr = get_user_tokens(user_email)
    new_balance = max(0, curr - 1)
    encoded_email = urllib.parse.quote(user_email)
    db_update("user_tokens", f"email=eq.{encoded_email}", {"tokens_left": new_balance})
    return new_balance


def is_casual_message(text: str) -> bool:
    t = text.strip().lower()
    casual_words = {
        "hi", "hello", "heyy", "heyyy", "hey", "yo", "wassup",
        "sup", "kya haal hai", "kaise ho", "bol bhai", "kya chal rha"
    }
    return t in casual_words


@app.route("/")
def index():
    user_email = (session.get("user_email") or "").strip().lower()
    logged_in = bool(user_email)
    tokens = get_user_tokens(user_email) if logged_in else 0
    return render_template(
        "index.html",
        logged_in=logged_in,
        user_email=user_email,
        tokens_left=tokens,
        supabase_url=SUPABASE_URL or "",
        supabase_key=SUPABASE_KEY or ""
    )


@app.route("/api/auth/sync", methods=["POST"])
def auth_sync():
    data = request.get_json() or {}
    email = verify_and_get_email(data)
    if email and "@" in email:
        session["user_email"] = email
        tokens = get_user_tokens(email)
        return jsonify({"ok": True, "email": email, "tokens": tokens})
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

    encoded_email = urllib.parse.quote(user_email)
    sessions = db_select(
        "chat_sessions",
        f"user_email=eq.{encoded_email}&select=id,title,created_at&order=created_at.desc&limit=30"
    )
    return jsonify(sessions)


@app.route("/api/chat-messages/<session_id>", methods=["GET"])
def get_chat_messages(session_id):
    user_email = verify_and_get_email()
    if not user_email or not session_id:
        return jsonify([])

    encoded_sess = urllib.parse.quote(str(session_id))
    encoded_email = urllib.parse.quote(user_email)

    # Security Fix: Verify that this session belongs to the logged-in user
    ownership = db_select(
        "chat_sessions",
        f"id=eq.{encoded_sess}&user_email=eq.{encoded_email}&select=id"
    )
    if not ownership:
        return jsonify([])

    messages = db_select(
        "chat_messages",
        f"session_id=eq.{encoded_sess}&select=role,content,created_at&order=created_at.asc"
    )
    return jsonify(messages)


@app.route("/api/chat-stream", methods=["POST"])
def chat_stream():
    payload = request.get_json() or {}
    user_email = verify_and_get_email(payload)

    if not user_email:
        return jsonify({"error": "Login required", "login_needed": True}), 401

    session["user_email"] = user_email
    tokens = get_user_tokens(user_email)
    message = payload.get("message", "").strip()
    display_message = payload.get("display_message", message).strip()
    history = payload.get("history", [])
    session_id = payload.get("session_id")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    casual = is_casual_message(display_message)

    if tokens <= 0 and user_email not in ADMIN_EMAILS:
        return jsonify({"error": "Tokens exhausted", "paywall": True}), 402

    def generate_sse(existing_sess_id: str | None):
        accumulated_reply = ""
        remaining_tokens = tokens
        token_deducted = False
        active_sess_id = existing_sess_id

        try:
            # Stream chunks token-by-token
            for chunk in ai_engine.stream_creator_chat(message, history):
                if chunk:
                    if not token_deducted and not casual:
                        remaining_tokens = deduct_user_token(user_email)
                        token_deducted = True

                    accumulated_reply += chunk
                    yield f"data: {json.dumps({'token': chunk, 'tokens_left': remaining_tokens, 'session_id': active_sess_id})}\n\n"

            # Smart Pause Feature: Save to Supabase ONLY after generation finishes without interruption!
            if accumulated_reply.strip():
                if not active_sess_id:
                    title_text = (display_message[:28] + "...") if len(display_message) > 28 else display_message
                    inserted = db_insert("chat_sessions", {
                        "user_email": user_email,
                        "title": title_text
                    })
                    if inserted and len(inserted) > 0:
                        active_sess_id = str(inserted[0].get("id"))

                if active_sess_id:
                    db_insert("chat_messages", {
                        "session_id": active_sess_id,
                        "role": "user",
                        "content": display_message
                    })
                    db_insert("chat_messages", {
                        "session_id": active_sess_id,
                        "role": "assistant",
                        "content": accumulated_reply
                    })
                    yield f"data: {json.dumps({'session_id': active_sess_id, 'tokens_left': remaining_tokens})}\n\n"

            yield "data: [DONE]\n\n"
        except GeneratorExit:
            # User clicked Stop/Pause -> Do NOT save incomplete draft to Supabase
            print("[Stream Paused by User]: Draft kept on client only.", flush=True)
        except Exception as exc:
            print(f"[Stream Error]: {exc}", flush=True)
            yield f"data: {json.dumps({'token': f'⚠️ Connection Error: {exc}', 'tokens_left': remaining_tokens, 'session_id': active_sess_id})}\n\n"
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
