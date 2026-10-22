"""
HookSpike AI - Core Backend Service (v4.2 - Production Stable)
=============================================================
- SSE Streaming Route for real-time ChatGPT-style outputs
- Clean Login / Logout state handling (no reload loops)
- Safe fallback when Supabase/OAuth keys are pending
- Admin bypass for creator accounts
"""

import json
import os
import sys
from flask import Flask, Response, jsonify, redirect, render_template, request, session, stream_with_context, url_for
from supabase import create_client, Client

# Import the generation engine
import ai_engine

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hookspike_creator_secret_vault_99")

# ============================================================
# AUTH CONFIGURATION (FAIL-SAFE)
# ============================================================
try:
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    HAS_AUTHLIB = True
except ImportError:
    HAS_AUTHLIB = False
    oauth = None

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if HAS_AUTHLIB and oauth and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# ============================================================
# SUPABASE DATABASE SETUP
# ============================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[HookSpike DB]: Supabase connected.")
    except Exception as exc:
        print(f"[HookSpike DB Error]: {exc}")

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
        else:
            supabase.table("user_tokens").insert({"email": user_email, "tokens_left": 5}).execute()
            return 5
    except Exception as e:
        print(f"[Token Fetch Error]: {e}")
        return 5

def deduct_user_token(user_email: str) -> int:
    if user_email in ADMIN_EMAILS:
        return 99999999

    if not supabase:
        return 4

    try:
        current = get_user_tokens(user_email)
        new_balance = max(0, current - 1)
        supabase.table("user_tokens").update({"tokens_left": new_balance}).eq("email", user_email).execute()
        return new_balance
    except Exception as e:
        print(f"[Token Deduct Error]: {e}")
        return 0

# ============================================================
# CORE ROUTES
# ============================================================

@app.route("/")
def index():
    user_email = session.get("user_email")
    logged_in = bool(user_email)
    tokens_left = get_user_tokens(user_email) if logged_in else 0

    return render_template(
        "index.html",
        logged_in=logged_in,
        user_email=user_email,
        tokens_left=tokens_left
    )

@app.route("/login/google")
def login_google():
    if not HAS_AUTHLIB or not oauth or not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # Fallback simulation for developer
        session["user_email"] = "playerofwar99@gmail.com"
        return redirect(url_for("index"))
    redirect_uri = url_for("auth_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get("userinfo")
        if user_info and user_info.get("email"):
            session["user_email"] = user_info["email"]
    except Exception as err:
        print(f"[Auth Error]: {err}")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ============================================================
# STREAMING CHAT ROUTE
# ============================================================

@app.route("/api/chat-stream", methods=["POST"])
def chat_stream():
    user_email = session.get("user_email")
    logged_in = bool(user_email)

    if not logged_in:
        return jsonify({"error": "Please login first", "paywall": True}), 402

    tokens = get_user_tokens(user_email)
    if tokens <= 0 and user_email not in ADMIN_EMAILS:
        return jsonify({"error": "Tokens exhausted", "paywall": True}), 402

    payload = request.get_json() or {}
    message = payload.get("message", "").strip()
    history = payload.get("history", [])

    if not message:
        return jsonify({"error": "Empty message"}), 400

    remaining_tokens = deduct_user_token(user_email)

    def generate_sse():
        try:
            for chunk in ai_engine.stream_creator_chat(message, history):
                payload_data = json.dumps({"token": chunk, "tokens_left": remaining_tokens})
                yield f"data: {payload_data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            err_payload = json.dumps({"token": f"\n⚠️ [Engine Error]: {exc}", "tokens_left": remaining_tokens})
            yield f"data: {err_payload}\n\n"
            yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate_sse()), mimetype="text/event-stream")

# ============================================================
# PAYMENT / TOP-UP WEBHOOK
# ============================================================

@app.route("/api/top-up-tokens", methods=["POST"])
def top_up_tokens():
    data = request.get_json() or {}
    target_email = data.get("email")
    pack = data.get("pack")
    auth_secret = data.get("secret")

    if auth_secret != os.environ.get("PAYMENT_WEBHOOK_SECRET", "hookspike_pay_vault_77"):
        return jsonify({"error": "Unauthorized"}), 403

    if not target_email:
        return jsonify({"error": "Email missing"}), 400

    added_tokens = 17 if pack == "starter" else 40
    current = get_user_tokens(target_email)
    new_total = current + added_tokens

    if supabase:
        supabase.table("user_tokens").upsert({"email": target_email, "tokens_left": new_total}).execute()

    return jsonify({"ok": True, "email": target_email, "new_tokens": new_total})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
        
