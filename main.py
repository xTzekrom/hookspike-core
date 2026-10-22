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

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as exc:
        print(f"[DB Warning]: {exc}")

ADMIN_EMAILS = [
    "playerofwar99@gmail.com",
    "unbbirlin1@gmail.com"
]

def get_user_tokens(user_email: str) -> int:
    if not user_email:
        return 0
    if user_email in ADMIN_EMAILS:
        return 99999999
    if not supabase:
        return 5
    try:
        res = supabase.table("user_tokens").select("tokens_left").eq("email", user_email).execute()
        if res.data and len(res.data) > 0:
            return int(res.data[0].get("tokens_left", 0))
        supabase.table("user_tokens").insert({"email": user_email, "tokens_left": 5}).execute()
        return 5
    except Exception:
        return 5

def deduct_user_token(user_email: str) -> int:
    if user_email in ADMIN_EMAILS:
        return 99999999
    if not supabase:
        return 4
    try:
        curr = get_user_tokens(user_email)
        new_balance = max(0, curr - 1)
        supabase.table("user_tokens").update({"tokens_left": new_balance}).eq("email", user_email).execute()
        return new_balance
    except Exception:
        return 0

@app.route("/")
def index():
    user_email = session.get("user_email")
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
    email = data.get("email", "").strip().lower()
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
    user_email = session.get("user_email")
    if not user_email or not supabase:
        return jsonify([])
    try:
        res = supabase.table("chat_sessions").select("id, title, created_at").eq("user_email", user_email).order("created_at", desc=True).limit(25).execute()
        return jsonify(res.data or [])
    except Exception as exc:
        print(f"[Fetch Sessions Error]: {exc}")
        return jsonify([])

@app.route("/api/chat-messages/<session_id>", methods=["GET"])
def get_chat_messages(session_id):
    user_email = session.get("user_email")
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
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Login required", "login_needed": True}), 401

    tokens = get_user_tokens(user_email)
    if tokens <= 0 and user_email not in ADMIN_EMAILS:
        return jsonify({"error": "Tokens exhausted", "paywall": True}), 402

    payload = request.get_json() or {}
    message = payload.get("message", "").strip()
    history = payload.get("history", [])
    session_id = payload.get("session_id")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    current_session_id = session_id
    if not current_session_id and supabase:
        try:
            title_text = (message[:32] + "...") if len(message) > 32 else message
            new_sess = supabase.table("chat_sessions").insert({
                "user_email": user_email,
                "title": title_text
            }).execute()
            if new_sess.data and len(new_sess.data) > 0:
                current_session_id = new_sess.data[0].get("id")
        except Exception as exc:
            print(f"[Session Create Error]: {exc}")

    def generate_sse():
        has_deducted = False
        remaining = tokens
        accumulated_reply = ""

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
                if not has_deducted and not chunk.startswith("⚠️"):
                    remaining = deduct_user_token(user_email)
                    has_deducted = True

                accumulated_reply += chunk
                yield f"data: {json.dumps({'token': chunk, 'tokens_left': remaining, 'session_id': current_session_id})}\n\n"

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
            yield f"data: {json.dumps({'token': f'⚠️ Connection Error: {exc}', 'tokens_left': remaining, 'session_id': current_session_id})}\n\n"
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
