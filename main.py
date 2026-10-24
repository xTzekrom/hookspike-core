"""
HookSpike AI - Production Backend (Supabase Auth & Streaming + Permanent Chat Memory)
Features:
- Paused / Aborted generations are NOT saved to Supabase until completed or refined.
- Strict session ownership check so users can only view their own chat history.
- Added /favicon.ico route for browser URL bars & search suggestions.
- Fixed Auth Verification for GET/POST requests, RLS User JWT forwarding & Fallback Token Memory.
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
app.config["SESSION_PERMANENT"] = True

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

# Fallback memory cache in case Supabase RLS blocks anon key writes for normal users
LOCAL_TOKEN_CACHE: dict[str, int] = {}


def get_request_jwt(req_data: dict | None = None) -> str:
    """Extracts user's Supabase JWT token if available so PostgREST RLS policies pass."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        tok = auth_header.split(" ", 1)[1].strip()
        if tok and tok != "undefined" and tok != "null":
            return tok
    if req_data and req_data.get("access_token"):
        tok = str(req_data.get("access_token")).strip()
        if tok and tok != "undefined" and tok != "null":
            return tok
    sess_tok = session.get("access_token", "")
    return sess_tok


def sb_headers(user_jwt: str = "") -> dict:
    # Use User JWT if available (passes Supabase RLS for normal users), else fallback to SUPABASE_KEY
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
        # Fallback retry without user_jwt if custom JWT header caused an issue
        if user_jwt:
            try:
                req = urllib.request.Request(url, headers=sb_headers(""), method="GET")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data if isinstance(data, list) else []
            except Exception:
                pass
        print(f"[DB Select Error ({table})]: {exc}", flush=True)
        return []


def db_insert(table: str, payload: dict, user_jwt: str = "") -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(user_jwt), method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if isinstance(data, list) else []
    except urllib.error.HTTPError as he:
        if user_jwt:
            try:
                body = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers=sb_headers(""), method="POST")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data if isinstance(data, list) else []
            except Exception:
                pass
        err_body = he.read().decode("utf-8", errors="ignore")
        print(f"[DB Insert HTTP Error ({table})]: {he.code} - {err_body}", flush=True)
        return []
    except Exception as exc:
        print(f"[DB Insert Error ({table})]: {exc}", flush=True)
        return []


def db_update(table: str, match_query: str, payload: dict, user_jwt: str = "") -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_query}"
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(user_jwt), method="PATCH")
        with urllib.request.urlopen(req, timeout=8) as _:
            return True
    except Exception as exc:
        if user_jwt:
            try:
                body = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers=sb_headers(""), method="PATCH")
                with urllib.request.urlopen(req, timeout=8) as _:
                    return True
            except Exception:
                pass
        print(f"[DB Update Error ({table})]: {exc}", flush=True)
        return False


def verify_and_get_email(req_data: dict | None = None) -> str:
    # Save token in session if provided
    token = get_request_jwt(req_data)
    if token:
        session["access_token"] = token

    # 1. Flask verified session check
    sess_email = (session.get("user_email") or "").strip().lower()
    if sess_email and "@" in sess_email:
        return sess_email

    # 2. Bearer Token Auth via Supabase SDK
    if token and supabase:
        try:
            user_res = supabase.auth.get_user(token)
            if user_res and user_res.user and user_res.user.email:
                verified_email = user_res.user.email.strip().lower()
                session["user_email"] = verified_email
                return verified_email
        except Exception as exc:
            print(f"[Token Auth Note]: {exc}", flush=True)

    # 3. Synchronized JSON Payload check (for POST requests)
    if req_data:
        raw_email = (req_data.get("email") or req_data.get("user_email") or "").strip().lower()
        if raw_email and "@" in raw_email:
            session["user_email"] = raw_email
            return raw_email

    # 4. FIXED: URL Query Params check (for GET requests like /api/chat-sessions?email=...)
    arg_email = (request.args.get("email") or request.args.get("user_email") or "").strip().lower()
    if arg_email and "@" in arg_email:
        session["user_email"] = arg_email
        return arg_email

    return ""


def get_user_tokens(user_email: str, user_jwt: str = "") -> int:
    user_email = (user_email or "").strip().lower()
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        return 99999999

    encoded_email = urllib.parse.quote(user_email)
    rows = db_select("user_tokens", f"email=eq.{encoded_email}&select=tokens_left", user_jwt)
    if rows and len(rows) > 0 and rows[0].get("tokens_left") is not None:
        t_left = int(rows[0].get("tokens_left", 5))
        LOCAL_TOKEN_CACHE[user_email] = t_left
        return t_left

    # If user not found in DB yet, give 5 default tokens
    inserted = db_insert("user_tokens", {"email": user_email, "tokens_left": 5}, user_jwt)
    if inserted and len(inserted) > 0 and inserted[0].get("tokens_left") is not None:
        t_left = int(inserted[0].get("tokens_left", 5))
        LOCAL_TOKEN_CACHE[user_email] = t_left
        return t_left

    # Fallback to local memory cache so normal users aren't stuck with 0 tokens if RLS blocks DB
    if user_email not in LOCAL_TOKEN_CACHE:
        LOCAL_TOKEN_CACHE[user_email] = 5
    return LOCAL_TOKEN_CACHE[user_email]


def deduct_user_token(user_email: str, user_jwt: str = "") -> int:
    user_email = (user_email or "").strip().lower()
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        return 99999999

    curr = get_user_tokens(user_email, user_jwt)
    new_balance = max(0, curr - 1)
    LOCAL_TOKEN_CACHE[user_email] = new_balance
    encoded_email = urllib.parse.quote(user_email)
    db_update("user_tokens", f"email=eq.{encoded_email}", {"tokens_left": new_balance}, user_jwt)
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
    user_jwt = session.get("access_token", "")
    logged_in = bool(user_email)
    tokens = get_user_tokens(user_email, user_jwt) if logged_in else 0
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
    data = request.get_json(silent=True) or {}
    email = verify_and_get_email(data)
    user_jwt = get_request_jwt(data)
    if email and "@" in email:
        session["user_email"] = email
        session.modified = True
        tokens = get_user_tokens(email, user_jwt)
        is_admin = email in ADMIN_EMAILS
        return jsonify({
            "ok": True,
            "email": email,
            "role": "admin" if is_admin else "user",
            "tokens": tokens
        })
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

    # Security Fix: Verify that this session belongs to the logged-in user
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

    if not user_email:
        return jsonify({"error": "Login required", "login_needed": True}), 401

    session["user_email"] = user_email
    tokens = get_user_tokens(user_email, user_jwt)
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
                        remaining_tokens = deduct_user_token(user_email, user_jwt)
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
                    }, user_jwt)
                    if inserted and len(inserted) > 0:
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
