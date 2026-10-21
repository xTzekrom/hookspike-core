import os
import sys
import time
from pathlib import Path

from flask import (
    Flask,
    render_template_string,
    request,
    session,
    redirect,
    url_for,
    send_file,
    jsonify,
)

from supabase import create_client, Client
from supabase.client import ClientOptions
from supabase_auth import SyncSupportedStorage


# ============================================================
# AI ENGINE
# ============================================================

try:
    from ai_engine import (
        get_ai_response,
        generate_thumbnail_image,
        generate_creator_pack,
        refine_creator_content,
        analyze_hook,
        discover_topics,
        generate_packaging_lab,
        generate_ab_packs,
        performance_coach,
        generate_content_plan,
        repurpose_creator_content,
    )
except ImportError:
    print("CRITICAL ERROR: 'ai_engine.py' file not found!")
    sys.exit(1)


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "CHANGE_THIS_SECRET_IN_RENDER"
)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
)


# ============================================================
# FLASK SESSION STORAGE FOR SUPABASE PKCE
# ============================================================

class FlaskSessionStorage(SyncSupportedStorage):

    def __init__(self):
        self.storage = session

    def get_item(self, key: str):
        return self.storage.get(key)

    def set_item(self, key: str, value: str):
        self.storage[key] = value

    def remove_item(self, key: str):
        self.storage.pop(key, None)


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")

supabase = None

if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase: Client = create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(
                storage=FlaskSessionStorage(),
                flow_type="pkce",
            ),
        )
        print("Supabase client initialized successfully.")
    except Exception as e:
        print(f"CRITICAL: Supabase initialization failed: {e}")
        supabase = None
else:
    print("WARNING: Supabase keys missing.")


# ============================================================
# HTML TEMPLATE LOADER
# ============================================================

HTML_TEMPLATE = (
    Path(__file__).resolve().parent / "index.html"
).read_text(encoding="utf-8")


# ============================================================
# TOKEN FUNCTIONS
# ============================================================

def get_user_tokens(user_id, email):
    if not supabase:
        return 5
    try:
        res = (
            supabase
            .table("user_tokens")
            .select("tokens_left")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return int(res.data[0]["tokens_left"])

        supabase.table("user_tokens").insert(
            {
                "id": user_id,
                "email": email,
                "tokens_left": 5,
            }
        ).execute()
        return 5
    except Exception as e:
        print(f"Database error in get_user_tokens: {e}")
        return 5


def decrease_user_token(user_id):
    if not supabase:
        return
    try:
        res = (
            supabase
            .table("user_tokens")
            .select("tokens_left")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return
        current = int(res.data[0]["tokens_left"])
        if current <= 0:
            return
        (
            supabase
            .table("user_tokens")
            .update({"tokens_left": current - 1})
            .eq("id", user_id)
            .execute()
        )
    except Exception as e:
        print(f"Database error on token update: {e}")


def _ai_result_is_success(result):
    if not isinstance(result, str):
        return bool(result)
    text = result.strip().lower()
    failure_markers = (
        "⚠️ ai is temporarily unavailable",
        "⚠️ ai is temporarily busy",
        "ai api key is not configured",
    )
    return bool(text) and not any(marker in text for marker in failure_markers)


# ============================================================
# ROUTES (HOME, STUDIO, AUTH)
# ============================================================

@app.route("/", methods=["GET", "POST"])
def index():
    user_id = session.get("user_id")
    email = session.get("user_email")

    if not user_id:
        return render_template_string(HTML_TEMPLATE, logged_in=False)

    tokens_left = get_user_tokens(user_id, email)
    result = None
    result_text = None
    result_image = None
    content_type = request.args.get("content_type", "hooks").strip().lower() if request.method == "GET" else "hooks"
    topic = request.args.get("topic", "").strip() if request.method == "GET" else ""
    show_paywall = (tokens_left <= 0)

    if request.method == "POST":
        content_type = request.form.get("content_type", "hooks").strip().lower()
        if content_type not in {"hooks", "script", "thumbnail"}:
            content_type = "hooks"
        topic = request.form.get("topic", "").strip()
        brand_voice = request.form.get("brand_voice", "").strip()

        if topic and tokens_left > 0:
            try:
                result = get_ai_response(content_type, topic, brand_voice=brand_voice[:4000])
                if isinstance(result, dict):
                    result_text = result.get("text")
                    result_image = result.get("image")
                else:
                    result_text = result
                    result_image = None

                if _ai_result_is_success(result):
                    decrease_user_token(user_id)
                    tokens_left = get_user_tokens(user_id, email)
            except Exception as e:
                result = "⚠️ AI Engine temporarily unavailable. Please try again."

        show_paywall = (tokens_left <= 0)

    return render_template_string(
        HTML_TEMPLATE,
        logged_in=True,
        user_email=email,
        result=result,
        result_text=result_text,
        result_image=result_image,
        content_type=content_type,
        topic=topic,
        tokens_left=tokens_left,
        show_paywall=show_paywall,
        studio_page=False,
        studio_tool="",
    )


@app.route("/creator-studio", methods=["GET"])
def creator_studio():
    user_id = session.get("user_id")
    email = session.get("user_email")
    if not user_id:
        return redirect("/")

    tokens_left = get_user_tokens(user_id, email)
    topic = request.args.get("topic", "").strip()
    studio_tool = request.args.get("tool", "").strip().lower()
    return render_template_string(
        HTML_TEMPLATE,
        logged_in=True,
        user_email=email,
        result=None,
        result_text=None,
        result_image=None,
        content_type="hooks",
        topic=topic,
        tokens_left=tokens_left,
        show_paywall=(tokens_left <= 0),
        studio_page=True,
        studio_tool=studio_tool,
    )


@app.route("/login/google")
def login_google():
    if not supabase:
        return "Supabase connection error.", 500
    redirect_url = "https://hookspike-core.onrender.com/auth/callback"
    try:
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_url}
        })
        return redirect(response.url)
    except Exception as e:
        return "Google login could not be started.", 500


@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error or not code or not supabase:
        session.clear()
        return "Google login failed.", 400
    try:
        response = supabase.auth.exchange_code_for_session({"auth_code": code})
        user_response = supabase.auth.get_user()
        user = getattr(user_response, "user", None)
        if not user:
            raise RuntimeError("User not found")
        session["user_id"] = user.id
        session["user_email"] = user.email or ""
        session.permanent = True
        return redirect(url_for("index"))
    except Exception as e:
        session.clear()
        return "Google login failed.", 400


@app.route("/logout")
def logout():
    try:
        if supabase:
            supabase.auth.sign_out()
    except:
        pass
    finally:
        session.clear()
    return redirect(url_for("index"))


# ============================================================
# STUDIO API ROUTES (Tools, Paywall, Features)
# =================================5===========================

def _studio_token_allowed():
    user_id = session.get("user_id")
    email = session.get("user_email", "")
    if not user_id:
        return None, 401, {"ok": False, "error": "⚠️ Please log in first."}
    tokens = get_user_tokens(user_id, email)
    if tokens <= 0:
        return None, 402, {"ok": False, "error": "🔒 You are out of creator tokens."}
    return (user_id, email), 200, None

@app.route("/generate-pack", methods=["POST"])
def generate_pack_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    topic = str(data.get("topic", "")).strip()
    result, err = generate_creator_pack(topic, str(data.get("brand_voice", ""))[:4000])
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/refine-content", methods=["POST"])
def refine_content_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = refine_creator_content(
        topic=str(data.get("topic", "")),
        content=str(data.get("content", "")),
        action=str(data.get("action", "")),
        brand_voice=str(data.get("brand_voice", ""))[:4000],
    )
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/analyze-hook", methods=["POST"])
def analyze_hook_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = analyze_hook(hook=str(data.get("hook", "")), topic=str(data.get("topic", "")))
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/discover-topics", methods=["POST"])
def discover_topics_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = discover_topics(str(data.get("category", "general")))
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/packaging-lab", methods=["POST"])
def packaging_lab_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = generate_packaging_lab(str(data.get("topic", "")).strip(), str(data.get("brand_voice", ""))[:4000])
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/ab-packs", methods=["POST"])
def ab_packs_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = generate_ab_packs(str(data.get("topic", "")).strip(), str(data.get("brand_voice", ""))[:4000])
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/performance-coach", methods=["POST"])
def performance_coach_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = performance_coach(str(data.get("topic", "")), str(data.get("metrics", "")).strip())
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/content-planner", methods=["POST"])
def content_planner_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = generate_content_plan(str(data.get("niche", "")).strip(), str(data.get("goal", "growth")))
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/repurpose-content", methods=["POST"])
def repurpose_content_route():
    identity, status, error = _studio_token_allowed()
    if error:
        return jsonify(error), status
    user_id, email = identity
    data = request.get_json(silent=True) or {}
    result, err = repurpose_creator_content(str(data.get("content", "")).strip(), "YouTube", str(data.get("target_platform", "Instagram Reels")))
    if result:
        decrease_user_token(user_id)
    return jsonify({"ok": True, "text": result})

@app.route("/generate-thumbnail", methods=["POST"])
def generate_thumbnail_route():
    if not session.get("user_id"):
        return jsonify({"ok": False, "image": None, "error": "⚠️ Please log in first."}), 401
    try:
        data = request.get_json(silent=True) or {}
        result = generate_thumbnail_image(
            topic=str(data.get("topic", ""))[:12000],
            thumbnail_text=str(data.get("thumbnail_text", ""))[:30000],
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "image": None, "error": "⚠️ Image server busy."}), 200


# ============================================================
# HEALTH & FAVICON
# ============================================================

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.route("/favicon.png")
def favicon():
    return send_file(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "file_00000000fd8481fab2b4f371e41aa854.png"),
        mimetype="image/png"
    )

@app.route("/health")
def health():
    return {"status": "ok", "app": "HookSpike AI", "ai_engine": "v2"}


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
