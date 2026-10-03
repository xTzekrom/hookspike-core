import os
import sys
import time

from flask import (
    Flask,
    render_template_string,
    request,
    session,
    redirect,
    url_for,
)

from supabase import create_client, Client
from supabase.client import ClientOptions
from supabase_auth import SyncSupportedStorage


# ============================================================
# AI ENGINE
# ============================================================

try:
    from ai_engine import get_ai_response
except ImportError:
    print("CRITICAL ERROR: 'ai_engine.py' file not found!")
    sys.exit(1)


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

# IMPORTANT:
# Render Dashboard -> Environment Variables me
# FLASK_SECRET_KEY set karna recommended hai.
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
    print(
        "WARNING: VITE_SUPABASE_URL or "
        "VITE_SUPABASE_ANON_KEY is missing."
    )


# ============================================================
# HTML
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>

<head>

    <meta
        name="google-site-verification"
        content="EOl-njARKhvmSLTzhuBy-3xJ8kchPVDb38nV-KzuLfk"
    />

    <title>HookSpike AI ⚡ - Ultra-Growth Creative Engine</title>

    <link rel="icon" type="image/png" href="https://raw.githubusercontent.com/xTzekrom/hookspike-core/main/file_00000000fd8481fab2b4f371e41aa854.png">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <style>

        body {
            font-family: 'Segoe UI', sans-serif;
            text-align: center;
            padding: 20px;
            background:
                radial-gradient(
                    circle at center,
                    #0d1527 0%,
                    #030712 100%
                );
            color: #f3f4f6;
            margin: 0;
        }
        /* --- Naya Creative Feature CSS --- */
        .hook-card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            padding: 20px;
            margin-top: 15px;
            border-left: 4px solid #f59e0b;
            transition: all 0.3s ease;
        }
        .hook-card:hover {
            border-color: #66fcf1;
            box-shadow: 0 0 15px rgba(102, 252, 241, 0.2);
        }
        .cue-box {
            background: rgba(245, 158, 11, 0.05);
            border: 1px dashed rgba(245, 158, 11, 0.3);
            border-radius: 10px;
            padding: 12px;
            margin-top: 15px;
            font-size: 13px;
            color: #9ca3af;
            text-align: left;
        }
        .cue-box strong {
            color: #f59e0b;
        }
        .copy-btn.copied {
            background: linear-gradient(90deg, #10b981, #059669) !important;
            color: white !important;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
        }
        

        .container {
            max-width: 500px;
            margin: 40px auto;
            background: rgba(11, 15, 25, 0.85);
            padding: 35px;
            border-radius: 24px;
            box-shadow:
                0 0 50px rgba(102, 252, 241, 0.15);
            border: 2px solid #1f2937;
            backdrop-filter: blur(15px);
        }

        .logo {
            font-size: 40px;
            font-weight: 900;
            color: #66fcf1;
            text-shadow:
                0 0 30px rgba(102, 252, 241, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .logo span {
            color: #f59e0b;
        }

        p.tagline {
            color: #9ca3af;
            font-size: 12px;
            margin-top: 5px;
            margin-bottom: 30px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 3px;
        }

        .counter-badge {
            display: inline-block;
            padding: 8px 18px;
            background: rgba(17, 24, 39, 0.9);
            border-radius: 30px;
            font-size: 13px;
            color: #66fcf1;
            border: 1px solid #00ffcc;
            margin-bottom: 25px;
            font-weight: bold;
        }

        .login-box {
            padding: 20px;
            text-align: center;
        }

        .google-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            padding: 16px;
            background: white;
            color: #1f2937;
            border-radius: 14px;
            font-weight: 700;
            font-size: 16px;
            text-decoration: none;
            border: 1px solid #e5e7eb;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            box-sizing: border-box;
            transition:
                transform 0.2s,
                box-shadow 0.2s;
        }

        .google-btn:hover {
            box-shadow: 0 6px 18px rgba(0,0,0,0.2);
        }

        .google-btn:active {
            transform: scale(0.98);
        }

        .google-icon {
            font-size: 22px;
            font-weight: 900;
        }

        .user-profile {
            font-size: 12px;
            color: #9ca3af;
            margin-bottom: 15px;
            text-align: right;
        }

        .logout-link {
            color: #f43f5e;
            text-decoration: none;
            margin-left: 8px;
            font-weight: bold;
        }

        label {
            display: block;
            text-align: left;
            font-size: 11px;
            color: #66fcf1;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 700;
        }

        select,
        input[type="text"] {
            width: 100%;
            padding: 18px;
            border: 2px solid #1f2937;
            border-radius: 14px;
            background-color: #0d111a;
            color: white;
            font-size: 16px;
            margin-bottom: 25px;
            outline: none;
            box-sizing: border-box;
        }

        button {
            width: 100%;
            padding: 18px;
            color: #030712;
            background:
                linear-gradient(
                    90deg,
                    #66fcf1,
                    #45a29e
                );
            border: none;
            border-radius: 16px;
            font-weight: 800;
            font-size: 18px;
            cursor: pointer;
            text-transform: uppercase;
        }

        .copy-btn {
            width: auto;
            display: inline-block;
            margin-top: 15px;
            padding: 10px 22px;
            background:
                linear-gradient(
                    90deg,
                    #f59e0b,
                    #d97706
                );
            color: #030712;
            border-radius: 10px;
            font-weight: bold;
            border: none;
            cursor: pointer;
        }

        .loader {
            display: none;
            margin: 25px auto;
            border: 4px solid #1f2937;
            border-radius: 50%;
            border-top: 4px solid #66fcf1;
            width: 45px;
            height: 45px;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            0% {
                transform: rotate(0deg);
            }

            100% {
                transform: rotate(360deg);
            }
        }

        .loading-text {
            display: none;
            color: #66fcf1;
            font-size: 14px;
            font-style: italic;
        }

        .result-box {
            text-align: left;
            margin-top: 35px;
            padding: 25px;
            background-color: #0d111a;
            border-radius: 20px;
            border-top: 4px solid #f59e0b;
            white-space: pre-wrap;
            font-size: 15px;
            line-height: 1.8;
            color: #e5e7eb;
            border-left: 1px solid #1f2833;
        }

        .result-box h3 {
            margin-top: 0;
            color: #f59e0b;
            font-size: 20px;
            font-weight: 800;
        }

        /* --- PREMIUM COMMERCIAL PAYWALL SUITE --- */
        .paywall-box {
            margin-top: 30px;
            padding: 40px 25px;
            background: linear-gradient(135deg, #0b1528 0%, #030712 100%);
            border: 2px solid #ef4444;
            border-radius: 28px;
            box-shadow: 0 0 35px rgba(239, 68, 68, 0.15);
            position: relative;
            overflow: hidden;
        }
        .paywall-box::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 100%; height: 4px;
            background: linear-gradient(90deg, #ef4444, #f59e0b);
        }
        .paywall-box h2 {
            color: #ef4444;
            font-size: 24px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .paywall-box p.pay-desc {
            color: #9ca3af;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .pricing-plan {
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 35px;
        }
        .plan-card {
            background: #0d111a;
            padding: 22px;
            border-radius: 18px;
            border: 1px solid #1f2937;
            text-align: left;
            position: relative;
            transition: all 0.3s ease;
            box-sizing: border-box;
            width: 100% !important;
        }
        .plan-card:hover {
            border-color: #66fcf1;
            box-shadow: 0 0 20px rgba(102, 252, 241, 0.1);
        }
        .plan-card.popular {
            border: 2px solid #f59e0b;
        }
        .plan-badge {
            position: absolute;
            top: -12px; right: 15px;
            background: #f59e0b;
            color: #030712;
            font-size: 10px;
            font-weight: 900;
            padding: 4px 10px;
            border-radius: 20px;
            text-transform: uppercase;
        }
        .plan-card h4 {
            margin: 0;
            color: #66fcf1;
            font-size: 16px;
            font-weight: 800;
        }
        .plan-card p.plan-sub {
            margin: 4px 0 12px 0;
            color: #6b7280;
            font-size: 12px;
        }
        .plan-price-row {
            display: flex;
            align-items: baseline;
            gap: 6px;
        }
        .plan-card p.price {
            margin: 0;
            font-size: 32px;
            font-weight: 900;
            color: #ffffff;
        }
        .plan-card span.duration {
            color: #9ca3af;
            font-size: 14px;
        }
        .upi-details {
            font-size: 15px;
            font-weight: 700;
            color: #66fcf1;
            background: rgba(17, 24, 39, 0.8);
            padding: 16px;
            border-radius: 14px;
            border: 1px solid #1f2937;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pay-btn {
            display: block;
            width: 100%;
            padding: 18px;
            background: linear-gradient(90deg, #66fcf1, #45a29e);
            color: #030712;
            text-decoration: none;
            border-radius: 16px;
            font-weight: 800;
            font-size: 16px;
            text-transform: uppercase;
            box-shadow: 0 4px 20px rgba(102, 252, 241, 0.2);
            box-sizing: border-box;
            transition: all 0.2s ease;
        }
        .pay-btn:hover {
            box-shadow: 0 6px 25px rgba(102, 252, 241, 0.3);
            transform: translateY(-2px);
        }


    </style>

    <script>

        function showLoading() {

            var submitBtn =
                document.getElementById("submitBtn");

            var loader =
                document.getElementById("loaderIcon");

            var loaderText =
                document.getElementById("loaderText");

            if (submitBtn) {
                submitBtn.style.display = "none";
            }

            if (loader) {
                loader.style.display = "block";
            }

            if (loaderText) {
                loaderText.style.display = "block";
            }
        }


         function copyText() {
            var element = document.getElementById("rawText");
            if (!element) return;

            var text = element.innerText || element.textContent;

            // --- AI Text Enhancer Engine (Auto Formatting & Emojis) ---
            let formattedText = text;
            const boostWords = {
                "problem": "⚠️ MASSIVE PROBLEM",
                "delay": "🚨 UNANNOUNCED DELAY",
                "secret": "🤫 SECRET DETAIL",
                "leak": "🔥 CONFIDENTIAL LEAK",
                "gta 6": "🎮 GTA 6",
                "rockstar": "⭐ Rockstar"
            };

            for (let [word, replaceWith] of Object.entries(boostWords)) {
                let regex = new RegExp(word, "gi");
                formattedText = formattedText.replace(regex, replaceWith);
            }

            // Copy Action
            if (navigator.clipboard) {
                navigator.clipboard.writeText(formattedText).then(function () {
                    triggerCopySuccess();
                }).catch(function () {
                    fallbackCopy(formattedText);
                });
            } else {
                fallbackCopy(formattedText);
            }
        }

        function triggerCopySuccess() {
            var btn = document.getElementById("copyBtnText");
            if (btn) {
                btn.innerText = "🟢 Copied with Strategy Matrix! ✓";
                btn.classList.add("copied");

                // Tech sound effect logic
                try {
                    let audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    let oscillator = audioCtx.createOscillator();
                    let gainNode = audioCtx.createGain();
                    oscillator.connect(gainNode);
                    gainNode.connect(audioCtx.destination);
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
                    gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
                    oscillator.start();
                    oscillator.stop(audioCtx.currentTime + 0.1);
                } catch(e) {}

                setTimeout(function () {
                    btn.innerText = "📋 Copy Strategy Data";
                    btn.classList.remove("copied");
                }, 2000);
            }
        }

        function fallbackCopy(text) {
            var textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand("copy");
            document.body.removeChild(textArea);
            triggerCopySuccess();
        }


    </script>

</head>


<body>

<div class="container">

    <div class="logo">
        Hook<span>Spike</span> AI ⚡
    </div>

    <p class="tagline">
        Hyper-Growth Retention Suite
    </p>


    {% if not logged_in %}

        <div class="login-box">

            <h3
                style="
                    color:#66fcf1;
                    margin-bottom:20px;
                "
            >
                Welcome Back Creator!
            </h3>

            <p
                style="
                    color:#9ca3af;
                    font-size:14px;
                    margin-bottom:30px;
                "
            >
                Sign in with Google to sync
                your tokens securely across
                all devices.
            </p>

            <a
                href="/login/google"
                class="google-btn"
            >

                <span class="google-icon">
                    G
                </span>

                <span>
                    Continue with Google
                </span>

            </a>

        </div>


    {% else %}

        <div class="user-profile">

            👤 {{ user_email }}

            |

            <a
                href="/logout"
                class="logout-link"
            >
                Logout
            </a>

        </div>


        <div class="counter-badge">

            ⚡ Neural Tokens Remaining:
            {{ tokens_left }} / 5

        </div>


        {% if show_paywall %}

            <div class="paywall-box">

                <h2>
                    🔒 Commercial Pipeline Locked
                </h2>

                <p class="pay-desc">
                    Your trial parameters have expired. Select an enterprise tier below to lift engine execution rate-limits instantly.
                </p>

                <div class="pricing-plan">

                    <!-- Plan 1: Pro Suite -->
                    <div class="plan-card">
                        <h4>Creator Pro Plan</h4>
                        <p class="plan-sub">Perfect for rising independent streamers & video editors</p>
                        <div class="plan-price-row">
                            <p class="price">₹1,499</p>
                            <span class="duration">/ monthly subscription</span>
                        </div>
                    </div>

                    <!-- Plan 2: Agency Suite (Popular) -->
                    <div class="plan-card popular">
                        <div class="plan-badge">Most Popular</div>
                        <h4>Agency Growth Suite</h4>
                        <p class="plan-sub">Full speed access with multi-platform deep tracking vectors</p>
                        <div class="plan-price-row">
                            <p class="price">₹1,999</p>
                            <span class="duration">/ monthly subscription</span>
                        </div>
                    </div>

                </div>

                <div class="upi-details">
                    <span>💥 Merchant UPI Anchor:</span>
                    <span style="color: #fff; font-family: monospace;">9657119506@axl</span>
                </div>

                <!-- Open UPI Gateway intent string configuration mapped to professional plan pricing -->
                <a
                    href="intent://pay?pa=9657119506@axl&pn=HookSpike%20AI&am=1499&cu=INR#Intent;scheme=upi;package=com.google.android.apps.nbu.paisa.user;end"
                    class="pay-btn"
                >
                    📱 Initialize Secure Gateway Payment
                </a>

            </div>
            


        {% else %}

            <form
                method="POST"
                action="/"
                onsubmit="showLoading()"
            >

                <label>
                    Select Optimization Engine:
                </label>

                <select
                    name="platform_type"
                    required
                >

                    <option value="youtube">
                        🎥 YouTube Engine
                        (Hooks & Thumbnails)
                    </option>

                    <option value="instagram">
                        📱 Instagram Reels Engine
                        (Viral Scripts & Hooks)
                    </option>

                    <option value="global_ai">
                        🌐 HookSpike Core AI Search
                        (Global Intelligence)
                    </option>

                </select>


                <label>
                    Enter Topic / Strategy Request:
                </label>

                <input
                    type="text"
                    name="topic"
                    placeholder="Enter topic, query, or script concept..."
                    value="{{ topic }}"
                    required
                >


                <button
                    type="submit"
                    id="submitBtn"
                >
                    Launch AI Strategy Engine 🚀
                </button>

            </form>

        {% endif %}


        <div
            id="loaderIcon"
            class="loader"
        ></div>

        <div
            id="loaderText"
            class="loading-text"
        >
            ⚡ HookSpike Compiling
            Multi-Platform Vectors...
        </div>


        {% if result and not show_paywall %}

            <div class="result-box">

                <h3>
                    📊 Engine Output Matrix Unlocked:
                </h3>

                <!-- Naya Visual Gaming Card Hook Wrapper -->
                <div class="hook-card">
                    <div id="rawText">{{ result }}</div>
                    
                    <!-- Dynamic Creator Video/Audio Guidance Box -->
                    <div class="cue-box">
                        🎬 <strong>Visual Cue Suggestion:</strong> Show high-paced B-roll mapping to the core query concept. Apply a 3-second aggressive frame zoom to disrupt viewer scrolling patterns.<br><br>
                        🎵 <strong>Audio Cue Suggestion:</strong> Layer a low-frequency cinematic sub-bass drop or 'Vine Boom' element exactly at the hook delivery timestamp.
                    </div>
                </div>

                <button
                    id="copyBtnText"
                    class="copy-btn"
                    onclick="copyText()"
                    type="button"
                >
                    📋 Copy Strategy Data
                </button>

            </div>

        {% endif %}

    {% endif %}

</div>

</body>

</html>
"""


# ============================================================
# TOKEN FUNCTIONS
# ============================================================

def get_user_tokens(user_id, email):

    # Development fallback if Supabase is unavailable.
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

            return int(
                res.data[0]["tokens_left"]
            )

        # First login -> create token record
        supabase.table("user_tokens").insert(
            {
                "id": user_id,
                "email": email,
                "tokens_left": 5,
            }
        ).execute()

        return 5

    except Exception as e:

        print(
            f"Database error in get_user_tokens: {e}"
        )

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

        # FIX:
        # res.data is a list.
        current = int(
            res.data[0]["tokens_left"]
        )

        if current <= 0:
            return

        (
            supabase
            .table("user_tokens")
            .update(
                {
                    "tokens_left": current - 1
                }
            )
            .eq("id", user_id)
            .execute()
        )

    except Exception as e:

        print(
            f"Database error on token update: {e}"
        )


# ============================================================
# AI RESULT / TOKEN SAFETY
# ============================================================

def _ai_result_is_success(result):
    """
    Only consume a user token when the AI engine actually returned
    a usable result. Provider/configuration failures must not burn tokens.
    """
    if not isinstance(result, str):
        return bool(result)

    text = result.strip().lower()

    failure_markers = (
        "⚠️ ai is temporarily unavailable",
        "⚠️ ai is temporarily busy",
        "ai api key is not configured",
        "gemini api key is not configured",
        "openai api key is not configured",
        "openai sdk is missing",
        "gemini research failed",
        "openai creative generation failed",
    )

    return bool(text) and not any(marker in text for marker in failure_markers)


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET", "POST"])
def index():

    # IMPORTANT:
    # OAuth callback saves these values.
    # We don't process ?code= here anymore.
    user_id = session.get("user_id")
    email = session.get("user_email")

    # Not logged in
    if not user_id:

        return render_template_string(
            HTML_TEMPLATE,
            logged_in=False,
        )


    # Get current token count
    tokens_left = get_user_tokens(
        user_id,
        email,
    )

    result = None
    topic = ""

    show_paywall = (
        tokens_left <= 0
    )


    # ========================================================
    # AI GENERATION
    # ========================================================

    if request.method == "POST":

        platform_type = (
            request.form
            .get("platform_type", "")
            .strip()
        )

        topic = (
            request.form
            .get("topic", "")
            .strip()
        )


        if not topic:

            return render_template_string(
                HTML_TEMPLATE,
                logged_in=True,
                user_email=email,
                result=None,
                topic="",
                tokens_left=tokens_left,
                show_paywall=show_paywall,
            )


        if tokens_left > 0:

            started_at = time.perf_counter()

            try:

                result = get_ai_response(
                    platform_type,
                    topic,
                )

                elapsed = time.perf_counter() - started_at

                print(
                    f"AI request completed in {elapsed:.2f}s "
                    f"| platform={platform_type} "
                    f"| topic_chars={len(topic)}"
                )

                # IMPORTANT:
                # Do NOT consume a token when the AI provider failed.
                if _ai_result_is_success(result):
                    decrease_user_token(user_id)

                    tokens_left = get_user_tokens(
                        user_id,
                        email,
                    )
                else:
                    print(
                        "AI request did not produce a successful result; "
                        "token was not consumed."
                    )

            except Exception as e:

                elapsed = time.perf_counter() - started_at

                print(
                    f"AI Engine Error after {elapsed:.2f}s: "
                    f"{repr(e)}"
                )

                result = (
                    "⚠️ AI Engine temporarily unavailable. "
                    "Your token was not consumed. Please try again."
                )


        show_paywall = (
            tokens_left <= 0
        )


    return render_template_string(
        HTML_TEMPLATE,
        logged_in=True,
        user_email=email,
        result=result,
        topic=topic,
        tokens_left=tokens_left,
        show_paywall=show_paywall,
    )


# ============================================================
# GOOGLE LOGIN
# ============================================================

@app.route("/login/google")
def login_google():

    if not supabase:

        return (
            "Supabase connection error. "
            "Check Render environment variables.",
            500,
        )


    # THIS MUST MATCH SUPABASE REDIRECT URL
    redirect_url = (
        "https://hookspike-core.onrender.com"
        "/auth/callback"
    )


    try:

        response = (
            supabase
            .auth
            .sign_in_with_oauth(
                {
                    "provider": "google",

                    "options": {
                        "redirect_to": redirect_url,
                    },
                }
            )
        )

        return redirect(
            response.url
        )

    except Exception as e:

        print(
            f"Google OAuth start error: {e}"
        )

        return (
            "Google login could not be started. "
            "Please try again.",
            500,
        )


# ============================================================
# GOOGLE OAUTH CALLBACK
# ============================================================

@app.route("/auth/callback")
def auth_callback():

    code = request.args.get("code")

    error = request.args.get("error")

    error_description = request.args.get(
        "error_description"
    )


    # --------------------------------------------------------
    # Google/Supabase returned an OAuth error
    # --------------------------------------------------------

    if error:

        print(
            "OAuth error:",
            error,
            error_description,
        )

        session.clear()

        return (
            "Google login was cancelled or rejected. "
            "Please start again.",
            400,
        )


    # --------------------------------------------------------
    # No authorization code
    # --------------------------------------------------------

    if not code:

        print(
            "OAuth callback received "
            "without authorization code."
        )

        session.clear()

        return (
            "Login callback did not contain "
            "an authorization code.",
            400,
        )


    if not supabase:

        return (
            "Supabase connection error.",
            500,
        )


    try:

        # ----------------------------------------------------
        # Exchange the PKCE authorization code
        # ----------------------------------------------------

        response = (
            supabase
            .auth
            .exchange_code_for_session(
                {
                    "auth_code": code
                }
            )
        )


        if not response:

            raise RuntimeError(
                "Supabase returned an empty response."
            )


        # ----------------------------------------------------
        # Get the authenticated user from the new session
        # ----------------------------------------------------

        user_response = (
            supabase
            .auth
            .get_user()
        )


        user = getattr(
            user_response,
            "user",
            None,
        )


        if not user:

            raise RuntimeError(
                "Could not retrieve authenticated user."
            )


        # ----------------------------------------------------
        # Save only the required identity in Flask session
        # ----------------------------------------------------

        session["user_id"] = user.id

        session["user_email"] = (
            user.email or ""
        )

        session.permanent = True

        print(
            "Google login successful:",
            user.email,
        )


        # ----------------------------------------------------
        # IMPORTANT:
        # Redirect to / WITHOUT the OAuth code.
        # This prevents the login-loop.
        # ----------------------------------------------------

        return redirect(
            url_for("index")
        )


    except Exception as e:

        print(
            "OAuth callback exchange error:",
            repr(e),
        )

        # Remove incomplete login state
        session.clear()

        return (
            "Google login failed. "
            "Please start a fresh login attempt.",
            400,
        )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    try:

        if supabase:

            supabase.auth.sign_out()

    except Exception as e:

        print(
            f"Supabase logout error: {e}"
        )

    finally:

        # Always clear Flask session
        session.clear()


    return redirect(
        url_for("index")
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.after_request
def add_no_cache_headers(response):
    # AI results are dynamic; never let an intermediary/browser serve
    # an old generated page as a new result.
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/health")
def health():

    return {
        "status": "ok",
        "app": "HookSpike AI",
        "ai_engine": "v2",
    }


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000,
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )

