"""
HookSpike AI - Core App Controller (v4.3 - Production Stable)
"""

import json
import os
from flask import Flask, Response, jsonify, redirect, render_template, request, session, stream_with_context, url_for
from supabase import create_client, Client
import ai_engine

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hookspike_secret_secure_key_2026")

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
        return 10
    try:
        res = supabase.table("user_tokens").select("tokens_left").eq("email", user_email).execute()
        if res.data and len(res.data) > 0:
            return int(res.data[0].get("tokens_left", 0))
        supabase.table("user_tokens").insert({"email": user_email, "tokens_left": 10}).execute()
        return 10
    except Exception:
        return 10

def deduct_user_token(user_email: str) -> int:
    if user_email in ADMIN_EMAILS:
        return 99999999
    if not supabase:
        return 9
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
    return render_template("index.html", logged_in=logged_in, user_email=user_email, tokens_left=tokens)

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if email and "@" in email:
        session["user_email"] = email
        return jsonify({"ok": True, "email": email, "tokens": get_user_tokens(email)})
    return jsonify({"error": "Valid email address required"}), 400

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

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

    if not message:
        return jsonify({"error": "Empty message"}), 400

    remaining = deduct_user_token(user_email)

    def generate_sse():
        try:
            for chunk in ai_engine.stream_creator_chat(message, history):
                yield f"data: {json.dumps({'token': chunk, 'tokens_left': remaining})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'token': f'⚠️ Error: {exc}', 'tokens_left': remaining})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate_sse()), mimetype="text/event-stream")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
