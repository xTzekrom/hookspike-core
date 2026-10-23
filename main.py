"""
HookSpike AI - Production Backend (Supabase Auth & Streaming + Permanent Chat Memory)
"""

import json
import os
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

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jhiqvsuigdfjwjbtlnwh.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_dBBumAWhsq1yRU5WCYkAXQ_EfMdlqPU")

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        print(f"[DB Warning]: {exc}")

ADMIN_EMAILS = {
    "playerofwar99@gmail.com",
    "unbbirlin1@gmail.com"
}


def verify_and_get_email(req_data: dict | None = None) -> str:
    """
    FIXED BUG 5 & 6: Securely resolves and normalizes user email (.strip().lower())
    Verifies Supabase JWT access_token if provided so no one can spoof Admin emails.
    """
    # 1. Check already verified Flask session
    sess_email = (session.get("user_email") or "").strip().lower()
    if sess_email:
        return sess_email

    # 2. Check Authorization Bearer token or payload token via Supabase Auth
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
            print(f"[Token Auth Warning]: {exc}")

    # 3. Fallback to query/body email (only if non-admin to block admin spoofing)
    raw_email = ""
    if req_data:
        raw_email = (req_data.get("email") or req_data.get("user_email") or "").strip().lower()
    if not raw_email:
        raw_email = (request.args.get("email") or "").strip().lower()

    if raw_email and "@" in raw_email:
        # Prevent unverified requests from claiming an ADMIN email without a valid token
        if raw_email in ADMIN_EMAILS and not token:
            return ""
        return raw_email

    return ""


def get_user_tokens(user_email: str) -> int:
    user_email = (user_email or "").strip().lower()
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        return 99999999
    if not supabase:
        return 0
    try:
        res = supabase.table("user_tokens").select("tokens_left").eq("email", user_email).execute()
        if res.data and len(res.data) > 0:
            return int(res.data[0].get("tokens_left", 0))
        
        # Naye user ke liye sirf pehli baar 5 tokens set karo
        supabase.table("user_tokens").insert({"email": user_email, "tokens_left": 5}).execute()
        return 5
    except Exception as e:
        print(f"[Token Fetch Error]: {e}")
        return 0


def deduct_user_token(user_email: str) -> int:
    user_email = (user_email or "").strip().lower()
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        return 99999999
    if not supabase:
        return 0
    try:
        curr = get_user_tokens(user_email)
        new_balance = max(0, curr - 1)
        supabase.table("user_tokens").update({"tokens_left": new_balance}).eq("email", user_email).execute()
        return new_balance
    except Exception as e:
        print(f"[Token Deduct Error]: {e}")
        return 0


def is_casual_message(text: str) -> bool:
    """Free casual greetings par token na katne ke liye filter"""
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
    return jsonify({"error": "Invalid or unverified email"}), 400


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
    if not user_email or not supabase:
        return jsonify([])
    try:
        res = supabase.table("chat_sessions").select("id, title, created_at").eq("user_email", user_email).order("created_at", desc=True).limit(30).execute()
        return jsonify(res.data or [])
    except Exception as exc:
        print(f"[Fetch Sessions Error]: {exc}")
        return jsonify([])


@app.route("/api/chat-messages/<session_id>", methods=["GET"])
def get_chat_messages(session_id):
    user_email = verify_and_get_email()
    if not user_email or not supabase or not session_id:
        return jsonify([])
    try:
        sess = supabase.table("chat_sessions").select("id").eq("id", session_id).eq("user_email", user_email).execute()
        if not sess.data:
            return jsonify([])
        res = supabase.table("chat_messages").select("role, content, created_at").eq("session_id", session_id).order("created_at", desc=False).execute()
        return jsonify(res.data or [])
    except Exception as exc:
        print(f"[Fetch Messages Error]: {exc}")
        return jsonify([])

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

    # Strict check - agar tokens 0 hain toh request AI tak jayegi hi nahi
    if tokens <= 0 and user_email not in ADMIN_EMAILS:
        return jsonify({"error": "Tokens exhausted", "paywall": True}), 402

    current_session_id = session_id
    if not current_session_id and supabase:
        try:
            title_text = (message[:26] + "...") if len(message) > 26 else message
            new_sess = supabase.table("chat_sessions").insert({
                "user_email": user_email,
                "title": title_text
            }).execute()
            if new_sess.data and len(new_sess.data) > 0:
                current_session_id = new_sess.data[0].get("id")
        except Exception as exc:
            print(f"[Session Create Error]: {exc}")

    # FIXED BUG 7: Token tabhi katega jab AI sach me reply dena shuru karega!
    def generate_sse():
        accumulated_reply = ""
        remaining_tokens = tokens
        token_deducted = False

        try:
            if current_session_id and supabase:
                try:
                    supabase.table("chat_messages").insert({
                        "session_id": current_session_id,
                        "role": "user",
                        "content": message
                    }).execute()
                except Exception as e:
                    print(f"[DB Save User Error]: {e}")

            for chunk in ai_engine.stream_creator_chat(message, history):
                if chunk and not token_deducted and not casual:
                    remaining_tokens = deduct_user_token(user_email)
                    token_deducted = True

                accumulated_reply += chunk
                yield f"data: {json.dumps({'token': chunk, 'tokens_left': remaining_tokens, 'session_id': current_session_id})}\n\n"

            if current_session_id and supabase and accumulated_reply:
                try:
                    supabase.table("chat_messages").insert({
                        "session_id": current_session_id,
                        "role": "assistant",
                        "content": accumulated_reply
                    }).execute()
                except Exception as e:
                    print(f"[DB Save AI Error]: {e}")

            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'token': f'⚠️ Connection Error: {exc}', 'tokens_left': remaining_tokens, 'session_id': current_session_id})}\n\n"
            yield "data: [DONE]\n\n"

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    }

    return Response(stream_with_context(generate_sse()), headers=headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
