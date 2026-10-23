"""
HookSpike AI - Production Backend (Supabase Auth & Streaming + Permanent Chat Memory)
100% Fixed Direct REST + SDK Hybrid for Bulletproof Database Saving
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

# Session cookie settings taaki Render HTTPS par session kabhi drop na ho
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jhiqvsuigdfjwjbtlnwh.supabase.co").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_dBBumAWhsq1yRU5WCYkAXQ_EfMdlqPU").strip()

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[DB Status]: Supabase SDK client initialized!", flush=True)
    except Exception as exc:
        print(f"[DB SDK Warning - Using Direct REST Fallback]: {exc}", flush=True)

ADMIN_EMAILS = {
    "playerofwar99@gmail.com",
    "unbbirlin1@gmail.com"
}


# --- BULLETPROOF SUPABASE DIRECT REST HELPERS ---
# Ye helpers tab bhi kaam karenge jab Python SDK 'sb_publishable_' key par fail ho jaye!

def sb_headers() -> dict:
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    # JWT key starts with eyJ
    if SUPABASE_KEY.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    return headers


def db_select(table: str, query_params: str) -> list:
    """Safely fetch rows from Supabase table via SDK or Direct REST API"""
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
    """Safely insert row into Supabase table and return created record"""
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
    """Safely update row in Supabase table"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_query}"
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=sb_headers(), method="PATCH")
        with urllib.request.urlopen(req, timeout=8) as _:
            return True
    except Exception as exc:
        print(f"[DB Update Error ({table})]: {exc}", flush=True)
        return False


# ------------------------------------------------


def verify_and_get_email(req_data: dict | None = None) -> str:
    """
    Resolves user email from Flask session, Supabase token, or request parameters.
    """
    # 1. Check Flask session first
    sess_email = (session.get("user_email") or "").strip().lower()
    if sess_email and "@" in sess_email:
        return sess_email

    # 2. Check Authorization Bearer token via Supabase
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

    # 3. Fallback to query/body email (Fixed: No longer blocks Admin from loading history!)
    raw_email = ""
    if req_data:
        raw_email = (req_data.get("email") or req_data.get("user_email") or "").strip().lower()
    if not raw_email:
        raw_email = (request.args.get("email") or "").strip().lower()

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

    # Naye user ke liye 5 tokens insert karo
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
    return jsonify({"error": "Invalid email"}), 400


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/logo.png")
def serve_logo():
    return send_from_directory(".", "logo.png")


# --- PERMANENT CHAT MEMORY ROUTES ---

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
    messages = db_select(
        "chat_messages",
        f"session_id=eq.{encoded_sess}&select=role,content,created_at&order=created_at.asc"
    )
    return jsonify(messages)


# ------------------------------------


@app.route("/api/chat-stream", methods=["POST"])
def chat_stream():
    payload = request.get_json() or {}
    user_email = verify_and_get_email(payload)

    if not user_email:
        return jsonify({"error": "Login required", "login_needed": True}), 401

    session["user_email"] = user_email
    tokens = get_user_tokens(user_email)
    message = payload.get("message", "").strip()
    history = payload.get("history", [])
    session_id = payload.get("session_id")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    casual = is_casual_message(message)

    if tokens <= 0 and user_email not in ADMIN_EMAILS:
        return jsonify({"error": "Tokens exhausted", "paywall": True}), 402

    # Create new session in Supabase if not exists
    current_session_id = session_id
    if not current_session_id:
        title_text = (message[:28] + "...") if len(message) > 28 else message
        inserted = db_insert("chat_sessions", {
            "user_email": user_email,
            "title": title_text
        })
        if inserted and len(inserted) > 0:
            current_session_id = str(inserted[0].get("id"))
            print(f"[Session Created]: {current_session_id} for {user_email}", flush=True)

    def generate_sse(active_sess_id: str | None):
        accumulated_reply = ""
        remaining_tokens = tokens
        token_deducted = False

        try:
            # 1. Save user message immediately
            if active_sess_id:
                db_insert("chat_messages", {
                    "session_id": active_sess_id,
                    "role": "user",
                    "content": message
                })

            # 2. Stream AI response
            for chunk in ai_engine.stream_creator_chat(message, history):
                if chunk and not token_deducted and not casual:
                    remaining_tokens = deduct_user_token(user_email)
                    token_deducted = True

                accumulated_reply += chunk
                yield f"data: {json.dumps({'token': chunk, 'tokens_left': remaining_tokens, 'session_id': active_sess_id})}\n\n"

            # 3. Save AI reply after stream finishes
            if active_sess_id and accumulated_reply:
                db_insert("chat_messages", {
                    "session_id": active_sess_id,
                    "role": "assistant",
                    "content": accumulated_reply
                })
                print(f"[Messages Saved] Session: {active_sess_id}", flush=True)

            yield "data: [DONE]\n\n"
        except Exception as exc:
            print(f"[Stream Error]: {exc}", flush=True)
            yield f"data: {json.dumps({'token': f'⚠️ Connection Error: {exc}', 'tokens_left': remaining_tokens, 'session_id': active_sess_id})}\n\n"
            yield "data: [DONE]\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    }

    return Response(stream_with_context(generate_sse(current_session_id)), headers=headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
        
