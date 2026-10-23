"""
HookSpike AI - Production Backend (100% Fixed Dual-Key & Auto-Fallback Engine)
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

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jhiqvsuigdfjwjbtlnwh.supabase.co").strip().rstrip("/")

# Always safe public key for Frontend & Fallback
PUBLIC_ANON_KEY = "sb_publishable_dBBumAWhsq1yRU5WCYkAXQ_EfMdlqPU"

# Backend key from Render Environment (or fallback to public key)
raw_env_key = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SECRET_KEY")
    or os.environ.get("SUPABASE_KEY")
    or PUBLIC_ANON_KEY
).strip()


SUPABASE_KEY = raw_env_key if raw_env_key else PUBLIC_ANON_KEY

supabase: Client | None = None
try:
    supabase = create_client(SUPABASE_URL, PUBLIC_ANON_KEY)
except Exception as exc:
    print(f"[Supabase Auth Init Note]: {exc}", flush=True)

ADMIN_EMAILS = {
    "playerofwar99@gmail.com",
    "unbbirlin1@gmail.com"
}


# --- BULLETPROOF DUAL-KEY SUPABASE REST ENGINE ---
# Pehle Render ki key try karega, agar usme koi dikkat aayi toh turant Public Key se save karega!

def make_headers(api_key: str) -> dict:
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def db_request(method: str, table: str, query_params: str = "", payload: dict | None = None) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if query_params:
        url = f"{url}?{query_params}"

    body = json.dumps(payload).encode("utf-8") if payload is not None else None

    # Try primary key first, then fallback to PUBLIC_ANON_KEY if different
    keys_to_try = [SUPABASE_KEY]
    if SUPABASE_KEY != PUBLIC_ANON_KEY:
        keys_to_try.append(PUBLIC_ANON_KEY)

    for idx, key in enumerate(keys_to_try):
        try:
            req = urllib.request.Request(url, data=body, headers=make_headers(key), method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return []
                data = json.loads(raw)
                return data if isinstance(data, list) else [data]
        except urllib.error.HTTPError as he:
            err_text = he.read().decode("utf-8", errors="ignore")
            print(f"[DB HTTP Error ({method} {table}) Key#{idx+1}]: {he.code} -> {err_text}", flush=True)
        except Exception as exc:
            print(f"[DB Network Error ({method} {table}) Key#{idx+1}]: {exc}", flush=True)

    return []


def db_select(table: str, query_params: str) -> list:
    return db_request("GET", table, query_params=query_params)


def db_insert(table: str, payload: dict) -> list:
    return db_request("POST", table, payload=payload)


def db_update(table: str, match_query: str, payload: dict) -> bool:
    res = db_request("PATCH", table, query_params=match_query, payload=payload)
    return bool(res is not None)


# ------------------------------------------------


def verify_and_get_email(req_data: dict | None = None) -> str:
    # 1. Check direct email from request payload or query params FIRST
    raw_email = ""
    if req_data:
        raw_email = (req_data.get("email") or req_data.get("user_email") or "").strip().lower()
    if not raw_email:
        raw_email = (request.args.get("email") or "").strip().lower()

    if raw_email and "@" in raw_email:
        session["user_email"] = raw_email
        return raw_email

    # 2. Check Flask session
    sess_email = (session.get("user_email") or "").strip().lower()
    if sess_email and "@" in sess_email:
        return sess_email

    # 3. Check Authorization Bearer token
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

    return ""


def get_user_tokens(user_email: str) -> int:
    user_email = (user_email or "").strip().lower()
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        # Ensure admin is also logged in user_tokens table for visibility
        encoded_email = urllib.parse.quote(user_email)
        rows = db_select("user_tokens", f"email=eq.{encoded_email}&select=tokens_left")
        if not rows:
            db_insert("user_tokens", {"email": user_email, "tokens_left": 999999})
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
    # ALWAYS pass PUBLIC_ANON_KEY to index.html so browser never gets blocked!
    return render_template(
        "index.html",
        logged_in=logged_in,
        user_email=user_email,
        tokens_left=tokens,
        supabase_url=SUPABASE_URL,
        supabase_key=PUBLIC_ANON_KEY
    )


@app.route("/api/auth/sync", methods=["POST"])
def auth_sync():
    data = request.get_json() or {}
    email = verify_and_get_email(data)
    if email and "@" in email:
        session["user_email"] = email
        tokens = get_user_tokens(email)
        print(f"[Auth Sync Success]: {email} (Tokens: {tokens})", flush=True)
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
        print("[Fetch Sessions]: No user_email resolved", flush=True)
        return jsonify([])

    encoded_email = urllib.parse.quote(user_email)
    sessions = db_select(
        "chat_sessions",
        f"user_email=eq.{encoded_email}&select=id,title,created_at&order=created_at.desc&limit=30"
    )
    print(f"[Fetch Sessions]: Found {len(sessions)} sessions for {user_email}", flush=True)
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


# --- DIAGNOSTIC TEST ROUTE ---
@app.route("/api/debug-db")
def debug_db():
    """Browser me /api/debug-db khol kar direct check kar sakte ho ki DB chal raha hai ya nahi"""
    test_insert = db_insert("chat_sessions", {
        "user_email": "unbbirlin1@gmail.com",
        "title": "⚡ System Connection Test"
    })
    sessions = db_select("chat_sessions", "select=id,user_email,title,created_at&limit=5")
    return jsonify({
        "status": "SUCCESS" if test_insert else "FAILED",
        "supabase_url": SUPABASE_URL,
        "inserted_test_row": test_insert,
        "recent_sessions_in_db": sessions
    })


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

    current_session_id = session_id
    if not current_session_id:
        title_text = (message[:28] + "...") if len(message) > 28 else message
        inserted = db_insert("chat_sessions", {
            "user_email": user_email,
            "title": title_text
        })
        if inserted and len(inserted) > 0 and isinstance(inserted[0], dict):
            current_session_id = str(inserted[0].get("id") or "")
            print(f"[Session Created]: ID={current_session_id} User={user_email}", flush=True)
        else:
            print(f"[Session Create Warning]: Insert returned empty for {user_email}", flush=True)

    def generate_sse(active_sess_id: str | None):
        accumulated_reply = ""
        remaining_tokens = tokens
        token_deducted = False

        try:
            if active_sess_id:
                db_insert("chat_messages", {
                    "session_id": active_sess_id,
                    "role": "user",
                    "content": message
                })

            for chunk in ai_engine.stream_creator_chat(message, history):
                if chunk and not token_deducted and not casual:
                    remaining_tokens = deduct_user_token(user_email)
                    token_deducted = True

                accumulated_reply += chunk
                yield f"data: {json.dumps({'token': chunk, 'tokens_left': remaining_tokens, 'session_id': active_sess_id})}\n\n"

            if active_sess_id and accumulated_reply:
                db_insert("chat_messages", {
                    "session_id": active_sess_id,
                    "role": "assistant",
                    "content": accumulated_reply
                })
                print(f"[Messages Saved]: Session={active_sess_id}", flush=True)

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
          
